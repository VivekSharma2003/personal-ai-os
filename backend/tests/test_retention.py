"""
Tests for Data Retention Policies.
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timedelta

from app.models.user import User
from app.models.interaction import Interaction
from app.models.audit_log import AuditLog, AuditEventType
from app.services.retention_service import RetentionService


@pytest_asyncio.fixture
async def retention_user(db_session):
    """Create a user with old and new records for retention testing."""
    user = User(external_id=f"retention_test_{uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()

    # Create some interactions — old ones and new ones
    old_date = datetime.utcnow() - timedelta(days=120)
    new_date = datetime.utcnow() - timedelta(days=5)

    for _ in range(3):
        db_session.add(Interaction(
            user_id=user.id,
            user_message="old message",
            assistant_response="old response",
            created_at=old_date,
        ))

    for _ in range(2):
        db_session.add(Interaction(
            user_id=user.id,
            user_message="new message",
            assistant_response="new response",
            created_at=new_date,
        ))

    # Create some audit logs — old and new
    for _ in range(4):
        db_session.add(AuditLog(
            user_id=user.id,
            event_type=AuditEventType.RULE_APPLIED.value,
            event_data={},
            created_at=old_date,
        ))

    for _ in range(2):
        db_session.add(AuditLog(
            user_id=user.id,
            event_type=AuditEventType.RULE_CREATED.value,
            event_data={},
            created_at=new_date,
        ))

    await db_session.flush()
    return user


@pytest.mark.asyncio
async def test_get_default_policies(db_session, retention_user):
    """Test that default policies are returned when no custom ones exist."""
    service = RetentionService(db_session)
    policies = await service.get_policies(retention_user.id)

    assert len(policies) == 3
    types = {p["resource_type"] for p in policies}
    assert types == {"interactions", "audit_logs", "conversations"}

    # All should be system defaults
    for p in policies:
        assert p["is_custom"] is False


@pytest.mark.asyncio
async def test_set_custom_policy(db_session, retention_user):
    """Test creating a custom retention policy."""
    service = RetentionService(db_session)

    policy = await service.set_policy(
        user_id=retention_user.id,
        resource_type="interactions",
        retention_days=30,
    )

    assert policy.retention_days == 30
    assert policy.resource_type == "interactions"

    # Verify it shows up in get_policies
    policies = await service.get_policies(retention_user.id)
    interactions_policy = next(
        p for p in policies if p["resource_type"] == "interactions"
    )
    assert interactions_policy["retention_days"] == 30
    assert interactions_policy["is_custom"] is True


@pytest.mark.asyncio
async def test_invalid_resource_type_raises(db_session, retention_user):
    """Test that an invalid resource type raises ValueError."""
    service = RetentionService(db_session)

    with pytest.raises(ValueError, match="Invalid resource_type"):
        await service.set_policy(
            user_id=retention_user.id,
            resource_type="nonexistent",
            retention_days=30,
        )


@pytest.mark.asyncio
async def test_preview_cleanup(db_session, retention_user):
    """Test dry-run cleanup preview."""
    service = RetentionService(db_session)

    # Set a short retention period for interactions
    await service.set_policy(retention_user.id, "interactions", 30)

    preview = await service.preview_cleanup(retention_user.id)

    # Should find the 3 old interactions (120 days old > 30 day retention)
    assert preview["interactions"] == 3


@pytest.mark.asyncio
async def test_execute_cleanup(db_session, retention_user):
    """Test that cleanup actually deletes old records."""
    service = RetentionService(db_session)

    # Set short retention
    await service.set_policy(retention_user.id, "interactions", 30)

    # Execute cleanup
    result = await service.execute_cleanup(retention_user.id)
    assert result["interactions"] == 3

    # Verify new records remain
    stats = await service.get_storage_stats(retention_user.id)
    assert stats["interactions"]["total_records"] == 2


@pytest.mark.asyncio
async def test_zero_retention_keeps_forever(db_session, retention_user):
    """Test that retention_days=0 means keep forever."""
    service = RetentionService(db_session)

    await service.set_policy(retention_user.id, "interactions", 0)

    preview = await service.preview_cleanup(retention_user.id)
    assert preview["interactions"] == 0  # Nothing should be deleted


@pytest.mark.asyncio
async def test_storage_stats(db_session, retention_user):
    """Test storage stats endpoint."""
    service = RetentionService(db_session)
    stats = await service.get_storage_stats(retention_user.id)

    assert stats["interactions"]["total_records"] == 5
    assert stats["audit_logs"]["total_records"] == 6
    assert stats["interactions"]["oldest_record"] is not None
