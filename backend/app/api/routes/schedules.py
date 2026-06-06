"""
Personal AI OS - Schedule API Routes
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.schedules import (
    ScheduleCreateRequest, ScheduleResponse, ScheduleListResponse
)
from app.dependencies import get_db
from app.services.scheduling_service import SchedulingService


router = APIRouter()


@router.post("/rules/{rule_id}/schedules", response_model=ScheduleResponse)
async def create_schedule(
    rule_id: str,
    request: ScheduleCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Attach a time-based schedule to a rule."""
    # Validate rule exists
    from app.services.rule_engine import RuleEngineService
    rule_engine = RuleEngineService(db)
    rule = await rule_engine.get_rule(UUID(rule_id))
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    scheduling = SchedulingService(db)
    schedule = await scheduling.create_schedule(
        rule_id=UUID(rule_id),
        schedule_type=request.schedule_type,
        start_time=request.start_time,
        end_time=request.end_time,
        cron_expression=request.cron_expression,
        timezone=request.timezone,
        active_days=request.active_days,
        description=request.description,
    )

    await db.commit()
    return ScheduleResponse(**schedule.to_dict())


@router.get("/rules/{rule_id}/schedules", response_model=ScheduleListResponse)
async def list_schedules(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all schedules for a rule."""
    scheduling = SchedulingService(db)
    schedules = await scheduling.get_schedules_for_rule(UUID(rule_id))

    return ScheduleListResponse(
        schedules=[ScheduleResponse(**s.to_dict()) for s in schedules],
        total=len(schedules),
        rule_id=rule_id,
    )


@router.get("/rules/{rule_id}/active-now")
async def check_rule_active(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Check if a rule is currently active based on its schedules."""
    scheduling = SchedulingService(db)
    is_active = await scheduling.is_rule_active_now(UUID(rule_id))

    return {
        "rule_id": rule_id,
        "is_active_now": is_active,
    }


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a rule schedule."""
    scheduling = SchedulingService(db)
    deleted = await scheduling.delete_schedule(UUID(schedule_id))

    if not deleted:
        raise HTTPException(status_code=404, detail="Schedule not found")

    await db.commit()
    return {"status": "deleted", "schedule_id": schedule_id}


@router.patch("/schedules/{schedule_id}/toggle", response_model=ScheduleResponse)
async def toggle_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Toggle a schedule's active state."""
    scheduling = SchedulingService(db)
    schedule = await scheduling.toggle_schedule(UUID(schedule_id))

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    await db.commit()
    return ScheduleResponse(**schedule.to_dict())
