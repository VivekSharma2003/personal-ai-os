"""
Personal AI OS - Quota Routes
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.user import User
from app.services.rule_engine import RuleEngineService
from app.services.quota_manager import QuotaManagerService
from app.api.schemas.quotas import QuotaStatusResponse

router = APIRouter(prefix="/api/quotas", tags=["Quotas"])


async def get_current_user_from_header(
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
) -> User:
    service = RuleEngineService(db)
    return await service.get_or_create_user(x_user_id)


@router.get("/status", response_model=QuotaStatusResponse)
async def get_quota_status(
    current_user: User = Depends(get_current_user_from_header)
):
    """Get the current rate limit and token quota status for the user."""
    service = QuotaManagerService()
    status = await service.get_quota_status(current_user.id)
    return QuotaStatusResponse(**status)


@router.post("/consume")
async def consume_quota(
    tokens: int,
    current_user: User = Depends(get_current_user_from_header)
):
    """
    Manually consume token quota for a user (useful for testing or external clients).
    Normally, this happens automatically inside the Prompt Builder.
    """
    service = QuotaManagerService()
    allowed, details = await service.check_and_consume_quota(current_user.id, tokens=tokens)
    
    if not allowed:
        raise HTTPException(status_code=429, detail=details)
        
    return {"status": "success", "details": details}
