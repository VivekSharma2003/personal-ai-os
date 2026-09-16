"""
Personal AI OS - A/B Testing Routes
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.dependencies import get_db
from app.services.ab_testing import ABTestingService
from app.services.rule_engine import RuleEngineService
from app.api.schemas.ab_testing import (
    CreateExperimentRequest,
    RecordResultRequest,
    VariantStats,
)

router = APIRouter(prefix="/api/ab-testing", tags=["A/B Testing"])


async def _get_user(x_user_id: str = Header(..., alias="X-User-ID"), db: AsyncSession = Depends(get_db)):
    return await RuleEngineService(db).get_or_create_user(x_user_id)


@router.post("/experiments")
async def create_experiment(
    request: CreateExperimentRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_user),
):
    """Create a new A/B prompt experiment."""
    service = ABTestingService(db)
    experiment = await service.create_experiment(
        user_id=current_user.id,
        name=request.name,
        variants=[v.model_dump() for v in request.variants],
    )
    return {"experiment_id": str(experiment.id), "name": experiment.name}


@router.get("/experiments/{experiment_id}/variant")
async def select_variant(
    experiment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Randomly serve one variant from the experiment."""
    service = ABTestingService(db)
    variant = await service.select_variant(experiment_id)
    if not variant:
        raise HTTPException(status_code=404, detail="No variants found for this experiment.")
    return {"variant_id": str(variant.id), "label": variant.label, "prompt_template": variant.prompt_template}


@router.post("/results")
async def record_result(
    request: RecordResultRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_user),
):
    """Record a user score for a variant."""
    service = ABTestingService(db)
    result = await service.record_result(
        variant_id=request.variant_id,
        user_id=current_user.id,
        score=request.score,
        feedback=request.feedback,
    )
    return {"result_id": str(result.id), "score": result.score}


@router.get("/experiments/{experiment_id}/stats", response_model=List[VariantStats])
async def get_stats(experiment_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get aggregated stats (avg score, response count) per variant."""
    service = ABTestingService(db)
    return await service.get_experiment_stats(experiment_id)
