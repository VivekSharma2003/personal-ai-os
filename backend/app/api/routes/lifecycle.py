"""
Personal AI OS - Lifecycle Routes

REST endpoints for rule lifecycle management.
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.dependencies import get_db
from app.services.lifecycle_service import LifecycleService

router = APIRouter()


def _get_user_id(x_user_id: str = Header(...)) -> UUID:
    return UUID(x_user_id)


@router.get("/rules/lifecycle")
async def get_lifecycle_report(
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get user-wide rule lifecycle analytics."""
    service = LifecycleService(db)
    return await service.get_lifecycle_report(user_id)


@router.get("/rules/{rule_id}/timeline")
async def get_rule_timeline(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get chronological lifecycle timeline for a specific rule."""
    service = LifecycleService(db)
    return {"timeline": await service.get_rule_timeline(rule_id)}


@router.post("/rules/lifecycle/scan")
async def trigger_stale_scan(
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger stale rule scan and auto-archive."""
    service = LifecycleService(db)
    report = await service.auto_archive(user_id)
    await db.commit()
    return report


@router.post("/rules/{rule_id}/resurrect")
async def resurrect_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Resurrect an archived rule back to active status."""
    service = LifecycleService(db)
    try:
        result = await service.resurrect_rule(rule_id)
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
