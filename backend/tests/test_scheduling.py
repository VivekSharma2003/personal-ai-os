"""
Tests for Rule Scheduling & Time-Awareness (Feature 3).
"""
import uuid
from datetime import datetime, timedelta
import pytest
import pytest_asyncio

from app.models.rule import Rule, RuleStatus
from app.models.rule_schedule import RuleSchedule, ScheduleType
from app.services.scheduling_service import SchedulingService
from app.services.rule_engine import RuleEngineService


@pytest.mark.asyncio
async def test_create_schedule(db_session):
    """Should create a schedule for a rule."""
    # Create a user and rule first
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("schedule_test_user")
    rule = await rule_engine.create_rule(
        user_id=user.id,
        content="Use formal tone during work hours",
        category="tone",
        original_correction="Be more formal",
    )
    await db_session.flush()

    scheduling = SchedulingService(db_session)
    schedule = await scheduling.create_schedule(
        rule_id=rule.id,
        schedule_type=ScheduleType.RECURRING.value,
        cron_expression="09:00-17:00",
        timezone="UTC",
        active_days="31",  # Weekdays only
        description="Active during work hours",
    )

    assert schedule.id is not None
    assert schedule.rule_id == rule.id
    assert schedule.schedule_type == ScheduleType.RECURRING.value
    assert schedule.cron_expression == "09:00-17:00"
    assert schedule.active_days == "31"


@pytest.mark.asyncio
async def test_one_time_schedule_active_within_window(db_session):
    """A one-time schedule should be active when now is within its window."""
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("onetime_schedule_user")
    rule = await rule_engine.create_rule(
        user_id=user.id,
        content="Test one-time schedule",
        category="style",
        original_correction="test",
    )
    await db_session.flush()

    now = datetime.utcnow()
    scheduling = SchedulingService(db_session)
    schedule = await scheduling.create_schedule(
        rule_id=rule.id,
        schedule_type=ScheduleType.ONE_TIME.value,
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=1),
    )
    await db_session.flush()

    is_active = await scheduling.is_rule_active_now(rule.id)
    assert is_active is True


@pytest.mark.asyncio
async def test_one_time_schedule_inactive_outside_window(db_session):
    """A one-time schedule should be inactive when now is outside its window."""
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("expired_schedule_user")
    rule = await rule_engine.create_rule(
        user_id=user.id,
        content="Test expired schedule",
        category="style",
        original_correction="test",
    )
    await db_session.flush()

    now = datetime.utcnow()
    scheduling = SchedulingService(db_session)
    schedule = await scheduling.create_schedule(
        rule_id=rule.id,
        schedule_type=ScheduleType.ONE_TIME.value,
        start_time=now - timedelta(hours=5),
        end_time=now - timedelta(hours=3),  # Ended 3 hours ago
    )
    await db_session.flush()

    is_active = await scheduling.is_rule_active_now(rule.id)
    assert is_active is False


@pytest.mark.asyncio
async def test_no_schedule_means_always_active(db_session):
    """A rule with no schedules should always be considered active."""
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("no_schedule_user")
    rule = await rule_engine.create_rule(
        user_id=user.id,
        content="Always active rule",
        category="style",
        original_correction="test",
    )
    await db_session.flush()

    scheduling = SchedulingService(db_session)
    is_active = await scheduling.is_rule_active_now(rule.id)
    assert is_active is True


@pytest.mark.asyncio
async def test_toggle_schedule(db_session):
    """Toggling a schedule should flip its is_active flag."""
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("toggle_schedule_user")
    rule = await rule_engine.create_rule(
        user_id=user.id,
        content="Toggle test",
        category="style",
        original_correction="test",
    )
    await db_session.flush()

    scheduling = SchedulingService(db_session)
    schedule = await scheduling.create_schedule(
        rule_id=rule.id,
        schedule_type=ScheduleType.RECURRING.value,
        cron_expression="09:00-17:00",
    )
    await db_session.flush()

    assert schedule.is_active is True
    toggled = await scheduling.toggle_schedule(schedule.id)
    assert toggled.is_active is False


@pytest.mark.asyncio
async def test_delete_schedule(db_session):
    """Deleting a schedule should remove it from the database."""
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("delete_schedule_user")
    rule = await rule_engine.create_rule(
        user_id=user.id,
        content="Delete test",
        category="style",
        original_correction="test",
    )
    await db_session.flush()

    scheduling = SchedulingService(db_session)
    schedule = await scheduling.create_schedule(
        rule_id=rule.id,
        schedule_type=ScheduleType.RECURRING.value,
        cron_expression="09:00-17:00",
    )
    await db_session.flush()

    deleted = await scheduling.delete_schedule(schedule.id)
    assert deleted is True

    # Verify it's gone
    result = await scheduling.get_schedule(schedule.id)
    assert result is None
