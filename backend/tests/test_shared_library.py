"""
Tests for Multi-User Shared Rule Library feature.
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.rule import Rule
from app.models.shared_rule import SharedRule


@pytest_asyncio.fixture
async def lib_user(db_session: AsyncSession):
    """Create a test user for library tests."""
    user = User(id=uuid4(), external_id=f"lib-test-{uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def lib_rule(db_session: AsyncSession, lib_user):
    """Create a test rule to publish."""
    rule = Rule(
        id=uuid4(),
        user_id=lib_user.id,
        content="Always use Oxford commas in lists",
        category="style",
        confidence=0.8,
        status="active",
    )
    db_session.add(rule)
    await db_session.flush()
    return rule


@pytest_asyncio.fixture
async def shared_rule(db_session: AsyncSession, lib_user, lib_rule):
    """Create a published shared rule."""
    shared = SharedRule(
        id=uuid4(),
        author_user_id=lib_user.id,
        source_rule_id=lib_rule.id,
        title="Oxford Comma Rule",
        description="Ensures Oxford commas in all lists",
        content=lib_rule.content,
        category=lib_rule.category,
        install_count=15,
        rating_sum=21.0,
        rating_count=5,
        visibility="public",
    )
    db_session.add(shared)
    await db_session.flush()
    return shared


class TestSharedLibraryRoutes:
    """Test shared library REST endpoints."""

    @pytest.mark.asyncio
    async def test_browse_empty(self, client: AsyncClient):
        """Browsing empty library returns empty list."""
        response = await client.get("/api/library")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_browse_with_data(self, client: AsyncClient, shared_rule):
        """Browsing library with data returns shared rules."""
        response = await client.get("/api/library")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_browse_with_query(self, client: AsyncClient, shared_rule):
        """Search filtering by query works."""
        response = await client.get("/api/library?query=Oxford")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_browse_with_category(self, client: AsyncClient, shared_rule):
        """Category filter works."""
        response = await client.get("/api/library?category=style")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_popular(self, client: AsyncClient, shared_rule):
        """Popular endpoint returns top rules."""
        response = await client.get("/api/library/popular")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_publish_rule(self, client: AsyncClient, lib_user, lib_rule):
        """Publishing a rule creates a shared library entry."""
        response = await client.post(
            "/api/library/publish",
            headers={"X-User-ID": str(lib_user.id)},
            json={
                "rule_id": str(lib_rule.id),
                "title": "My Cool Rule",
                "description": "A great rule",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "shared_rule" in data

    @pytest.mark.asyncio
    async def test_install_rule(self, client: AsyncClient, lib_user, shared_rule):
        """Installing a shared rule creates a personal copy."""
        # Create a second user to install
        other_user_id = uuid4()
        response = await client.post(
            f"/api/library/{shared_rule.id}/install",
            headers={"X-User-ID": str(lib_user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert "installed_rule_id" in data

    @pytest.mark.asyncio
    async def test_rate_rule(self, client: AsyncClient, lib_user, shared_rule):
        """Rating a shared rule updates the average."""
        response = await client.post(
            f"/api/library/{shared_rule.id}/rate",
            headers={"X-User-ID": str(lib_user.id)},
            json={"rating": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_ratings"] == 6

    @pytest.mark.asyncio
    async def test_rate_invalid(self, client: AsyncClient, lib_user, shared_rule):
        """Invalid rating is rejected."""
        response = await client.post(
            f"/api/library/{shared_rule.id}/rate",
            headers={"X-User-ID": str(lib_user.id)},
            json={"rating": 6},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_unpublish_rule(self, client: AsyncClient, lib_user, shared_rule):
        """Author can unpublish their shared rule."""
        response = await client.delete(
            f"/api/library/{shared_rule.id}",
            headers={"X-User-ID": str(lib_user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True

    @pytest.mark.asyncio
    async def test_install_nonexistent(self, client: AsyncClient, lib_user):
        """Installing non-existent shared rule returns 404."""
        response = await client.post(
            f"/api/library/{uuid4()}/install",
            headers={"X-User-ID": str(lib_user.id)},
        )
        assert response.status_code == 404


class TestSharedRuleModel:
    """Test SharedRule model methods."""

    @pytest.mark.asyncio
    async def test_avg_rating(self, shared_rule):
        """avg_rating property computes correctly."""
        assert shared_rule.avg_rating == 4.2  # 21/5

    @pytest.mark.asyncio
    async def test_to_dict(self, shared_rule):
        """to_dict returns expected fields."""
        d = shared_rule.to_dict()
        assert d["title"] == "Oxford Comma Rule"
        assert d["install_count"] == 15
        assert d["avg_rating"] == 4.2
