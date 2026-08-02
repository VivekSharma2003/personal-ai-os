"""
Tests for Rule Impact Simulation (Dry-Run) feature.
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.rule import Rule
from app.services.simulation_service import SimulationService


@pytest_asyncio.fixture
async def sim_user(db_session: AsyncSession):
    """Create a test user for simulation tests."""
    user = User(id=uuid4(), external_id=f"sim-test-{uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def sim_rule(db_session: AsyncSession, sim_user):
    """Create a test rule for edit simulation."""
    rule = Rule(
        id=uuid4(),
        user_id=sim_user.id,
        content="Always use bullet points for lists",
        category="formatting",
        confidence=0.8,
        status="active",
    )
    db_session.add(rule)
    await db_session.flush()
    return rule


class TestSimulationService:
    """Test SimulationService utility methods."""

    @pytest.mark.asyncio
    async def test_compute_impact_identical(self, db_session):
        """Identical texts have zero impact."""
        service = SimulationService(db_session)
        score = service._compute_impact("hello world", "hello world")
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_compute_impact_different(self, db_session):
        """Completely different texts have high impact."""
        service = SimulationService(db_session)
        score = service._compute_impact("hello world", "foo bar baz")
        assert score > 0.5

    @pytest.mark.asyncio
    async def test_compute_impact_partial(self, db_session):
        """Partially overlapping texts have moderate impact."""
        service = SimulationService(db_session)
        score = service._compute_impact("hello world foo", "hello world bar")
        assert 0.0 < score < 1.0

    @pytest.mark.asyncio
    async def test_compute_impact_empty(self, db_session):
        """Empty text results in max impact."""
        service = SimulationService(db_session)
        score = service._compute_impact("", "hello")
        assert score == 1.0

    @pytest.mark.asyncio
    async def test_summarize_diff_identical(self, db_session):
        """Identical texts produce 'nearly identical' summary."""
        service = SimulationService(db_session)
        summary = service._summarize_diff("hello world", "hello world")
        assert "identical" in summary.lower()

    @pytest.mark.asyncio
    async def test_summarize_diff_with_changes(self, db_session):
        """Changed texts produce diff summary with counts."""
        service = SimulationService(db_session)
        summary = service._summarize_diff("hello world", "hello universe")
        assert "+" in summary or "-" in summary


class TestSimulationRoutes:
    """Test simulation REST endpoints."""

    @pytest.mark.asyncio
    async def test_simulate_rule_missing_prompts(self, client: AsyncClient, sim_user):
        """Simulating without test prompts returns validation error."""
        response = await client.post(
            "/api/simulate/rule",
            headers={"X-User-ID": str(sim_user.id)},
            json={
                "draft_rule_content": "Use formal tone",
                "test_prompts": [],
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_simulate_edit_not_found(self, client: AsyncClient, sim_user):
        """Simulating edit for non-existent rule returns 404."""
        response = await client.post(
            "/api/simulate/edit",
            headers={"X-User-ID": str(sim_user.id)},
            json={
                "rule_id": str(uuid4()),
                "new_content": "Use numbered lists instead",
                "test_prompts": ["List some items"],
            },
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_simulate_rule_validation(self, client: AsyncClient, sim_user):
        """Request with valid data passes validation."""
        response = await client.post(
            "/api/simulate/rule",
            headers={"X-User-ID": str(sim_user.id)},
            json={
                "draft_rule_content": "",
                "test_prompts": ["Hello"],
            },
        )
        # Empty content should fail validation
        assert response.status_code == 422
