"""
Personal AI OS - LLM Fallback Routes
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db
from app.models.user import User
from app.models.llm_fallback import LLMFallbackPolicy
from app.services.rule_engine import RuleEngineService
from app.api.schemas.llm_fallbacks import (
    LLMFallbackPolicyCreate,
    LLMFallbackPolicyUpdate,
    LLMFallbackPolicyResponse
)

router = APIRouter(prefix="/api/llm/fallbacks", tags=["LLM Fallbacks"])

async def get_current_user_from_header(
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
) -> User:
    service = RuleEngineService(db)
    return await service.get_or_create_user(x_user_id)

@router.post("", response_model=LLMFallbackPolicyResponse)
async def create_fallback_policy(
    policy_in: LLMFallbackPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header)
):
    """Create a new LLM fallback policy."""
    if policy_in.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create policies for this user")
        
    policy = LLMFallbackPolicy(**policy_in.model_dump())
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


@router.get("", response_model=List[LLMFallbackPolicyResponse])
async def list_fallback_policies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header)
):
    """List all LLM fallback policies for the current user."""
    result = await db.execute(
        select(LLMFallbackPolicy).where(LLMFallbackPolicy.user_id == current_user.id)
    )
    return result.scalars().all()


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fallback_policy(
    policy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header)
):
    """Delete an LLM fallback policy."""
    result = await db.execute(
        select(LLMFallbackPolicy).where(
            LLMFallbackPolicy.id == policy_id,
            LLMFallbackPolicy.user_id == current_user.id
        )
    )
    policy = result.scalars().first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
        
    await db.delete(policy)
    await db.commit()
