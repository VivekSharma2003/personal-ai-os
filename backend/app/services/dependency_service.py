"""
Personal AI OS - Rule Dependency Service

Manages rule dependency chains with cycle detection and resolution.
"""
from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Any
from uuid import UUID
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule_dependency import RuleDependency, DependencyType
from app.models.rule import Rule
from app.core.logging import get_logger

logger = get_logger("services.dependency")


class DependencyService:
    """
    Manages rule dependency relationships with cycle detection.

    Supports three dependency types:
      - REQUIRES: child only active if parent is active
      - EXCLUDES: child only active if parent is NOT active
      - ENHANCES: advisory only (no enforcement)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def add_dependency(
        self,
        rule_id: UUID,
        depends_on_rule_id: UUID,
        dependency_type: str = DependencyType.REQUIRES.value,
    ) -> Optional[RuleDependency]:
        """
        Create a dependency link between two rules.

        Returns None if a cycle would be created.
        """
        # Prevent self-dependency
        if rule_id == depends_on_rule_id:
            raise ValueError("A rule cannot depend on itself")

        # Check both rules exist
        rule = await self._get_rule(rule_id)
        parent = await self._get_rule(depends_on_rule_id)
        if not rule or not parent:
            raise ValueError("One or both rules not found")

        # Check for cycles (would adding this edge create a cycle?)
        if await self._would_create_cycle(rule_id, depends_on_rule_id):
            raise ValueError(
                "Adding this dependency would create a circular chain"
            )

        # Check for duplicates
        existing = await self.db.execute(
            select(RuleDependency).where(
                RuleDependency.rule_id == rule_id,
                RuleDependency.depends_on_rule_id == depends_on_rule_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("This dependency already exists")

        dep = RuleDependency(
            rule_id=rule_id,
            depends_on_rule_id=depends_on_rule_id,
            dependency_type=dependency_type,
        )
        self.db.add(dep)
        await self.db.flush()

        logger.info(
            f"Dependency created: {rule_id} {dependency_type} {depends_on_rule_id}",
            extra={"extra_data": {"dep_id": str(dep.id)}},
        )

        return dep

    async def remove_dependency(self, dep_id: UUID) -> bool:
        """Remove a dependency by ID."""
        result = await self.db.execute(
            select(RuleDependency).where(RuleDependency.id == dep_id)
        )
        dep = result.scalar_one_or_none()
        if not dep:
            return False

        await self.db.delete(dep)
        return True

    async def get_dependencies(self, rule_id: UUID) -> List[Dict[str, Any]]:
        """Get all dependencies for a rule (things this rule depends on)."""
        result = await self.db.execute(
            select(RuleDependency).where(RuleDependency.rule_id == rule_id)
        )
        deps = result.scalars().all()

        enriched = []
        for dep in deps:
            parent_rule = await self._get_rule(dep.depends_on_rule_id)
            enriched.append({
                **dep.to_dict(),
                "depends_on_content": parent_rule.content[:80] if parent_rule else None,
            })

        return enriched

    async def get_dependents(self, rule_id: UUID) -> List[Dict[str, Any]]:
        """Get all rules that depend on this rule."""
        result = await self.db.execute(
            select(RuleDependency).where(
                RuleDependency.depends_on_rule_id == rule_id
            )
        )
        deps = result.scalars().all()

        enriched = []
        for dep in deps:
            child_rule = await self._get_rule(dep.rule_id)
            enriched.append({
                **dep.to_dict(),
                "rule_content": child_rule.content[:80] if child_rule else None,
            })

        return enriched

    # ------------------------------------------------------------------
    # Chain resolution
    # ------------------------------------------------------------------

    async def resolve_chain(self, rule_ids: List[UUID]) -> List[UUID]:
        """
        Given a list of candidate active rules, filter out any whose
        dependencies aren't satisfied.

        - REQUIRES: rule is removed if its parent is NOT in the active set
        - EXCLUDES: rule is removed if its parent IS in the active set
        - ENHANCES: no filtering (advisory only)
        """
        active_set = set(rule_ids)

        # Load all dependencies for these rules in one query
        result = await self.db.execute(
            select(RuleDependency).where(
                RuleDependency.rule_id.in_(rule_ids),
                RuleDependency.dependency_type.in_([
                    DependencyType.REQUIRES.value,
                    DependencyType.EXCLUDES.value,
                ]),
            )
        )
        deps = result.scalars().all()

        # Build dependency map
        deps_by_rule: Dict[UUID, List[RuleDependency]] = defaultdict(list)
        for dep in deps:
            deps_by_rule[dep.rule_id].append(dep)

        # Filter
        resolved = []
        for rule_id in rule_ids:
            if rule_id not in deps_by_rule:
                # No dependencies — always included
                resolved.append(rule_id)
                continue

            satisfied = True
            for dep in deps_by_rule[rule_id]:
                if dep.dependency_type == DependencyType.REQUIRES.value:
                    if dep.depends_on_rule_id not in active_set:
                        satisfied = False
                        break
                elif dep.dependency_type == DependencyType.EXCLUDES.value:
                    if dep.depends_on_rule_id in active_set:
                        satisfied = False
                        break

            if satisfied:
                resolved.append(rule_id)

        return resolved

    # ------------------------------------------------------------------
    # Dependency graph
    # ------------------------------------------------------------------

    async def get_dependency_graph(self, user_id: UUID) -> Dict[str, Any]:
        """
        Build a full dependency graph for a user's rules.

        Returns a structure suitable for visualization:
          - nodes: [{id, content, category, status}]
          - edges: [{from, to, type}]
        """
        # Get all user rules
        result = await self.db.execute(
            select(Rule).where(Rule.user_id == user_id)
        )
        rules = result.scalars().all()
        rule_ids = [r.id for r in rules]

        # Get all dependencies between user's rules
        result = await self.db.execute(
            select(RuleDependency).where(
                RuleDependency.rule_id.in_(rule_ids)
            )
        )
        deps = result.scalars().all()

        # Build nodes (only rules that have at least one dependency)
        dep_rule_ids = set()
        for dep in deps:
            dep_rule_ids.add(dep.rule_id)
            dep_rule_ids.add(dep.depends_on_rule_id)

        nodes = [
            {
                "id": str(r.id),
                "content": r.content[:80],
                "category": r.category,
                "status": r.status,
            }
            for r in rules
            if r.id in dep_rule_ids
        ]

        edges = [
            {
                "from": str(d.rule_id),
                "to": str(d.depends_on_rule_id),
                "type": d.dependency_type,
            }
            for d in deps
        ]

        return {
            "nodes": nodes,
            "edges": edges,
            "total_rules": len(rules),
            "rules_with_dependencies": len(dep_rule_ids),
        }

    # ------------------------------------------------------------------
    # Cycle detection
    # ------------------------------------------------------------------

    async def _would_create_cycle(
        self, from_id: UUID, to_id: UUID
    ) -> bool:
        """
        Check if adding an edge from_id → to_id would create a cycle.

        Uses BFS starting from to_id to see if we can reach from_id.
        """
        visited: Set[UUID] = set()
        queue: deque[UUID] = deque([to_id])

        while queue:
            current = queue.popleft()
            if current == from_id:
                return True  # cycle detected

            if current in visited:
                continue
            visited.add(current)

            # Get outgoing edges from current
            result = await self.db.execute(
                select(RuleDependency.depends_on_rule_id).where(
                    RuleDependency.rule_id == current
                )
            )
            for (next_id,) in result:
                if next_id not in visited:
                    queue.append(next_id)

        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_rule(self, rule_id: UUID) -> Optional[Rule]:
        result = await self.db.execute(select(Rule).where(Rule.id == rule_id))
        return result.scalar_one_or_none()
