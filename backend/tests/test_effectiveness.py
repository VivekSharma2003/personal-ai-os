"""
Tests for Rule Effectiveness Analytics.
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime

from app.models.rule import Rule, RuleStatus
from app.models.audit_log import AuditLog, AuditEventType
from app.models.user import User
from app.services.effectiveness_service import EffectivenessService


@pytest_asyncio.fixture
async def user_with_rules(db_session):
    """Create a user with rules and audit events for effectiveness testing."""
    user = User(external_id=f"eff_test_{uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()

    # Create two rules
    rule_good = Rule(
        user_id=user.id,
        content="Use bullet points for lists",
        category="formatting",
        confidence=0.8,
        status=RuleStatus.ACTIVE.value,
        times_applied=10,
        times_reinforced=5,
    )
    rule_bad = Rule(
        user_id=user.id,
        content="Always use emojis",
        category="style",
        confidence=0.3,
        status=RuleStatus.ACTIVE.value,
        times_applied=3,
        times_reinforced=0,
    )
    db_session.add_all([rule_good, rule_bad])
    await db_session.flush()

    # Add audit events for rule_good (many applies + reinforcements)
    for _ in range(10):
        db_session.add(AuditLog(
            user_id=user.id,
            rule_id=rule_good.id,
            event_type=AuditEventType.RULE_APPLIED.value,
            event_data={},
        ))
    for _ in range(5):
        db_session.add(AuditLog(
            user_id=user.id,
            rule_id=rule_good.id,
            event_type=AuditEventType.RULE_REINFORCED.value,
            event_data={},
        ))

    # Add audit events for rule_bad (few applies, edited = override)
    for _ in range(3):
        db_session.add(AuditLog(
            user_id=user.id,
            rule_id=rule_bad.id,
            event_type=AuditEventType.RULE_APPLIED.value,
            event_data={},
        ))
    db_session.add(AuditLog(
        user_id=user.id,
        rule_id=rule_bad.id,
        event_type=AuditEventType.RULE_EDITED.value,
        event_data={},
    ))

    await db_session.flush()
    return user, rule_good, rule_bad


@pytest.mark.asyncio
async def test_single_rule_effectiveness(db_session, user_with_rules):
    """Test that a well-reinforced rule gets a high score."""
    user, rule_good, _ = user_with_rules
    service = EffectivenessService(db_session)

    result = await service.get_rule_effectiveness(rule_good.id)

    assert "error" not in result
    assert result["apply_count"] == 10
    assert result["reinforce_count"] == 5
    assert result["score"] > 0
    assert result["grade"] in ("A", "B", "C", "D", "F")
    assert result["trend"] in ("improving", "declining", "stable")


@pytest.mark.asyncio
async def test_bad_rule_scores_lower(db_session, user_with_rules):
    """Test that a rule with overrides scores lower than a reinforced one."""
    user, rule_good, rule_bad = user_with_rules
    service = EffectivenessService(db_session)

    good_result = await service.get_rule_effectiveness(rule_good.id)
    bad_result = await service.get_rule_effectiveness(rule_bad.id)

    # Good rule should score higher (more reinforcements, no overrides)
    assert good_result["score"] > bad_result["score"]


@pytest.mark.asyncio
async def test_effectiveness_report(db_session, user_with_rules):
    """Test the user-wide effectiveness report."""
    user, _, _ = user_with_rules
    service = EffectivenessService(db_session)

    report = await service.get_user_effectiveness_report(user.id)

    assert report["total_rules"] == 2
    assert report["average_score"] > 0
    assert len(report["top_rules"]) > 0
    assert "category_breakdown" in report


@pytest.mark.asyncio
async def test_nonexistent_rule_returns_error(db_session):
    """Test effectiveness for a non-existent rule."""
    service = EffectivenessService(db_session)
    result = await service.get_rule_effectiveness(uuid4())
    assert "error" in result
