"""
Personal AI OS - Test Idempotency Key Service
"""
import pytest
import uuid
from app.services.idempotency import IdempotencyService


@pytest.mark.asyncio
async def test_miss_then_store_then_hit():
    service = IdempotencyService()
    key = f"idem-test-{uuid.uuid4()}"

    # Clean state → miss
    result = await service.get(key)
    assert result is None
    assert await service.exists(key) is False

    # Store
    payload = {"order_id": "ord_123", "status": "created"}
    await service.store(key, payload, ttl=60)

    # Hit — exact payload returned
    result = await service.get(key)
    assert result == payload
    assert await service.exists(key) is True

    # Cleanup
    deleted = await service.delete(key)
    assert deleted is True
    assert await service.exists(key) is False


@pytest.mark.asyncio
async def test_different_keys_are_isolated():
    service = IdempotencyService()
    key_a = f"idem-a-{uuid.uuid4()}"
    key_b = f"idem-b-{uuid.uuid4()}"

    await service.store(key_a, {"msg": "A"}, ttl=60)

    assert await service.get(key_a) == {"msg": "A"}
    assert await service.get(key_b) is None

    await service.delete(key_a)


@pytest.mark.asyncio
async def test_delete_nonexistent_returns_false():
    service = IdempotencyService()
    deleted = await service.delete(f"ghost-{uuid.uuid4()}")
    assert deleted is False


@pytest.mark.asyncio
async def test_idempotency_api_flow(client):
    key = f"api-idem-{uuid.uuid4()}"

    # Miss
    resp = await client.post("/api/idempotency/check", json={"key": key})
    assert resp.status_code == 200
    assert resp.json()["hit"] is False

    # Store
    resp = await client.post("/api/idempotency/store", json={
        "key": key,
        "response": {"result": "ok", "id": 42},
        "ttl": 60,
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "stored"

    # Hit
    resp = await client.post("/api/idempotency/check", json={"key": key})
    assert resp.status_code == 200
    data = resp.json()
    assert data["hit"] is True
    assert data["response"]["id"] == 42

    # Delete
    resp = await client.delete(f"/api/idempotency/{key}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"

    # 404 on double-delete
    resp = await client.delete(f"/api/idempotency/{key}")
    assert resp.status_code == 404
