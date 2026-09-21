"""
Personal AI OS - Test LLM Response Cache
"""
import pytest
from app.services.llm_cache import LLMCacheService


@pytest.mark.asyncio
async def test_cache_miss_then_store_then_hit():
    service = LLMCacheService()
    provider, model, prompt = "openai", "gpt-4o", "What is 2+2?"

    # Clean state
    await service.invalidate(provider, model, prompt)

    # Miss
    result = await service.get(provider, model, prompt)
    assert result is None

    # Store
    await service.store(provider, model, prompt, "4", ttl=60)

    # Hit
    result = await service.get(provider, model, prompt)
    assert result == "4"

    # Cleanup
    deleted = await service.invalidate(provider, model, prompt)
    assert deleted is True


@pytest.mark.asyncio
async def test_different_keys_dont_collide():
    service = LLMCacheService()

    await service.store("openai", "gpt-4o", "Hello?", "Hi!", ttl=60)
    await service.store("anthropic", "claude-3", "Hello?", "Hey!", ttl=60)

    r1 = await service.get("openai", "gpt-4o", "Hello?")
    r2 = await service.get("anthropic", "claude-3", "Hello?")
    assert r1 == "Hi!"
    assert r2 == "Hey!"

    await service.invalidate("openai", "gpt-4o", "Hello?")
    await service.invalidate("anthropic", "claude-3", "Hello?")


@pytest.mark.asyncio
async def test_flush_all():
    service = LLMCacheService()

    await service.store("openai", "gpt-4o", "Prompt A", "Answer A", ttl=60)
    await service.store("openai", "gpt-4o", "Prompt B", "Answer B", ttl=60)

    stats = await service.stats()
    assert stats["cached_entries"] >= 2

    flushed = await service.flush_all()
    assert flushed >= 2

    stats = await service.stats()
    assert stats["cached_entries"] == 0


@pytest.mark.asyncio
async def test_cache_api(client):
    # Miss
    resp = await client.post("/api/llm-cache/lookup", json={
        "provider": "openai", "model": "gpt-4o", "prompt": "api test prompt"
    })
    assert resp.status_code == 200
    assert resp.json()["hit"] is False

    # Store
    resp = await client.post("/api/llm-cache/store", json={
        "provider": "openai", "model": "gpt-4o",
        "prompt": "api test prompt", "response": "api answer", "ttl": 60
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "stored"

    # Hit
    resp = await client.post("/api/llm-cache/lookup", json={
        "provider": "openai", "model": "gpt-4o", "prompt": "api test prompt"
    })
    assert resp.status_code == 200
    assert resp.json()["hit"] is True
    assert resp.json()["response"] == "api answer"

    # Invalidate
    resp = await client.post("/api/llm-cache/invalidate", json={
        "provider": "openai", "model": "gpt-4o", "prompt": "api test prompt"
    })
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    # Stats
    resp = await client.get("/api/llm-cache/stats")
    assert resp.status_code == 200
    assert "cached_entries" in resp.json()
