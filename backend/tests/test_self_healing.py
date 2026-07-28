"""
Tests for Feature 31 - Automated LLM Adherence Judge & Rule Self-Healing
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.rule import Rule
from app.models.interaction import Interaction
from app.models.adherence_eval import AdherenceEvaluation


@pytest_asyncio.fixture
async def heal_user(db_session: AsyncSession):
    user = User(id=uuid4(), external_id=f"heal-test-{uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def heal_rule(db_session: AsyncSession, heal_user):
    rule = Rule(
        id=uuid4(),
        user_id=heal_user.id,
        content="Do not use contractions",
        category="style",
        confidence=0.8,
        status="active",
    )
    db_session.add(rule)
    await db_session.flush()
    return rule


@pytest_asyncio.fixture
async def heal_interaction(db_session: AsyncSession, heal_user, heal_rule):
    interaction = Interaction(
        id=uuid4(),
        user_id=heal_user.id,
        conversation_id=f"conv-{uuid4().hex[:8]}",
        user_message="Hello!",
        assistant_response="I'm here to help.",  # contraction violated the rule!
        rules_applied=[heal_rule.id],
    )
    db_session.add(interaction)
    await db_session.flush()
    return interaction


class TestSelfHealing:
    @pytest.mark.asyncio
    async def test_evaluation_and_healing_flow(
        self, client: AsyncClient, db_session: AsyncSession, heal_user, heal_rule, heal_interaction
    ):
        # 1. Evaluate interaction
        eval_resp = await client.post(
            f"/api/evaluations/evaluate/{heal_interaction.id}",
            headers={"X-User-ID": str(heal_user.id)},
        )
        assert eval_resp.status_code == 200
        eval_data = eval_resp.json()
        assert eval_data["interaction_id"] == str(heal_interaction.id)
        assert len(eval_data["evaluations"]) == 1

        # Save some low-adherence evaluations to trigger healing
        for _ in range(3):
            ad_eval = AdherenceEvaluation(
                id=uuid4(),
                interaction_id=heal_interaction.id,
                rule_id=heal_rule.id,
                adhered=False,
                score=0.4,
                justification="Response included contraction 'I'm'.",
            )
            db_session.add(ad_eval)
        await db_session.flush()

        # 2. Get adherence stats
        stats_resp = await client.get(
            "/api/evaluations/stats",
            headers={"X-User-ID": str(heal_user.id)},
        )
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        assert len(stats) >= 1
        assert stats[0]["rule_id"] == str(heal_rule.id)
        assert stats[0]["eval_count"] >= 4

        # 3. Heal rule
        heal_rule_resp = await client.post(
            f"/api/evaluations/heal/{heal_rule.id}",
            headers={"X-User-ID": str(heal_user.id)},
        )
        assert heal_rule_resp.status_code == 200
        heal_data = heal_rule_resp.json()
        assert heal_data["healed"] is True
        assert heal_data["old_content"] == "Do not use contractions"
        assert heal_data["new_content"] != ""
