"""
Personal AI OS - Scheduling Service

Manages rule schedules and determines if a rule is currently active
based on its time-based schedules.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule_schedule import RuleSchedule, ScheduleType


# Day bitmask constants
DAY_BITS = {
    0: 1,   # Monday
    1: 2,   # Tuesday
    2: 4,   # Wednesday
    3: 8,   # Thursday
    4: 16,  # Friday
    5: 32,  # Saturday
    6: 64,  # Sunday
}


class SchedulingService:
    """Service for managing rule schedules and time-based rule activation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_schedule(
        self,
        rule_id: UUID,
        schedule_type: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        cron_expression: Optional[str] = None,
        timezone: str = "UTC",
        active_days: str = "127",
        description: Optional[str] = None,
    ) -> RuleSchedule:
        """
        Create a new schedule for a rule.

        Args:
            rule_id: UUID of the rule to schedule.
            schedule_type: "one_time" or "recurring".
            start_time: Start of one-time window (required for one_time).
            end_time: End of one-time window (required for one_time).
            cron_expression: Daily time window "HH:MM-HH:MM" for recurring.
            timezone: IANA timezone string.
            active_days: Bitmask string for active days (127 = all).
            description: Human-readable description.

        Returns:
            Created RuleSchedule.
        """
        schedule = RuleSchedule(
            rule_id=rule_id,
            schedule_type=schedule_type,
            start_time=start_time,
            end_time=end_time,
            cron_expression=cron_expression,
            timezone=timezone,
            active_days=active_days,
            description=description,
            is_active=True,
        )

        self.db.add(schedule)
        await self.db.flush()
        return schedule

    async def get_schedule(self, schedule_id: UUID) -> Optional[RuleSchedule]:
        """Get a schedule by ID."""
        result = await self.db.execute(
            select(RuleSchedule).where(RuleSchedule.id == schedule_id)
        )
        return result.scalar_one_or_none()

    async def get_schedules_for_rule(self, rule_id: UUID) -> List[RuleSchedule]:
        """Get all schedules for a rule."""
        result = await self.db.execute(
            select(RuleSchedule)
            .where(RuleSchedule.rule_id == rule_id)
            .order_by(RuleSchedule.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_schedule(self, schedule_id: UUID) -> bool:
        """Delete a schedule."""
        schedule = await self.get_schedule(schedule_id)
        if not schedule:
            return False
        await self.db.delete(schedule)
        return True

    async def toggle_schedule(self, schedule_id: UUID) -> Optional[RuleSchedule]:
        """Toggle a schedule's active state."""
        schedule = await self.get_schedule(schedule_id)
        if not schedule:
            return None
        schedule.is_active = not schedule.is_active
        schedule.updated_at = datetime.utcnow()
        return schedule

    async def is_rule_active_now(self, rule_id: UUID) -> bool:
        """
        Check if a rule is currently within any of its active schedule windows.

        A rule with NO schedules is always active (schedules are opt-in).
        A rule with schedules is active if ANY schedule says it's currently active.

        Returns:
            True if the rule should be active now.
        """
        schedules = await self.get_schedules_for_rule(rule_id)

        # No schedules = always active
        if not schedules:
            return True

        # Filter to enabled schedules only
        active_schedules = [s for s in schedules if s.is_active]
        if not active_schedules:
            return True  # All schedules disabled = treat as always active

        now = datetime.utcnow()

        for schedule in active_schedules:
            if self._is_within_window(schedule, now):
                return True

        return False

    def _is_within_window(self, schedule: RuleSchedule, now: datetime) -> bool:
        """Check if the current time falls within a schedule's window."""
        if schedule.schedule_type == ScheduleType.ONE_TIME.value:
            return self._check_one_time(schedule, now)
        elif schedule.schedule_type == ScheduleType.RECURRING.value:
            return self._check_recurring(schedule, now)
        return False

    def _check_one_time(self, schedule: RuleSchedule, now: datetime) -> bool:
        """Check a one-time schedule window."""
        if not schedule.start_time or not schedule.end_time:
            return False
        return schedule.start_time <= now <= schedule.end_time

    def _check_recurring(self, schedule: RuleSchedule, now: datetime) -> bool:
        """
        Check a recurring schedule.

        Uses the `active_days` bitmask and `cron_expression` as "HH:MM-HH:MM".
        """
        # Check day of week
        day_bit = DAY_BITS.get(now.weekday(), 0)
        try:
            active_days_mask = int(schedule.active_days or "127")
        except ValueError:
            active_days_mask = 127

        if not (active_days_mask & day_bit):
            return False  # Not an active day

        # Check time window from cron_expression (format: "HH:MM-HH:MM")
        if not schedule.cron_expression:
            return True  # No time restriction, day match is sufficient

        try:
            start_str, end_str = schedule.cron_expression.split("-")
            start_h, start_m = map(int, start_str.strip().split(":"))
            end_h, end_m = map(int, end_str.strip().split(":"))

            current_minutes = now.hour * 60 + now.minute
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m

            if start_minutes <= end_minutes:
                return start_minutes <= current_minutes <= end_minutes
            else:
                # Overnight window (e.g., "22:00-06:00")
                return current_minutes >= start_minutes or current_minutes <= end_minutes
        except (ValueError, AttributeError):
            return True  # Invalid expression — default to active

    async def get_active_rule_ids(self, rule_ids: List[UUID]) -> List[UUID]:
        """
        Given a list of rule IDs, return only those currently active.

        Optimized batch check to avoid N+1 queries.
        """
        if not rule_ids:
            return []

        result = await self.db.execute(
            select(RuleSchedule)
            .where(
                RuleSchedule.rule_id.in_(rule_ids),
                RuleSchedule.is_active.is_(True),
            )
        )
        schedules = list(result.scalars().all())

        # Group schedules by rule_id
        rule_schedules: dict[UUID, list[RuleSchedule]] = {}
        for s in schedules:
            rule_schedules.setdefault(s.rule_id, []).append(s)

        now = datetime.utcnow()
        active_ids = []

        for rule_id in rule_ids:
            if rule_id not in rule_schedules:
                # No schedules = always active
                active_ids.append(rule_id)
            else:
                # Has schedules — check if any window is active now
                for schedule in rule_schedules[rule_id]:
                    if self._is_within_window(schedule, now):
                        active_ids.append(rule_id)
                        break

        return active_ids
