"""
Tests for Feature 32 - Rule Execution Graph Visualizer
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.rule import Rule
from app.models.rule_dependency import RuleDependency, DependencyType


@pytest_asyncio.fixture
async def graph_user(db_session: AsyncSession):
    user = User(id=uuid4(), external_id=f"graph-test-{uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def graph_rules(db_session: AsyncSession, graph_user):
    rules = []
    # Create 3 rules
    for i in range(3):
        rule = Rule(
            id=uuid4(),
            user_id=graph_user.id,
            content=f"Rule number {i}",
            category="style",
            confidence=0.8,
            status="active",
        )
        db_session.add(rule)
        rules.append(rule)
    await db_session.flush()
    return rules


class TestRuleGraph:
    @pytest.mark.asyncio
    async def test_acyclic_and_conflict_graph(
        self, client: AsyncClient, db_session: AsyncSession, graph_user, graph_rules
    ):
        # Establish dependencies: Rule 1 requires Rule 0, Rule 2 requires Rule 1
        r0, r1, r2 = graph_rules
        dep1 = RuleDependency(
            id=uuid4(),
            rule_id=r1.id,
            depends_on_rule_id=r0.id,
            dependency_type=DependencyType.REQUIRES.value,
        )
        dep2 = RuleDependency(
            id=uuid4(),
            rule_id=r2.id,
            depends_on_rule_id=r1.id,
            dependency_type=DependencyType.REQUIRES.value,
        )
        db_session.add_all([dep1, dep2])
        await db_session.flush()

        # 1. Check topological sort order
        resp = await client.get(
            "/api/rules/graph/topology",
            headers={"X-User-ID": str(graph_user.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_cycle"] is False
        # Since r1 requires r0, and r2 requires r1, the topological execution order must be r0 -> r1 -> r2
        order_ids = [n["id"] for n in data["topological_order"]]
        assert order_ids.index(str(r0.id)) < order_ids.index(str(r1.id))
        assert order_ids.index(str(r1.id)) < order_ids.index(str(r2.id))

        # 2. Check cycle detection (should be False)
        cycle_resp = await client.get(
            "/api/rules/graph/cycles",
            headers={"X-User-ID": str(graph_user.id)},
        )
        assert cycle_resp.status_code == 200
        assert cycle_resp.json()["has_cycle"] is False

        # Add an exclusion to test conflict path analyzer: Rule 2 excludes Rule 0
        dep_exclude = RuleDependency(
            id=uuid4(),
            rule_id=r2.id,
            depends_on_rule_id=r0.id,
            dependency_type=DependencyType.EXCLUDES.value,
        )
        db_session.add(dep_exclude)
        await db_session.flush()

        # 3. Check conflict path analysis (should find rule 2 requiring and excluding rule 0)
        conflict_resp = await client.get(
            "/api/rules/graph/conflict-paths",
            headers={"X-User-ID": str(graph_user.id)},
        )
        assert conflict_resp.status_code == 200
        conflicts = conflict_resp.json()
        assert len(conflicts) >= 1
        assert any(c["rule_id"] == str(r2.id) and c["conflicting_rule_id"] == str(r0.id) for c in conflicts)
