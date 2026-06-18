"""
Tests for Background Job Dashboard.
"""
import pytest
import asyncio

from app.core.job_tracker import JobTracker, get_job_tracker, tracked_job


@pytest.fixture(autouse=True)
def clean_tracker():
    """Reset the tracker singleton between tests."""
    tracker = get_job_tracker()
    tracker.clear()
    yield
    tracker.clear()


def test_record_and_get_runs():
    """Test recording job runs and retrieving them."""
    tracker = get_job_tracker()

    tracker.record_run("test_job", "success", 150.0)
    tracker.record_run("test_job", "success", 200.0)
    tracker.record_run("test_job", "failure", 50.0, detail="Connection error")

    runs = tracker.get_runs("test_job")
    assert len(runs) == 3
    # Most recent first
    assert runs[0]["status"] == "failure"
    assert runs[0]["detail"] == "Connection error"


def test_get_stats():
    """Test aggregate statistics computation."""
    tracker = get_job_tracker()

    tracker.record_run("stats_job", "success", 100.0)
    tracker.record_run("stats_job", "success", 200.0)
    tracker.record_run("stats_job", "failure", 50.0, detail="Timeout")

    stats = tracker.get_stats("stats_job")
    assert stats["total_runs"] == 3
    assert stats["success_count"] == 2
    assert stats["failure_count"] == 1
    assert stats["success_rate"] == pytest.approx(66.7, abs=0.1)
    assert stats["avg_duration_ms"] == pytest.approx(116.67, abs=0.1)


def test_get_all_stats():
    """Test getting stats for all tracked jobs."""
    tracker = get_job_tracker()

    tracker.record_run("job_a", "success", 100.0)
    tracker.record_run("job_b", "failure", 50.0)

    all_stats = tracker.get_all_stats()
    assert "job_a" in all_stats
    assert "job_b" in all_stats
    assert all_stats["job_a"]["success_count"] == 1
    assert all_stats["job_b"]["failure_count"] == 1


def test_empty_job_stats():
    """Test stats for a job with no runs."""
    tracker = get_job_tracker()
    stats = tracker.get_stats("nonexistent")
    assert stats["total_runs"] == 0
    assert stats["avg_duration_ms"] == 0
    assert stats["success_rate"] == 0


@pytest.mark.asyncio
async def test_tracked_job_decorator_success():
    """Test that @tracked_job records successful runs."""
    tracker = get_job_tracker()

    @tracked_job
    async def my_good_job():
        await asyncio.sleep(0.01)
        return "done"

    result = await my_good_job()
    assert result == "done"

    runs = tracker.get_runs("my_good_job")
    assert len(runs) == 1
    assert runs[0]["status"] == "success"
    assert runs[0]["duration_ms"] > 0


@pytest.mark.asyncio
async def test_tracked_job_decorator_failure():
    """Test that @tracked_job records failures without re-raising."""
    tracker = get_job_tracker()

    @tracked_job
    async def my_bad_job():
        raise RuntimeError("Something broke")

    result = await my_bad_job()
    assert result is None  # Decorator catches the error

    runs = tracker.get_runs("my_bad_job")
    assert len(runs) == 1
    assert runs[0]["status"] == "failure"
    assert "Something broke" in runs[0]["detail"]


def test_ring_buffer_max_size():
    """Test that the ring buffer doesn't grow beyond MAX_RUNS."""
    tracker = get_job_tracker()

    for i in range(150):
        tracker.record_run("overflow_job", "success", float(i))

    runs = tracker.get_runs("overflow_job", limit=200)
    assert len(runs) <= JobTracker.MAX_RUNS
