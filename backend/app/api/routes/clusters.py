"""
Personal AI OS - Cluster Routes

REST endpoints for rule similarity cluster management.
"""
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.dependencies import get_db
from app.services.cluster_service import ClusterService

router = APIRouter()


def _get_user_id(x_user_id: str = Header(...)) -> UUID:
    return UUID(x_user_id)


@router.get("/clusters")
async def list_clusters(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all rule clusters for the user."""
    service = ClusterService(db)
    return await service.list_clusters(user_id, limit, offset)


@router.post("/clusters/generate")
async def generate_clusters(
    similarity_threshold: float = Query(default=None, ge=0.5, le=1.0),
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate clusters by grouping similar rules."""
    service = ClusterService(db)
    return await service.generate_clusters(user_id, similarity_threshold)


@router.get("/clusters/{cluster_id}")
async def get_cluster_detail(
    cluster_id: UUID,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get cluster detail with member rules."""
    service = ClusterService(db)
    detail = await service.get_cluster_detail(cluster_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return detail


@router.post("/clusters/{cluster_id}/merge")
async def merge_cluster(
    cluster_id: UUID,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Merge all rules in a cluster into a single generalized rule."""
    service = ClusterService(db)
    result = await service.merge_cluster(cluster_id)
    if not result:
        raise HTTPException(status_code=404, detail="Cluster not found or empty")
    return result
