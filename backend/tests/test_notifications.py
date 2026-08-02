"""
Tests for Rule Change Notifications & Digest feature.
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.notification import Notification
from app.models.audit_log import AuditLog


@pytest_asyncio.fixture
async def notif_user(db_session: AsyncSession):
    """Create a test user for notification tests."""
    user = User(id=uuid4(), external_id=f"notif-test-{uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def notifications(db_session: AsyncSession, notif_user):
    """Create test notifications."""
    items = []
    types = ["rule_created", "conflict_detected", "decay_warning", "rule_archived", "system"]
    for i, ntype in enumerate(types):
        notif = Notification(
            id=uuid4(),
            user_id=notif_user.id,
            type=ntype,
            title=f"Test Notification #{i}",
            body=f"Body of notification #{i}",
            extra_data={"index": i},
            is_read=(i >= 3),  # First 3 unread, last 2 read
        )
        db_session.add(notif)
        items.append(notif)
    await db_session.flush()
    return items


class TestNotificationRoutes:
    """Test notification REST endpoints."""

    @pytest.mark.asyncio
    async def test_list_notifications(self, client: AsyncClient, notif_user, notifications):
        """Listing notifications returns items."""
        response = await client.get(
            "/api/notifications",
            headers={"X-User-ID": str(notif_user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["notifications"]) == 5

    @pytest.mark.asyncio
    async def test_list_unread_only(self, client: AsyncClient, notif_user, notifications):
        """Filtering for unread only works."""
        response = await client.get(
            "/api/notifications?unread_only=true",
            headers={"X-User-ID": str(notif_user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_list_by_type(self, client: AsyncClient, notif_user, notifications):
        """Type filter works."""
        response = await client.get(
            "/api/notifications?type_filter=rule_created",
            headers={"X-User-ID": str(notif_user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_unread_count(self, client: AsyncClient, notif_user, notifications):
        """Unread count returns correct number."""
        response = await client.get(
            "/api/notifications/unread-count",
            headers={"X-User-ID": str(notif_user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["unread_count"] == 3
        assert "by_type" in data

    @pytest.mark.asyncio
    async def test_mark_read(self, client: AsyncClient, notif_user, notifications):
        """Marking a notification as read works."""
        unread_notif = notifications[0]
        response = await client.patch(
            f"/api/notifications/{unread_notif.id}/read",
            headers={"X-User-ID": str(notif_user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["marked_read"] is True

    @pytest.mark.asyncio
    async def test_mark_read_not_found(self, client: AsyncClient, notif_user):
        """Marking non-existent notification returns 404."""
        response = await client.patch(
            f"/api/notifications/{uuid4()}/read",
            headers={"X-User-ID": str(notif_user.id)},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_mark_all_read(self, client: AsyncClient, notif_user, notifications):
        """Marking all as read updates all unread notifications."""
        response = await client.patch(
            "/api/notifications/read-all",
            headers={"X-User-ID": str(notif_user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["marked_read"] == 3

    @pytest.mark.asyncio
    async def test_delete_notification(self, client: AsyncClient, notif_user, notifications):
        """Deleting a notification archives it."""
        response = await client.delete(
            f"/api/notifications/{notifications[0].id}",
            headers={"X-User-ID": str(notif_user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, notif_user):
        """Deleting non-existent notification returns 404."""
        response = await client.delete(
            f"/api/notifications/{uuid4()}",
            headers={"X-User-ID": str(notif_user.id)},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_digest_no_activity(self, client: AsyncClient, notif_user):
        """Digest with no audit events returns stable message."""
        response = await client.get(
            "/api/notifications/digest",
            headers={"X-User-ID": str(notif_user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["event_count"] == 0
        assert "stable" in data["digest"].lower() or "no" in data["digest"].lower()


class TestNotificationModel:
    """Test Notification model methods."""

    @pytest.mark.asyncio
    async def test_to_dict(self, notifications):
        """to_dict returns expected fields."""
        d = notifications[0].to_dict()
        assert d["type"] == "rule_created"
        assert d["is_read"] is False
        assert "id" in d
        assert "title" in d
