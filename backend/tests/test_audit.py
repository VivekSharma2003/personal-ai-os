"""
Tests for Audit Trail REST API (Feature 4).
"""
import pytest
import pytest_asyncio

from app.models.audit_log import AuditLog, AuditEventType
from app.services.audit_service import AuditService
from app.services.rule_engine import RuleEngineService


@pytest.mark.asyncio
async def test_list_audit_logs_paginated(db_session):
    """Should return paginated audit logs."""
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("audit_test_user")

    # Create a rule to generate audit logs
    rule = await rule_engine.create_rule(
        user_id=user.id,
        content="Audit test rule",
        category="style",
        original_correction="test",
    )
    await db_session.flush()

    audit_service = AuditService(db_session)
    logs, total = await audit_service.list_logs(
        user_id=user.id,
        page=1,
        page_size=10,
    )

    assert total >= 1  # At least the rule_created event
    assert len(logs) >= 1
    assert logs[0].event_type == AuditEventType.RULE_CREATED.value


@pytest.mark.asyncio
async def test_list_audit_logs_filter_by_event_type(db_session):
    """Should filter audit logs by event type."""
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("audit_filter_user")

    await rule_engine.create_rule(
        user_id=user.id,
        content="Filter test rule",
        category="style",
        original_correction="test",
    )
    await db_session.flush()

    audit_service = AuditService(db_session)

    # Filter by rule_created
    logs, total = await audit_service.list_logs(
        user_id=user.id,
        event_type="rule_created",
    )
    assert total >= 1
    for log in logs:
        assert log.event_type == "rule_created"

    # Filter by non-existent type
    logs, total = await audit_service.list_logs(
        user_id=user.id,
        event_type="nonexistent_event",
    )
    assert total == 0


@pytest.mark.asyncio
async def test_get_audit_stats(db_session):
    """Should return aggregate statistics."""
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("audit_stats_user")

    await rule_engine.create_rule(
        user_id=user.id,
        content="Stats test rule",
        category="style",
        original_correction="test",
    )
    await db_session.flush()

    audit_service = AuditService(db_session)
    stats = await audit_service.get_stats(user_id=user.id)

    assert stats["total_events"] >= 1
    assert "rule_created" in stats["event_counts"]
    assert stats["most_recent"] is not None


@pytest.mark.asyncio
async def test_export_csv(db_session):
    """Should export audit logs as valid CSV."""
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("audit_csv_user")

    await rule_engine.create_rule(
        user_id=user.id,
        content="CSV test rule",
        category="style",
        original_correction="test",
    )
    await db_session.flush()

    audit_service = AuditService(db_session)
    csv_content = await audit_service.export_csv(user_id=user.id)

    assert "id,rule_id,event_type,event_data,created_at" in csv_content
    assert "rule_created" in csv_content


@pytest.mark.asyncio
async def test_audit_api_endpoint(client):
    """The /api/audit endpoint should return paginated logs."""
    # First create a rule (which generates audit logs)
    response = await client.get(
        "/api/audit",
        params={"user_id": "audit_api_user", "page": 1, "page_size": 10},
    )

    assert response.status_code == 200
    data = response.json()
    assert "logs" in data
    assert "total" in data
    assert "page" in data
