"""
Personal AI OS - Shared Library Routes

REST endpoints for browsing, publishing, installing, and rating
shared community rules.
"""
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.dependencies import get_db
from app.services.shared_library_service import SharedLibraryService
from app.api.schemas.shared_library import PublishRuleRequest, RateRuleRequest

router = APIRouter()


def _get_user_id(x_user_id: str = Header(...)) -> UUID:
    return UUID(x_user_id)


@router.post("/library/publish")
async def publish_rule(
    body: PublishRuleRequest,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Publish a rule to the shared community library."""
    service = SharedLibraryService(db)
    result = await service.publish_rule(
        user_id=user_id,
        rule_id=UUID(body.rule_id),
        title=body.title,
        description=body.description,
        visibility=body.visibility,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/library")
async def browse_library(
    query: str = Query(default=None),
    category: str = Query(default=None),
    sort_by: str = Query(default="popular", pattern="^(popular|rating|newest)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Browse and search the shared rule library."""
    service = SharedLibraryService(db)
    return await service.browse_library(query, category, sort_by, limit, offset)


@router.get("/library/popular")
async def get_popular(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get top shared rules by install count."""
    service = SharedLibraryService(db)
    return await service.get_popular(limit)


@router.post("/library/{shared_rule_id}/install")
async def install_rule(
    shared_rule_id: UUID,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Install a shared rule into the user's personal ruleset."""
    service = SharedLibraryService(db)
    result = await service.install_rule(user_id, shared_rule_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/library/{shared_rule_id}/rate")
async def rate_rule(
    shared_rule_id: UUID,
    body: RateRuleRequest,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Rate a shared rule (1-5 stars)."""
    service = SharedLibraryService(db)
    result = await service.rate_rule(user_id, shared_rule_id, body.rating)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/library/{shared_rule_id}")
async def unpublish_rule(
    shared_rule_id: UUID,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Unpublish a shared rule (author only)."""
    service = SharedLibraryService(db)
    result = await service.unpublish(user_id, shared_rule_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
