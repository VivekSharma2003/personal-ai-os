"""
Personal AI OS - Test Circuit Breaker
"""
import pytest
import uuid
from app.services.circuit_breaker import CircuitBreaker


def _svc():
    """Unique service name per test to avoid Redis key collisions."""
    return f"test-svc-{uuid.uuid4()}"


@pytest.mark.asyncio
async def test_starts_closed():
    cb = CircuitBreaker(_svc(), "default")
    assert await cb.is_open() is False
    status = await cb.get_status()
    assert status["state"] == "CLOSED"
    assert status["failures"] == 0


@pytest.mark.asyncio
async def test_trips_after_threshold():
    svc = _svc()
    cb = CircuitBreaker(svc, "default", failure_threshold=3)

    for _ in range(3):
        await cb.record_failure()

    assert await cb.is_open() is True
    status = await cb.get_status()
    assert status["state"] == "OPEN"


@pytest.mark.asyncio
async def test_success_resets_failure_count():
    svc = _svc()
    cb = CircuitBreaker(svc, "default", failure_threshold=5)

    await cb.record_failure()
    await cb.record_failure()
    await cb.record_success()

    status = await cb.get_status()
    assert status["failures"] == 0
    assert status["state"] == "CLOSED"


@pytest.mark.asyncio
async def test_force_open_and_close():
    svc = _svc()
    cb = CircuitBreaker(svc, "default")

    await cb.force_open()
    assert (await cb.get_status())["state"] == "OPEN"

    await cb.force_close()
    assert (await cb.get_status())["state"] == "CLOSED"
    assert await cb.is_open() is False


@pytest.mark.asyncio
async def test_circuit_breaker_api(client):
    svc, res = f"api-svc-{uuid.uuid4()}", "gpt-4o"

    # Status — starts closed
    resp = await client.get(f"/api/circuit-breaker/{svc}/{res}")
    assert resp.status_code == 200
    assert resp.json()["state"] == "CLOSED"

    # Record 5 failures (default threshold)
    for _ in range(5):
        resp = await client.post(f"/api/circuit-breaker/{svc}/{res}/failure")
        assert resp.status_code == 200
    assert resp.json()["state"] == "OPEN"

    # Force close
    resp = await client.post(f"/api/circuit-breaker/{svc}/{res}/close")
    assert resp.status_code == 200
    assert resp.json()["state"] == "CLOSED"

    # Record a success
    resp = await client.post(f"/api/circuit-breaker/{svc}/{res}/success")
    assert resp.status_code == 200
