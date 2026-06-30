"""
Tests for Rule Auto-Archival & Lifecycle Manager.
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timedelta

from app.models.user import User
from app.models.rule import Rule, RuleStatus
from app.services.lifecycle_service import LifecycleService


@pytest_asyncio.fixture
async def lc_user(db_session):
    """Create a test user."""
    user = User(external_id=f"lc_test_{uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.mark.asyncio
async def test_lifecycle_scan_and_archive(db_session, lc_user):
    """Test scanning for stale rules and auto-archival."""
    service = LifecycleService(db_session)

    # 1. Create a stale rule (confidence < 0.4 and last_applied_at in the past or None)
    stale_rule = Rule(
        user_id=lc_user.id,
        content="Stale rule content",
        category="style",
        status=RuleStatus.ACTIVE.value,
        confidence=0.2,
        last_applied_at=datetime.utcnow() - timedelta(days=40),
    )

    # 2. Create a fresh rule (confidence > 0.4 or last_applied_at is recent)
    fresh_rule = Rule(
        user_id=lc_user.id,
        content="Fresh rule content",
        category="style",
        status=RuleStatus.ACTIVE.value,
        confidence=0.8,
        last_applied_at=datetime.utcnow(),
    )

    db_session.add(stale_rule)
    db_session.add(fresh_rule)
    await db_session.flush()

    # Scan for stale rules
    stale_list = await service.scan_for_stale_rules(lc_user.id, inactive_days=30)
    assert len(stale_list) == 1
    assert stale_list[0]["id"] == str(stale_rule.id)

    # Auto-archive
    report = await service.auto_archive(lc_user.id)
    assert report["archived_count"] == 1
    assert str(stale_rule.id) in report["archived_rule_ids"]

    # Verify status in DB
    await db_session.refresh(stale_rule)
    assert stale_rule.status == RuleStatus.ARCHIVED.value

    # Resurrect rule
    resurrected = await service.resurrect_rule(stale_rule.id)
    assert resurrected["status"] == RuleStatus.ACTIVE.value
    assert resurrected["confidence"] > 0.2


@pytest.mark.asyncio
async def test_lifecycle_routes(client, db_session, lc_user):
    """Test lifecycle HTTP endpoints."""
    headers = {"X-User-ID": str(lc_user.id)}

    # Get lifecycle report
    response = await client.get("/api/rules/lifecycle", headers=headers)
    print("DEBUG RESPONSE:", response.json())
    assert response.status_code == 200
    data = response.json()
    assert "status_counts" in data
    assert "avg_age_days" in data

    # Trigger scan
    response = await client.post("/api/rules/lifecycle/scan?inactive_days=30", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
