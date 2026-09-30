"""
Personal AI OS - Rule Changelog Routes

GET  /api/changelog/{rule_id}                    — full history
GET  /api/changelog/{rule_id}/{version}          — single version
GET  /api/changelog/{rule_id}/diff?from=1&to=3   — unified diff between versions
POST /api/changelog/{rule_id}                    — manually record a change
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.services.changelog_service import ChangelogService

router = APIRouter(prefix="/api/changelog", tags=["Rule Changelog"])


class RecordChangeRequest(BaseModel):
    new_content: str
    old_content: Optional[str] = None
    changed_by: Optional[str] = None
    change_reason: Optional[str] = None


def _entry_to_dict(entry) -> dict:
    return {
        "id": str(entry.id),
        "rule_id": str(entry.rule_id),
        "version": entry.version,
        "old_content": entry.old_content,
        "new_content": entry.new_content,
        "changed_by": entry.changed_by,
        "change_reason": entry.change_reason,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


@router.get("/{rule_id}")
async def get_history(rule_id: UUID, db: AsyncSession = Depends(get_db)):
    """Return the full versioned history for a rule."""
    service = ChangelogService(db)
    entries = await service.get_history(rule_id)
    return [_entry_to_dict(e) for e in entries]


@router.get("/{rule_id}/diff")
async def get_diff(
    rule_id: UUID,
    from_version: int = Query(..., alias="from", ge=1),
    to_version: int = Query(..., alias="to", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """Return a unified diff patch between two versions of a rule."""
    service = ChangelogService(db)
    try:
        return await service.diff(rule_id, from_version, to_version)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{rule_id}/{version}")
async def get_version(rule_id: UUID, version: int, db: AsyncSession = Depends(get_db)):
    """Return a single version snapshot of a rule."""
    service = ChangelogService(db)
    entry = await service.get_version(rule_id, version)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Version {version} not found")
    return _entry_to_dict(entry)


@router.post("/{rule_id}")
async def record_change(
    rule_id: UUID,
    req: RecordChangeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Manually record a rule change (called internally after rule updates)."""
    service = ChangelogService(db)
    entry = await service.record(
        rule_id=rule_id,
        new_content=req.new_content,
        old_content=req.old_content,
        changed_by=req.changed_by,
        change_reason=req.change_reason,
    )
    await db.commit()
    return _entry_to_dict(entry)
