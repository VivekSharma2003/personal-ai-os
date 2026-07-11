"""
Tests for Rule Similarity Clusters feature.
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.rule import Rule
from app.models.rule_cluster import RuleCluster, rule_cluster_members


@pytest_asyncio.fixture
async def cluster_user(db_session: AsyncSession):
    """Create a test user for cluster tests."""
    user = User(id=uuid4(), external_id=f"cluster-test-{uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def cluster_rules(db_session: AsyncSession, cluster_user):
    """Create multiple rules for clustering."""
    rules = []
    for i in range(5):
        rule = Rule(
            id=uuid4(),
            user_id=cluster_user.id,
            content=f"Test rule content #{i}",
            category="style",
            confidence=0.7,
            status="active",
        )
        db_session.add(rule)
        rules.append(rule)
    await db_session.flush()
    return rules


@pytest_asyncio.fixture
async def cluster_with_rules(db_session: AsyncSession, cluster_user, cluster_rules):
    """Create a cluster with rules assigned."""
    cluster = RuleCluster(
        id=uuid4(),
        user_id=cluster_user.id,
        name="Test Style Cluster",
        description="Test cluster for style rules",
        rule_count=len(cluster_rules),
        avg_similarity=0.85,
    )
    db_session.add(cluster)
    await db_session.flush()

    for rule in cluster_rules:
        await db_session.execute(
            rule_cluster_members.insert().values(
                cluster_id=cluster.id,
                rule_id=rule.id,
                similarity_to_centroid=0.85,
            )
        )
    await db_session.flush()
    return cluster


class TestClusterRoutes:
    """Test cluster REST endpoints."""

    @pytest.mark.asyncio
    async def test_list_clusters_empty(self, client: AsyncClient, cluster_user):
        """Listing clusters for a user with no clusters returns empty list."""
        response = await client.get(
            "/api/clusters",
            headers={"X-User-ID": str(cluster_user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["clusters"] == []

    @pytest.mark.asyncio
    async def test_list_clusters_with_data(
        self, client: AsyncClient, cluster_user, cluster_with_rules
    ):
        """Listing clusters returns existing clusters."""
        response = await client.get(
            "/api/clusters",
            headers={"X-User-ID": str(cluster_user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(c["name"] == "Test Style Cluster" for c in data["clusters"])

    @pytest.mark.asyncio
    async def test_get_cluster_detail(
        self, client: AsyncClient, cluster_user, cluster_with_rules
    ):
        """Getting cluster detail returns member rules."""
        response = await client.get(
            f"/api/clusters/{cluster_with_rules.id}",
            headers={"X-User-ID": str(cluster_user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Style Cluster"
        assert len(data["rules"]) == 5

    @pytest.mark.asyncio
    async def test_get_cluster_not_found(self, client: AsyncClient, cluster_user):
        """Getting non-existent cluster returns 404."""
        response = await client.get(
            f"/api/clusters/{uuid4()}",
            headers={"X-User-ID": str(cluster_user.id)},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_clusters_insufficient_rules(
        self, client: AsyncClient, cluster_user
    ):
        """Generating clusters with fewer than 2 rules returns message."""
        response = await client.post(
            "/api/clusters/generate",
            headers={"X-User-ID": str(cluster_user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["clusters_created"] == 0


class TestRuleClusterModel:
    """Test RuleCluster model methods."""

    @pytest.mark.asyncio
    async def test_to_dict(self, cluster_with_rules):
        """to_dict returns expected fields."""
        d = cluster_with_rules.to_dict()
        assert d["name"] == "Test Style Cluster"
        assert d["rule_count"] == 5
        assert d["avg_similarity"] == 0.85
        assert "id" in d
        assert "user_id" in d
