"""
Tests for Prompt Replay & Regression Testing feature.
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.interaction import Interaction
from app.models.replay import ReplayRun, ReplayResult


@pytest_asyncio.fixture
async def replay_user(db_session: AsyncSession):
    """Create a test user for replay tests."""
    user = User(id=uuid4(), external_id=f"replay-test-{uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def replay_interactions(db_session: AsyncSession, replay_user):
    """Create test interactions for replaying."""
    interactions = []
    for i in range(3):
        interaction = Interaction(
            id=uuid4(),
            user_id=replay_user.id,
            conversation_id=f"conv-{uuid4().hex[:8]}",
            user_message=f"Test prompt #{i}: How should I format this?",
            assistant_response=f"Original response #{i}: You should format it this way.",
        )
        db_session.add(interaction)
        interactions.append(interaction)
    await db_session.flush()
    return interactions


@pytest_asyncio.fixture
async def replay_run(db_session: AsyncSession, replay_user):
    """Create a completed replay run."""
    run = ReplayRun(
        id=uuid4(),
        user_id=replay_user.id,
        name="Test Replay Run",
        status="completed",
        total_interactions=5,
        completed=5,
        regressions_found=1,
        improvements_found=2,
        unchanged_count=2,
    )
    db_session.add(run)
    await db_session.flush()

    # Add some results
    for i, verdict in enumerate(["regression", "improved", "unchanged"]):
        result = ReplayResult(
            id=uuid4(),
            run_id=run.id,
            original_prompt=f"Prompt #{i}",
            original_response=f"Original #{i}",
            replayed_response=f"Replayed #{i}",
            similarity_score=0.5 + i * 0.2,
            verdict=verdict,
            diff_summary=f"+2 new terms; -1 removed terms",
        )
        db_session.add(result)

    await db_session.flush()
    return run


class TestReplayRoutes:
    """Test replay REST endpoints."""

    @pytest.mark.asyncio
    async def test_list_runs_empty(self, client: AsyncClient, replay_user):
        """Listing runs for a user with no runs returns empty."""
        response = await client.get(
            "/api/replay",
            headers={"X-User-ID": str(replay_user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["runs"] == []

    @pytest.mark.asyncio
    async def test_list_runs_with_data(self, client: AsyncClient, replay_user, replay_run):
        """Listing runs returns existing runs."""
        response = await client.get(
            "/api/replay",
            headers={"X-User-ID": str(replay_user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_run_detail(self, client: AsyncClient, replay_user, replay_run):
        """Getting run detail returns correct data."""
        response = await client.get(
            f"/api/replay/{replay_run.id}",
            headers={"X-User-ID": str(replay_user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Replay Run"
        assert data["status"] == "completed"
        assert data["regressions_found"] == 1
        assert data["improvements_found"] == 2

    @pytest.mark.asyncio
    async def test_get_run_not_found(self, client: AsyncClient, replay_user):
        """Getting non-existent run returns 404."""
        response = await client.get(
            f"/api/replay/{uuid4()}",
            headers={"X-User-ID": str(replay_user.id)},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_results(self, client: AsyncClient, replay_user, replay_run):
        """Getting results for a run returns items."""
        response = await client.get(
            f"/api/replay/{replay_run.id}/results",
            headers={"X-User-ID": str(replay_user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["results"]) >= 1

    @pytest.mark.asyncio
    async def test_get_results_filtered(self, client: AsyncClient, replay_user, replay_run):
        """Filtering results by verdict works."""
        response = await client.get(
            f"/api/replay/{replay_run.id}/results?verdict=regression",
            headers={"X-User-ID": str(replay_user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        for r in data["results"]:
            assert r["verdict"] == "regression"

    @pytest.mark.asyncio
    async def test_start_replay_no_interactions(self, client: AsyncClient, replay_user):
        """Starting replay with no interactions returns error."""
        response = await client.post(
            "/api/replay",
            headers={"X-User-ID": str(replay_user.id)},
            json={"name": "Empty Run"},
        )
        assert response.status_code == 400


class TestReplayModels:
    """Test replay model methods."""

    @pytest.mark.asyncio
    async def test_run_to_dict(self, replay_run):
        """ReplayRun.to_dict returns expected fields."""
        d = replay_run.to_dict()
        assert d["name"] == "Test Replay Run"
        assert d["progress_pct"] == 100.0
        assert d["regressions_found"] == 1

    @pytest.mark.asyncio
    async def test_run_progress_pct(self, db_session):
        """Progress percentage computation is correct."""
        run = ReplayRun(
            id=uuid4(),
            user_id=uuid4(),
            name="Partial Run",
            total_interactions=10,
            completed=3,
        )
        d = run.to_dict()
        assert d["progress_pct"] == 30.0
