"""
Personal AI OS - Experiment Routes

REST endpoints for rule A/B testing.
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.dependencies import get_db
from app.services.experiment_service import ExperimentService
from app.api.schemas.experiments import CreateExperimentRequest, RecordOutcomeRequest

router = APIRouter()


def _get_user_id(x_user_id: str = Header(...)) -> UUID:
    return UUID(x_user_id)


@router.post("/experiments")
async def create_experiment(
    body: CreateExperimentRequest,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new A/B experiment between two rule variants."""
    service = ExperimentService(db)
    try:
        experiment = await service.create_experiment(
            user_id=user_id,
            name=body.name,
            rule_a_id=UUID(body.rule_a_id),
            rule_b_id=UUID(body.rule_b_id),
            min_sample_size=body.min_sample_size,
        )
        await db.commit()
        return experiment.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/experiments")
async def list_experiments(
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all experiments for the user."""
    service = ExperimentService(db)
    experiments = await service.list_experiments(user_id)
    return {"experiments": experiments, "total": len(experiments)}


@router.get("/experiments/{experiment_id}")
async def get_experiment(
    experiment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get experiment details and current statistics."""
    service = ExperimentService(db)
    result = await service.get_experiment(experiment_id)
    if not result:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return result


@router.post("/experiments/{experiment_id}/outcome")
async def record_outcome(
    experiment_id: UUID,
    body: RecordOutcomeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Record a satisfaction outcome for an experiment variant."""
    service = ExperimentService(db)
    try:
        result = await service.record_outcome(experiment_id, body.variant, body.positive)
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/experiments/{experiment_id}/conclude")
async def conclude_experiment(
    experiment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Finalize experiment, apply winner rule, archive loser."""
    service = ExperimentService(db)
    try:
        result = await service.conclude_experiment(experiment_id)
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/experiments/{experiment_id}/pause")
async def pause_experiment(
    experiment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Pause or resume an experiment."""
    service = ExperimentService(db)
    try:
        result = await service.pause_experiment(experiment_id)
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
