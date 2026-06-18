"""
Personal AI OS - Rule Effectiveness Analytics API Routes
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.effectiveness import (
    RuleEffectivenessResponse,
    EffectivenessReportResponse,
)
from app.dependencies import get_db
from app.services.rule_engine import RuleEngineService
from app.services.effectiveness_service import EffectivenessService


router = APIRouter()


@router.get(
    "/rules/effectiveness",
    response_model=EffectivenessReportResponse,
    summary="Get user-wide rule effectiveness report",
)
async def get_effectiveness_report(
    user_id: str = Query(..., description="External user ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a comprehensive effectiveness report for all of a user's active rules.

    Returns top performing rules, underperformers, stale rules, and
    category-level breakdowns.
    """
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(user_id)

    service = EffectivenessService(db)
    report = await service.get_user_effectiveness_report(user.id)
    return report


@router.get(
    "/rules/{rule_id}/effectiveness",
    response_model=RuleEffectivenessResponse,
    summary="Get effectiveness detail for a single rule",
)
async def get_rule_effectiveness(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Compute detailed effectiveness metrics for a specific rule.

    Returns score (0-100), grade (A-F), trend (improving/declining/stable),
    and apply/reinforce/override counts.
    """
    service = EffectivenessService(db)
    result = await service.get_rule_effectiveness(rule_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result
