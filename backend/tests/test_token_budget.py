"""
Personal AI OS - Test Token Budget Enforcer
"""
import pytest
from app.services.token_budget import TokenBudgetService, _estimate_tokens


def test_estimate_tokens_basic():
    # 10 words → ~13 tokens
    result = _estimate_tokens("one two three four five six seven eight nine ten")
    assert 12 <= result <= 15


def test_check_within_budget():
    service = TokenBudgetService()
    short_prompt = "Tell me a joke."
    report = service.check("openai", "gpt-4o", short_prompt, reserved_output_tokens=1024)
    assert report["within_budget"] is True
    assert report["overflow"] == 0
    assert report["limit"] == 100_000


def test_check_over_budget():
    service = TokenBudgetService()
    # Simulate a huge prompt by using a tiny reserved window for a "small" model
    # gpt-3.5-turbo limit 12_000; reserve 11_999 → only 1 token available
    very_long = "word " * 200   # ~270 estimated tokens
    report = service.check("openai", "gpt-3.5-turbo", very_long, reserved_output_tokens=11_999)
    assert report["within_budget"] is False
    assert report["overflow"] > 0


def test_truncate_fits_after():
    service = TokenBudgetService()
    # gpt-3.5-turbo limit = 12_000; reserve 11_500 → 500 tokens available
    long_prompt = " ".join([f"word{i}" for i in range(500)])  # ~675 tokens
    truncated = service.truncate("openai", "gpt-3.5-turbo", long_prompt, reserved_output_tokens=11_500)
    final_report = service.check("openai", "gpt-3.5-turbo", truncated, reserved_output_tokens=11_500)
    assert final_report["within_budget"] is True
    assert "[...truncated" in truncated


def test_truncate_noop_when_fits():
    service = TokenBudgetService()
    short = "Hello, world!"
    result = service.truncate("openai", "gpt-4o", short)
    assert result == short


def test_unknown_model_uses_default():
    service = TokenBudgetService()
    limit = service.get_limit("mystery_corp", "turbo-x99")
    assert limit == 16_000


@pytest.mark.asyncio
async def test_token_budget_api_check(client):
    resp = await client.post("/api/token-budget/check", json={
        "provider": "openai",
        "model": "gpt-4o",
        "prompt": "What is the meaning of life?",
        "reserved_output_tokens": 1024
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "within_budget" in data
    assert data["within_budget"] is True


@pytest.mark.asyncio
async def test_token_budget_api_truncate(client):
    long_prompt = " ".join([f"token{i}" for i in range(200)])
    resp = await client.post("/api/token-budget/truncate", json={
        "provider": "openai",
        "model": "gpt-3.5-turbo",
        "prompt": long_prompt,
        "reserved_output_tokens": 11_990
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "prompt" in data
    assert "was_truncated" in data


@pytest.mark.asyncio
async def test_token_budget_api_limits(client):
    resp = await client.get("/api/token-budget/limits")
    assert resp.status_code == 200
    data = resp.json()
    assert "openai:gpt-4o" in data
    assert "_default" in data
