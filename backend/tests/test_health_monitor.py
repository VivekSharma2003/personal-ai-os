"""
Personal AI OS - Test Background Health Monitor
"""
import pytest
from app.services.health_monitor import HealthMonitorService


@pytest.mark.asyncio
async def test_run_and_store(db_session):
    service = HealthMonitorService(db_session)
    snap = await service.run_and_store()

    assert snap.id is not None
    assert snap.db_ok is True          # in-process test DB is always up
    assert snap.redis_ok is True       # test Redis is always up
    assert snap.healthy is True
    assert snap.db_latency_ms >= 0
    assert snap.redis_latency_ms >= 0
    assert snap.active_rules_count is not None


@pytest.mark.asyncio
async def test_get_latest(db_session):
    service = HealthMonitorService(db_session)
    # No snapshots yet — should return None
    snap = await service.get_latest()
    # There may already be snapshots from other tests; just check it doesn't crash
    assert snap is None or snap.id is not None


@pytest.mark.asyncio
async def test_history_ordering(db_session):
    service = HealthMonitorService(db_session)
    await service.run_and_store()
    await service.run_and_store()
    await service.run_and_store()

    snaps = await service.get_recent(limit=3)
    assert len(snaps) >= 2
    # Newest first
    for i in range(len(snaps) - 1):
        assert snaps[i].checked_at >= snaps[i + 1].checked_at


@pytest.mark.asyncio
async def test_health_monitor_api_run(client):
    resp = await client.post("/api/health-monitor/run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["db_ok"] is True
    assert data["redis_ok"] is True
    assert data["healthy"] is True
    assert "db_latency_ms" in data


@pytest.mark.asyncio
async def test_health_monitor_api_latest(client):
    # Seed a snapshot first
    await client.post("/api/health-monitor/run")

    resp = await client.get("/api/health-monitor/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert "healthy" in data


@pytest.mark.asyncio
async def test_health_monitor_api_history(client):
    await client.post("/api/health-monitor/run")
    resp = await client.get("/api/health-monitor/history?limit=5")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_health_monitor_api_status(client):
    await client.post("/api/health-monitor/run")
    resp = await client.get("/api/health-monitor/status")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("healthy", "degraded", "critical", "unknown")
