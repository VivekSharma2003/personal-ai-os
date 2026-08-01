"""
Personal AI OS - Self-Healing Routes

REST API routes for dynamic rule adherence evaluation and automated self-healing.
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from app.dependencies import get_db
from app.services.self_healing_service import SelfHealingService
from app.api.schemas.self_healing import AdherenceEvaluationResponse, RuleAdherenceStat, HealedRuleResponse

router = APIRouter()


def _get_user_id(x_user_id: str = Header(...)) -> UUID:
    return UUID(x_user_id)


@router.post("/evaluations/evaluate/{interaction_id}", response_model=dict)
async def evaluate_interaction(
    interaction_id: UUID,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Judge and store rule compliance metrics for a specific user interaction response."""
    service = SelfHealingService(db)
    result = await service.evaluate_interaction(interaction_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/evaluations/stats", response_model=List[RuleAdherenceStat])
async def get_adherence_stats(
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve adherence score breakdowns and evaluation frequencies across all active rules."""
    service = SelfHealingService(db)
    return await service.get_adherence_stats(user_id)


@router.post("/evaluations/heal/{rule_id}", response_model=dict)
async def heal_rule(
    rule_id: UUID,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Trigger the LLM self-healing optimization to automatically refine and clarify a rule with low adherence."""
    service = SelfHealingService(db)
    result = await service.heal_rule(rule_id, user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
