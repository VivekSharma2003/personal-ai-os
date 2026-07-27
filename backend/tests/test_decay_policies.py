"""
Tests for Feature 29 - Context-Aware Dynamic Decay with Task Tags
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.rule import Rule
from app.models.decay_policy import DecayPolicy
from app.models.interaction import Interaction


@pytest_asyncio.fixture
async def decay_user(db_session: AsyncSession):
    user = User(id=uuid4(), external_id=f"decay-test-{uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def decay_rule(db_session: AsyncSession, decay_user):
    rule = Rule(
        id=uuid4(),
        user_id=decay_user.id,
        content="Always use metric units",
        category="formatting",
        confidence=0.8,
        status="active",
        last_applied_at=datetime.utcnow() - timedelta(days=20),
    )
    db_session.add(rule)
    await db_session.flush()
    return rule


class TestDecayPolicies:
    @pytest.mark.asyncio
    async def test_policy_crud_and_processing(
        self, client: AsyncClient, db_session: AsyncSession, decay_user, decay_rule
    ):
        # 1. Create decay policy override
        response = await client.post(
            "/api/decay/policies",
            headers={"X-User-ID": str(decay_user.id)},
            json={
                "category": "formatting",
                "base_decay_rate": 0.1,
                "grace_period_days": 10,
                "topic_sensitivity": 0.5,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "formatting"
        assert data["base_decay_rate"] == 0.1
        policy_id = data["id"]

        # 2. List policies
        list_resp = await client.get(
            "/api/decay/policies",
            headers={"X-User-ID": str(decay_user.id)},
        )
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

        # 3. Dry-run decay check
        # With grace_period_days = 10, and last_applied_at 20 days ago,
        # weeks_unused = (20 - 10) // 7 = 1.
        # Since formatting was completely inactive (no recent interactions),
        # decay rate is scaled by (1 - topic_sensitivity) = (1 - 0.5) = 0.5.
        # So decay = 1 * 0.1 * 0.5 = 0.05.
        process_dry_resp = await client.post(
            "/api/decay/process?dry_run=true",
            headers={"X-User-ID": str(decay_user.id)},
        )
        assert process_dry_resp.status_code == 200
        process_dry_data = process_dry_resp.json()
        assert process_dry_data["processed"] == 1
        assert round(process_dry_data["changes"][0]["new_confidence"], 2) == 0.75

        # 4. Commit decay check
        process_resp = await client.post(
            "/api/decay/process?dry_run=false",
            headers={"X-User-ID": str(decay_user.id)},
        )
        assert process_resp.status_code == 200
        process_data = process_resp.json()
        assert process_data["processed"] == 1

        # Check DB updated
        await db_session.refresh(decay_rule)
        assert round(decay_rule.confidence, 2) == 0.75

        # 5. Delete policy
        del_resp = await client.delete(
            f"/api/decay/policies/{policy_id}",
            headers={"X-User-ID": str(decay_user.id)},
        )
        assert del_resp.status_code == 200
