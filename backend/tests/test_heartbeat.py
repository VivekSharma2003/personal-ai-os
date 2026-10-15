"""
Personal AI OS - Test Job Heartbeat Watchdog
"""
import asyncio
import pytest
import uuid
from app.services.job_heartbeat import JobHeartbeat, HeartbeatWatchdog


def _job():
    name = f"indexer-{uuid.uuid4()}"
    job_id = f"run-{uuid.uuid4()}"
    return name, job_id


@pytest.mark.asyncio
async def test_start_appears_in_active():
    name, job_id = _job()
    hb = JobHeartbeat(name, job_id, ttl=60)
    await hb.start()
    try:
        watchdog = HeartbeatWatchdog()
        active = await watchdog.list_active()
        members = [f"{j['job_name']}:{j['job_id']}" for j in active]
        assert f"{name}:{job_id}" in members
    finally:
        await hb.finish()


@pytest.mark.asyncio
async def test_finish_removes_from_registry():
    name, job_id = _job()
    hb = JobHeartbeat(name, job_id, ttl=60)
    await hb.start()
    await hb.finish()

    watchdog = HeartbeatWatchdog()
    active = await watchdog.list_active()
    members = [f"{j['job_name']}:{j['job_id']}" for j in active]
    assert f"{name}:{job_id}" not in members


@pytest.mark.asyncio
async def test_stale_detection():
    name, job_id = _job()
    hb = JobHeartbeat(name, job_id, ttl=60)
    await hb.start()

    # A 1-second threshold means the job is immediately stale
    watchdog = HeartbeatWatchdog()
    stale = await watchdog.stale_jobs(staleness_threshold=1)
    # Allow a tiny sleep so the score is clearly older than 1 s
    await asyncio.sleep(1.1)
    stale = await watchdog.stale_jobs(staleness_threshold=1)
    stale_members = [s["member"] for s in stale]
    assert f"{name}:{job_id}" in stale_members

    await hb.finish()


@pytest.mark.asyncio
async def test_beat_refreshes_and_clears_stale():
    name, job_id = _job()
    hb = JobHeartbeat(name, job_id, ttl=60)
    await hb.start()
    await asyncio.sleep(1.1)

    # Without beat → stale
    watchdog = HeartbeatWatchdog()
    stale_before = await watchdog.stale_jobs(staleness_threshold=1)
    assert any(s["member"] == f"{name}:{job_id}" for s in stale_before)

    # Beat → no longer stale
    await hb.beat()
    stale_after = await watchdog.stale_jobs(staleness_threshold=1)
    assert not any(s["member"] == f"{name}:{job_id}" for s in stale_after)

    await hb.finish()


@pytest.mark.asyncio
async def test_heartbeat_api(client):
    name, job_id = f"api-job-{uuid.uuid4()}", f"run-{uuid.uuid4()}"

    # Start
    resp = await client.post(f"/api/heartbeat/{name}/{job_id}/start")
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"

    # Active list
    resp = await client.get("/api/heartbeat/jobs")
    assert resp.status_code == 200
    members = [f"{j['job_name']}:{j['job_id']}" for j in resp.json()]
    assert f"{name}:{job_id}" in members

    # Beat
    resp = await client.post(f"/api/heartbeat/{name}/{job_id}/beat")
    assert resp.status_code == 200

    # Finish
    resp = await client.post(f"/api/heartbeat/{name}/{job_id}/finish")
    assert resp.status_code == 200
    assert resp.json()["status"] == "finished"

    # No longer active
    resp = await client.get("/api/heartbeat/jobs")
    members = [f"{j['job_name']}:{j['job_id']}" for j in resp.json()]
    assert f"{name}:{job_id}" not in members
