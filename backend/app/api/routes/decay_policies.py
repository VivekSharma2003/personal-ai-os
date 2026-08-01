"""
Personal AI OS - Decay Policy Routes

REST API endpoints for managing context-aware decay policies and processing rule decay.
"""
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from app.dependencies import get_db
from app.services.decay_policy_service import DecayPolicyService
from app.api.schemas.decay_policies import DecayPolicyUpsert, DecayPolicyResponse, DecayProcessResponse

router = APIRouter()


def _get_user_id(x_user_id: str = Header(...)) -> UUID:
    return UUID(x_user_id)


@router.post("/decay/policies", response_model=DecayPolicyResponse)
async def create_or_update_policy(
    body: DecayPolicyUpsert,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create or update a decay policy override for a specific tag, category, or generic user profile."""
    service = DecayPolicyService(db)
    tag_uuid = UUID(body.tag_id) if body.tag_id else None
    policy = await service.create_or_update_policy(
        user_id=user_id,
        tag_id=tag_uuid,
        category=body.category,
        base_decay_rate=body.base_decay_rate,
        grace_period_days=body.grace_period_days,
        topic_sensitivity=body.topic_sensitivity,
    )
    return policy


@router.get("/decay/policies", response_model=List[DecayPolicyResponse])
async def list_policies(
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all decay policies defined for the user."""
    service = DecayPolicyService(db)
    return await service.list_policies(user_id)


@router.delete("/decay/policies/{policy_id}", response_model=dict)
async def delete_policy(
    policy_id: UUID,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a specific decay policy override."""
    service = DecayPolicyService(db)
    result = await service.delete_policy(policy_id, user_id)
    if result["count"] == 0:
        raise HTTPException(status_code=404, detail="Decay policy not found")
    return {"deleted": True}


@router.post("/decay/process", response_model=DecayProcessResponse)
async def process_decay(
    dry_run: bool = Query(default=False),
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Trigger the dynamic decay processor for a user's active rules (supporting preview in dry_run mode)."""
    service = DecayPolicyService(db)
    return await service.process_dynamic_decay(user_id, dry_run)
