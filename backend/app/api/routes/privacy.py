"""
Personal AI OS - Privacy Routes
"""
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.user import User
from app.services.rule_engine import RuleEngineService
from app.services.pii_scrubber import PIIScrubberService
from app.api.schemas.privacy import ScrubRequest, ScrubResponse

router = APIRouter(prefix="/api/privacy", tags=["Privacy"])


async def get_current_user_from_header(
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
) -> User:
    service = RuleEngineService(db)
    return await service.get_or_create_user(x_user_id)


@router.post("/scrub", response_model=ScrubResponse)
async def scrub_text(
    request: ScrubRequest,
    current_user: User = Depends(get_current_user_from_header)
):
    """
    Test endpoint for the PII scrubber.
    Normally, this runs automatically before saving chat logs.
    """
    service = PIIScrubberService(active=True)
    scrubbed = service.scrub_text(request.text)
    
    return ScrubResponse(
        original_text=request.text,
        scrubbed_text=scrubbed
    )
