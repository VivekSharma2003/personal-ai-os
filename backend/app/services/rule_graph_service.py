"""
Personal AI OS - Rule Graph Service

Handles DAG building, cycle detection, topological sorting, and conflict path analysis
for rule dependencies.
"""
from typing import List, Dict, Any, Tuple, Set
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule, RuleStatus
from app.models.rule_dependency import RuleDependency, DependencyType

import collections


class RuleGraphService:
    """Service to represent, validate, and analyze the DAG of rule dependencies."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_rules_and_dependencies(self, user_id: UUID) -> Tuple[List[Rule], List[RuleDependency]]:
        """Fetch all active rules and their dependency relationships for a user."""
        rules_stmt = select(Rule).where(
            and_(Rule.user_id == user_id, Rule.status == RuleStatus.ACTIVE.value)
        )
        rules_res = await self.db.execute(rules_stmt)
        rules = list(rules_res.scalars().all())

        if not rules:
            return [], []

        rule_ids = [r.id for r in rules]
        dep_stmt = select(RuleDependency).where(
            and_(
                RuleDependency.rule_id.in_(rule_ids),
                RuleDependency.depends_on_rule_id.in_(rule_ids),
            )
        )
        dep_res = await self.db.execute(dep_stmt)
        dependencies = list(dep_res.scalars().all())

        return rules, dependencies

    async def get_topology(self, user_id: UUID) -> Dict[str, Any]:
        """
        Build the dependency graph and return its topological sorting order.
        If a cycle is detected, returns cycle information instead.
        """
        rules, dependencies = await self.get_user_rules_and_dependencies(user_id)

        rule_map = {r.id: r.content for r in rules}
        nodes = list(rule_map.keys())

        # Adjacency list: depends_on -> rule (parent -> child)
        adj: Dict[UUID, List[UUID]] = {n: [] for n in nodes}
        in_degree: Dict[UUID, int] = {n: 0 for n in nodes}

        for dep in dependencies:
            if dep.dependency_type == DependencyType.REQUIRES.value:
                # depends_on must execute first
                adj[dep.depends_on_rule_id].append(dep.rule_id)
                in_degree[dep.rule_id] += 1

        # Kahn's Algorithm
        queue = collections.deque([n for n in nodes if in_degree[n] == 0])
        order = []

        while queue:
            curr = queue.popleft()
            order.append(curr)

            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # If order doesn't contain all nodes, there is a cycle in "requires" dependencies
        has_cycle = len(order) < len(nodes)
        cycle_nodes = []
        if has_cycle:
            cycle_nodes = [str(n) for n in nodes if in_degree[n] > 0]

        return {
            "has_cycle": has_cycle,
            "cycle_nodes": cycle_nodes,
            "topological_order": [
                {"id": str(nid), "content": rule_map[nid]} for nid in order
            ],
            "adjacency_list": {
                str(k): [str(v) for v in val] for k, val in adj.items()
            },
        }

    async def detect_cycles(self, user_id: UUID) -> Dict[str, Any]:
        """Detect any cycles in rule dependencies (specifically requires relationships)."""
        topology = await self.get_topology(user_id)
        return {
            "has_cycle": topology["has_cycle"],
            "cycle_nodes": topology["cycle_nodes"],
        }

    async def analyze_conflict_paths(self, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Identify conflict-prone execution paths.
        For example: Rule A requires Rule B, but Rule A also excludes Rule B.
        Or Rule A requires Rule B, and Rule B excludes Rule C, but Rule A requires Rule C.
        """
        rules, dependencies = await self.get_user_rules_and_dependencies(user_id)

        rule_map = {r.id: r for r in rules}
        nodes = list(rule_map.keys())

        # Excludes relationships map
        excludes: Dict[UUID, Set[UUID]] = {n: set() for n in nodes}
        # Requires relationships (parent -> child)
        requires: Dict[UUID, Set[UUID]] = {n: set() for n in nodes}

        for dep in dependencies:
            if dep.dependency_type == DependencyType.EXCLUDES.value:
                excludes[dep.rule_id].add(dep.depends_on_rule_id)
                excludes[dep.depends_on_rule_id].add(dep.rule_id)
            elif dep.dependency_type == DependencyType.REQUIRES.value:
                # rule_id requires depends_on_rule_id (child -> parent)
                requires[dep.rule_id].add(dep.depends_on_rule_id)

        conflicts = []

        # Find direct and transitive conflicts:
        # A requires B, but A excludes B
        for r_id in nodes:
            # Transitive requirements of r_id
            visited = set()
            def dfs(curr):
                for parent in requires[curr]:
                    if parent not in visited:
                        visited.add(parent)
                        dfs(parent)

            dfs(r_id)

            # Check if any transitively required rule is directly excluded by r_id
            for req_id in visited:
                if req_id in excludes[r_id]:
                    conflicts.append(
                        {
                            "type": "require_exclude_conflict",
                            "description": (
                                f"Rule '{rule_map[r_id].content[:40]}' transitively requires "
                                f"'{rule_map[req_id].content[:40]}', but also excludes it."
                            ),
                            "rule_id": str(r_id),
                            "conflicting_rule_id": str(req_id),
                        }
                    )

            # Check if two required rules exclude each other
            req_list = list(visited)
            for i in range(len(req_list)):
                for j in range(i + 1, len(req_list)):
                    u, v = req_list[i], req_list[j]
                    if v in excludes[u]:
                        conflicts.append(
                            {
                                "type": "mutually_exclusive_requirements",
                                "description": (
                                    f"Rule '{rule_map[r_id].content[:40]}' requires both "
                                    f"'{rule_map[u].content[:40]}' and '{rule_map[v].content[:40]}', "
                                    "which exclude each other."
                                ),
                                "rule_id": str(r_id),
                                "required_rules": [str(u), str(v)],
                            }
                        )

        return conflicts
