"""
Personal AI OS - Analytics API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.analytics import AnalyticsResponse
from app.dependencies import get_db
from app.services.analytics import AnalyticsService
from app.services.rule_engine import RuleEngineService


router = APIRouter()


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    user_id: str = Query(..., description="External user ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated analytics for a user.

    Returns usage statistics including:
    - Total conversations, messages, rules, corrections
    - Correction rate and average rules applied per chat
    - Daily activity for the last 30 days
    - Rule category breakdown
    - Most-applied rule
    """
    rule_engine = RuleEngineService(db)
    analytics = AnalyticsService(db)

    try:
        user = await rule_engine.get_or_create_user(user_id)
        result = await analytics.get_analytics(user.id)
        return AnalyticsResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
