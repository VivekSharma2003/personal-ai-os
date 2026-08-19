"""
Personal AI OS - Cost Optimization Routes
"""
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.user import User
from app.services.rule_engine import RuleEngineService
from app.services.cost_optimizer import CostOptimizerService
from app.api.schemas.cost_optimization import (
    ReviewSavingsResponse,
    PruneRulesRequest,
    PruneRulesResponse
)

router = APIRouter(prefix="/api/analytics/cost-optimization", tags=["Cost Optimization"])


async def get_current_user_from_header(
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
) -> User:
    service = RuleEngineService(db)
    return await service.get_or_create_user(x_user_id)


@router.get("", response_model=ReviewSavingsResponse)
async def review_cost_savings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header)
):
    """Review potential prompt token savings by identifying low-efficiency rules."""
    optimizer = CostOptimizerService(db)
    return await optimizer.review_savings(current_user.id)


@router.post("/prune", response_model=PruneRulesResponse)
async def prune_rules_test(
    request: PruneRulesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header)
):
    """Test pruning behavior on rules to fit within max_tokens context limit."""
    optimizer = CostOptimizerService(db)
    return await optimizer.prune_rules(current_user.id, request.max_tokens)
