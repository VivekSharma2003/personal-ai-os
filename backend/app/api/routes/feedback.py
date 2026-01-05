"""
Personal AI OS - Feedback API Routes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.feedback import FeedbackRequest, FeedbackResponse, RuleInfo
from app.dependencies import get_db
from app.services.interaction import InteractionService


router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse)
async def provide_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Provide feedback or correction on a previous AI response.
    
    The system will:
    1. Detect if this is a correction
    2. Extract a reusable rule
    3. Check for duplicates
    4. Create or reinforce the rule
    """
    service = InteractionService(db)
    
    try:
        result = await service.process_feedback(
            interaction_id=request.interaction_id,
            correction=request.correction
        )
        
        rule_info = None
        if result.get("rule"):
            rule_data = result["rule"]
            rule_info = RuleInfo(
                id=rule_data.get("id", ""),
                content=rule_data.get("content", ""),
                category=rule_data.get("category", ""),
                confidence=rule_data.get("confidence", 0.5),
                status=rule_data.get("status", "active"),
                times_applied=rule_data.get("times_applied", 0),
                times_reinforced=rule_data.get("times_reinforced", 0),
                created_at=rule_data.get("created_at")
            )
        
        return FeedbackResponse(
            status=result["status"],
            rule=rule_info,
            message=result["message"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
