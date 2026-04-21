"""
Personal AI OS - Rule Suggestions API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.suggestions import SuggestionsResponse
from app.dependencies import get_db
from app.services.suggestions import SuggestionService
from app.services.rule_engine import RuleEngineService


router = APIRouter()


@router.get("/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(
    user_id: str = Query(..., description="External user ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get AI-powered rule suggestions based on interaction patterns.

    Analyzes recent interactions to identify implicit user preferences
    that could be turned into explicit rules. Returns confidence-scored
    suggestions the user can accept or dismiss.
    """
    rule_engine = RuleEngineService(db)
    suggestion_service = SuggestionService(db)

    try:
        user = await rule_engine.get_or_create_user(user_id)
        result = await suggestion_service.get_suggestions(user.id)
        return SuggestionsResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
