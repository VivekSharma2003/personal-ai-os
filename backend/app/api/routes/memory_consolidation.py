"""
Personal AI OS - Memory Consolidation Routes
"""
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.dependencies import get_db
from app.models.user import User
from app.services.rule_engine import RuleEngineService
from app.services.memory_consolidation_service import MemoryConsolidationService
from app.api.schemas.memory_consolidation import (
    MemoryConsolidationRequest,
    MemoryConsolidationResponse,
    MemorySearchResponse,
    EpisodicMemoryResponse
)

router = APIRouter(prefix="/api/memory", tags=["Memory Consolidation"])


async def get_current_user_from_header(
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
) -> User:
    service = RuleEngineService(db)
    return await service.get_or_create_user(x_user_id)


@router.post("/consolidate", response_model=MemoryConsolidationResponse)
async def consolidate_memory(
    request: MemoryConsolidationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header)
):
    """Trigger memory consolidation for older threads or a specific thread."""
    service = MemoryConsolidationService(db)
    
    if request.thread_id:
        memory = await service.consolidate_thread(current_user.id, request.thread_id)
        return MemoryConsolidationResponse(
            status="success",
            memories_created=1 if memory else 0,
            threads_processed=1
        )
    else:
        result = await service.consolidate_old_threads(current_user.id, request.days_old or 30)
        return MemoryConsolidationResponse(
            status="success",
            **result
        )


@router.get("/search", response_model=MemorySearchResponse)
async def search_memories(
    q: str,
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header)
):
    """Search for relevant episodic memories."""
    service = MemoryConsolidationService(db)
    memories = await service.search_memories(current_user.id, q, limit)
    
    return MemorySearchResponse(
        results=[EpisodicMemoryResponse.model_validate(m) for m in memories],
        query=q
    )
