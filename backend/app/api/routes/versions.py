"""
Personal AI OS - Version History API Routes
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.versions import (
    VersionResponse, VersionHistoryResponse,
    RollbackRequest, DiffResponse
)
from app.dependencies import get_db
from app.services.versioning import VersioningService


router = APIRouter()


@router.get("/rules/{rule_id}/versions", response_model=VersionHistoryResponse)
async def get_version_history(
    rule_id: str,
    limit: int = Query(50, ge=1, le=200, description="Max versions to return"),
    db: AsyncSession = Depends(get_db)
):
    """Get the full version history of a rule."""
    versioning = VersioningService(db)
    versions = await versioning.get_history(UUID(rule_id), limit=limit)

    return VersionHistoryResponse(
        rule_id=rule_id,
        versions=[VersionResponse(**v.to_dict()) for v in versions],
        total=len(versions),
    )


@router.post("/rules/{rule_id}/rollback", response_model=dict)
async def rollback_rule(
    rule_id: str,
    request: RollbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """Roll back a rule to a specific version."""
    versioning = VersioningService(db)

    rule = await versioning.rollback(UUID(rule_id), request.version_number)
    if not rule:
        raise HTTPException(
            status_code=404,
            detail="Rule or version not found"
        )

    await db.commit()

    return {
        "status": "rolled_back",
        "rule_id": rule_id,
        "restored_to_version": request.version_number,
        "current_content": rule.content,
        "message": f"Successfully rolled back to version {request.version_number}",
    }


@router.get("/rules/{rule_id}/versions/{v1}/diff/{v2}", response_model=DiffResponse)
async def diff_versions(
    rule_id: str,
    v1: int,
    v2: int,
    db: AsyncSession = Depends(get_db)
):
    """Compare two versions of a rule."""
    versioning = VersioningService(db)

    result = await versioning.diff(UUID(rule_id), v1, v2)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return DiffResponse(
        rule_id=result["rule_id"],
        version_a=VersionResponse(**result["version_a"]),
        version_b=VersionResponse(**result["version_b"]),
        content_diff=result["content_diff"],
        changes=result["changes"],
        has_changes=result["has_changes"],
    )
