"""
Tests for LLM Cost Tracking and Budget Guardrails.
"""
import pytest
import pytest_asyncio
from uuid import uuid4

from app.models.user import User
from app.services.cost_service import CostService
from app.core.cost_tracker import compute_cost


@pytest_asyncio.fixture
async def cost_user(db_session):
    """Create a test user for cost tracking tests."""
    user = User(external_id=f"cost_test_{uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.mark.asyncio
async def test_record_usage(db_session, cost_user):
    """Test recording LLM usage and cost computation."""
    service = CostService(db_session)

    usage = await service.record_usage(
        user_id=cost_user.id,
        provider="openai",
        model="gpt-4o",
        prompt_tokens=1000,
        completion_tokens=2000,
        endpoint="chat",
    )

    assert usage is not None
    assert usage.provider == "openai"
    assert usage.model == "gpt-4o"
    assert usage.prompt_tokens == 1000
    assert usage.completion_tokens == 2000
    assert usage.total_tokens == 3000

    # gpt-4o pricing is $0.005 / 1K prompt, $0.015 / 1K completion
    # 1000 * 0.005/1000 + 2000 * 0.015/1000 = 0.005 + 0.030 = 0.035
    assert abs(usage.estimated_cost_usd - 0.035) < 1e-6


@pytest.mark.asyncio
async def test_budget_enforcement(db_session, cost_user):
    """Test checking and exceeding budgets."""
    service = CostService(db_session)

    # Initially allowed
    status = await service.check_budget(cost_user.id)
    assert status["allowed"] is True

    # Record some usage that does NOT exceed budget (default limits are $5.0 daily, $100.0 monthly)
    await service.record_usage(
        user_id=cost_user.id,
        provider="openai",
        model="gpt-4",
        prompt_tokens=10000,
        completion_tokens=20000,
        endpoint="chat",
    )

    status = await service.check_budget(cost_user.id)
    assert status["allowed"] is True

    # Record usage that EXCEEDS the daily budget
    # Let's record huge usage (e.g. 500,000 prompts, 500,000 completions on gpt-4)
    # gpt-4 is $0.03 / 1k prompt, $0.06 / 1k completion.
    # 500000 * 0.03/1000 = $15.0 (which is > $5.0)
    await service.record_usage(
        user_id=cost_user.id,
        provider="openai",
        model="gpt-4",
        prompt_tokens=500000,
        completion_tokens=500000,
        endpoint="chat",
    )

    status = await service.check_budget(cost_user.id)
    assert status["allowed"] is False
    assert status["daily_exceeded"] is True


@pytest.mark.asyncio
async def test_cost_routes(client, db_session, cost_user):
    """Test cost endpoint routes."""
    # Set headers for authorization fallback
    headers = {"X-User-ID": str(cost_user.id)}

    response = await client.get("/api/costs", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "month"
    assert data["total_requests"] == 0

    response = await client.get("/api/costs/budget", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "daily_limit_usd" in data
    assert "monthly_limit_usd" in data

    response = await client.get("/api/costs/trend", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["trend"], list)

    response = await client.get("/api/costs/breakdown", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "by_endpoint" in data
