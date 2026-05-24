"""
Personal AI OS - Conflict API Routes
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.conflicts import (
    ConflictResponse, ConflictsListResponse,
    ResolveConflictRequest, ConflictScanResponse
)
from app.dependencies import get_db
from app.services.conflicts import ConflictService
from app.services.rule_engine import RuleEngineService
from app.models.rule_conflict import ConflictStatus


router = APIRouter()


@router.get("/conflicts", response_model=ConflictsListResponse)
async def list_conflicts(
    user_id: str = Query(..., description="External user ID"),
    status: Optional[str] = Query(None, description="Filter by status: active, resolved, dismissed"),
    db: AsyncSession = Depends(get_db)
):
    """List all detected rule conflicts for a user."""
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(user_id)

    conflict_service = ConflictService(db)
    conflicts = await conflict_service.get_conflicts(user.id, status=status)

    active_count = sum(1 for c in conflicts if c.status == ConflictStatus.ACTIVE.value)

    return ConflictsListResponse(
        conflicts=[
            ConflictResponse(**c.to_dict()) for c in conflicts
        ],
        total=len(conflicts),
        active=active_count,
    )


@router.post("/conflicts/{conflict_id}/resolve", response_model=ConflictResponse)
async def resolve_conflict(
    conflict_id: str,
    request: ResolveConflictRequest,
    db: AsyncSession = Depends(get_db)
):
    """Resolve a detected conflict with a chosen strategy."""
    conflict_service = ConflictService(db)

    details = {}
    if request.merged_content:
        details["merged_content"] = request.merged_content
    if request.disable_rule_id:
        details["disable_rule_id"] = request.disable_rule_id

    conflict = await conflict_service.resolve_conflict(
        conflict_id=UUID(conflict_id),
        resolution=request.resolution,
        details=details,
    )

    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

    await db.commit()
    return ConflictResponse(**conflict.to_dict())


@router.post("/conflicts/{conflict_id}/dismiss", response_model=ConflictResponse)
async def dismiss_conflict(
    conflict_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Dismiss a conflict (acknowledge without taking action)."""
    conflict_service = ConflictService(db)
    conflict = await conflict_service.dismiss_conflict(UUID(conflict_id))

    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

    await db.commit()
    return ConflictResponse(**conflict.to_dict())


@router.post("/conflicts/scan", response_model=ConflictScanResponse)
async def scan_conflicts(
    user_id: str = Query(..., description="External user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger a full conflict scan for all active rules."""
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(user_id)

    conflict_service = ConflictService(db)

    try:
        new_conflicts = await conflict_service.scan_all_user_conflicts(user.id)
        all_conflicts = await conflict_service.get_conflicts(user.id, status="active")

        await db.commit()

        return ConflictScanResponse(
            new_conflicts=len(new_conflicts),
            total_active=len(all_conflicts),
            message=f"Scan complete. Found {len(new_conflicts)} new conflict(s).",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
