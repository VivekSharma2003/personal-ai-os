"""
Personal AI OS - Replay Routes

REST endpoints for prompt replay and regression testing.
"""
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.dependencies import get_db
from app.services.replay_service import ReplayService
from app.api.schemas.replay import StartReplayRequest

router = APIRouter()


def _get_user_id(x_user_id: str = Header(...)) -> UUID:
    return UUID(x_user_id)


@router.post("/replay")
async def start_replay(
    body: StartReplayRequest,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Start a new prompt replay run."""
    service = ReplayService(db)
    result = await service.start_replay(
        user_id=user_id,
        name=body.name,
        interaction_ids=body.interaction_ids,
        sample_size=body.sample_size,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/replay")
async def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all replay runs for the user."""
    service = ReplayService(db)
    return await service.list_runs(user_id, limit, offset)


@router.get("/replay/{run_id}")
async def get_run(
    run_id: UUID,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific replay run."""
    service = ReplayService(db)
    run = await service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Replay run not found")
    return run


@router.get("/replay/{run_id}/results")
async def get_results(
    run_id: UUID,
    verdict: str = Query(default=None, pattern="^(regression|improved|unchanged)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed results for a replay run, optionally filtered by verdict."""
    service = ReplayService(db)
    return await service.get_results(run_id, verdict, limit, offset)
