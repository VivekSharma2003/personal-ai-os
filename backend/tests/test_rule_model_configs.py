"""
Tests for Feature 28 - Model-Specific Temperature Tuning & Prompt Optimization
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.rule import Rule
from app.models.rule_model_config import RuleModelConfig


@pytest_asyncio.fixture
async def config_user(db_session: AsyncSession):
    user = User(id=uuid4(), external_id=f"cfg-test-{uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def config_rule(db_session: AsyncSession, config_user):
    rule = Rule(
        id=uuid4(),
        user_id=config_user.id,
        content="Always use formal language",
        category="style",
        confidence=0.8,
        status="active",
    )
    db_session.add(rule)
    await db_session.flush()
    return rule


class TestRuleModelConfigs:
    @pytest.mark.asyncio
    async def test_upsert_list_and_delete_configs(
        self, client: AsyncClient, config_user, config_rule
    ):
        # 1. Create config override
        response = await client.post(
            f"/api/rules/{config_rule.id}/model-configs",
            headers={"X-User-ID": str(config_user.id)},
            json={
                "provider": "openai",
                "model_name": "gpt-4",
                "temperature_override": 0.2,
                "max_tokens_override": 100,
                "optimized_content": "Be extremely formal, like a butler",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "created"
        config_id = data["config"]["id"]

        # 2. List configs
        list_resp = await client.get(
            f"/api/rules/{config_rule.id}/model-configs",
            headers={"X-User-ID": str(config_user.id)},
        )
        assert list_resp.status_code == 200
        configs = list_resp.json()
        assert len(configs) == 1
        assert configs[0]["provider"] == "openai"
        assert configs[0]["model_name"] == "gpt-4"

        # 3. Update existing config override
        update_resp = await client.post(
            f"/api/rules/{config_rule.id}/model-configs",
            headers={"X-User-ID": str(config_user.id)},
            json={
                "provider": "openai",
                "model_name": "gpt-4",
                "temperature_override": 0.1,
                "max_tokens_override": 150,
                "optimized_content": "Butler-esque style is strictly required",
            },
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["action"] == "updated"

        # 4. Delete config override
        del_resp = await client.delete(
            f"/api/rules/model-configs/{config_id}",
            headers={"X-User-ID": str(config_user.id)},
        )
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] is True
