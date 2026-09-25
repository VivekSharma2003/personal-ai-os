"""
Personal AI OS - Rule Deduplication Routes

GET  /api/dedup/scan   — find duplicate rules for the current user
POST /api/dedup/merge  — merge a group of duplicates into one rule
"""
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.services.dedup_service import DedupService
from app.services.rule_engine import RuleEngineService

router = APIRouter(prefix="/api/dedup", tags=["Deduplication"])


async def _get_user(
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db),
):
    return await RuleEngineService(db).get_or_create_user(x_user_id)


class MergeRequest(BaseModel):
    rule_ids: List[UUID] = Field(..., min_length=2)
    merged_content: str


@router.get("/scan")
async def scan_duplicates(
    threshold: float = 0.70,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_user),
):
    """
    Scan the current user's active rules for exact or near-duplicate entries.
    Returns similarity groups sorted by score descending.
    """
    service = DedupService(db)
    groups = await service.find_duplicates(current_user.id, similarity_threshold=threshold)
    return {"duplicate_groups": groups, "total": len(groups)}


@router.post("/merge")
async def merge_duplicates(
    req: MergeRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_user),
):
    """
    Archive the specified duplicate rules and replace them with a single merged rule.
    """
    service = DedupService(db)
    result = await service.merge(current_user.id, req.rule_ids, req.merged_content)
    return result
