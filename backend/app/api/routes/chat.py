"""
Personal AI OS - Chat API Routes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.chat import ChatRequest, ChatResponse
from app.dependencies import get_db
from app.services.interaction import InteractionService


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Process a chat message with automatic rule application.
    
    Rules are fetched based on user preferences and applied to the prompt.
    The response is generated with all relevant rules considered.
    """
    service = InteractionService(db)
    
    try:
        result = await service.process_chat(
            user_id=request.user_id,
            message=request.message,
            conversation_id=request.conversation_id
        )
        
        return ChatResponse(
            response=result["response"],
            rules_applied=result["rules_applied"],
            interaction_id=result["interaction_id"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
