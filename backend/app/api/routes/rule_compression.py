"""
Personal AI OS - Rule Compression Routes
"""
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.user import User
from app.services.rule_engine import RuleEngineService
from app.services.rule_compressor import RuleCompressorService
from app.api.schemas.rule_compression import CompressionRequest, CompressionResponse

router = APIRouter(prefix="/api/compression", tags=["Rule Compression"])


async def get_current_user_from_header(
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
) -> User:
    service = RuleEngineService(db)
    return await service.get_or_create_user(x_user_id)


@router.post("/compress", response_model=CompressionResponse)
async def compress_rules(
    request: CompressionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header)
):
    """
    Manually trigger rule compression for a specific category.
    Normally, this is handled via background jobs.
    """
    service = RuleCompressorService(db)
    result = await service.compress_category(current_user.id, request.category)
    return CompressionResponse(**result)
