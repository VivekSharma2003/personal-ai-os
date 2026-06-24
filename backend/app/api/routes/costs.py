"""
Personal AI OS - Cost Routes

REST endpoints for LLM cost tracking and budget management.
"""
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.dependencies import get_db
from app.services.cost_service import CostService

router = APIRouter()


def _get_user_id(x_user_id: str = Header(...)) -> UUID:
    return UUID(x_user_id)


@router.get("/costs")
async def get_usage_summary(
    period: str = Query(default="month", regex="^(day|week|month)$"),
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated LLM usage summary for a period."""
    service = CostService(db)
    return await service.get_usage_summary(user_id, period)


@router.get("/costs/trend")
async def get_cost_trend(
    days: int = Query(default=30, ge=1, le=365),
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get daily cost time-series for the last N days."""
    service = CostService(db)
    trend = await service.get_cost_trend(user_id, days)
    return {"days": days, "trend": trend}


@router.get("/costs/breakdown")
async def get_cost_breakdown(
    period: str = Query(default="month", regex="^(day|week|month)$"),
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get per-endpoint cost breakdown."""
    service = CostService(db)
    return await service.get_cost_breakdown(user_id, period)


@router.get("/costs/budget")
async def get_budget(
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get current budget limits and spend status."""
    service = CostService(db)
    return await service.get_budget(user_id)


@router.get("/costs/budget/check")
async def check_budget(
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Pre-flight budget check — is the user allowed to make LLM calls?"""
    service = CostService(db)
    return await service.check_budget(user_id)
