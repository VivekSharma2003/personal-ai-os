"""
Personal AI OS - Conversation API Routes
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.conversations import (
    ConversationCreateRequest, ConversationUpdateRequest,
    ForkRequest, ConversationResponse,
    ConversationsListResponse, ConversationTreeResponse
)
from app.dependencies import get_db
from app.services.conversation_service import ConversationService
from app.services.rule_engine import RuleEngineService


router = APIRouter()


@router.get("/conversations", response_model=ConversationsListResponse)
async def list_conversations(
    user_id: str = Query(..., description="External user ID"),
    include_archived: bool = Query(False, description="Include archived conversations"),
    include_forks: bool = Query(True, description="Include forked conversations"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List all conversations for a user."""
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(user_id)

    conv_service = ConversationService(db)
    result = await conv_service.list_conversations(
        user_id=user.id,
        include_archived=include_archived,
        include_forks=include_forks,
        limit=page_size,
        offset=(page - 1) * page_size,
    )

    return ConversationsListResponse(
        conversations=[ConversationResponse(**c) for c in result["conversations"]],
        total=result["total"],
    )


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new conversation."""
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(request.user_id)

    conv_service = ConversationService(db)
    conversation = await conv_service.create_conversation(
        user_id=user.id,
        title=request.title,
        description=request.description,
    )

    await db.commit()

    conv_dict = conversation.to_dict()
    conv_dict["message_count"] = 0
    return ConversationResponse(**conv_dict)


@router.post("/conversations/{conversation_id}/fork", response_model=ConversationResponse)
async def fork_conversation(
    conversation_id: str,
    request: ForkRequest,
    db: AsyncSession = Depends(get_db)
):
    """Fork a conversation at a specific message, creating a branch."""
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(request.user_id)

    conv_service = ConversationService(db)

    fork = await conv_service.fork_conversation(
        conversation_id=UUID(conversation_id),
        at_interaction_id=UUID(request.at_interaction_id),
        user_id=user.id,
        title=request.title,
    )

    if not fork:
        raise HTTPException(
            status_code=404,
            detail="Conversation or interaction not found"
        )

    await db.commit()

    conv_dict = fork.to_dict()
    conv_dict["message_count"] = 0  # Will be updated on next list
    return ConversationResponse(**conv_dict)


@router.get("/conversations/{conversation_id}/tree", response_model=ConversationTreeResponse)
async def get_conversation_tree(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a conversation and all its forks as a tree structure."""
    conv_service = ConversationService(db)
    tree = await conv_service.get_conversation_tree(UUID(conversation_id))

    if not tree:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationTreeResponse(**tree)


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    request: ConversationUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update a conversation's title or description."""
    conv_service = ConversationService(db)

    conversation = None
    if request.title:
        conversation = await conv_service.rename_conversation(
            UUID(conversation_id), request.title
        )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.commit()
    conv_dict = conversation.to_dict()
    conv_dict["message_count"] = 0
    return ConversationResponse(**conv_dict)


@router.post("/conversations/{conversation_id}/pin", response_model=ConversationResponse)
async def toggle_pin_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Toggle a conversation's pinned status."""
    conv_service = ConversationService(db)
    conversation = await conv_service.toggle_pin(UUID(conversation_id))

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.commit()
    conv_dict = conversation.to_dict()
    conv_dict["message_count"] = 0
    return ConversationResponse(**conv_dict)


@router.post("/conversations/{conversation_id}/archive", response_model=ConversationResponse)
async def archive_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Archive a conversation."""
    conv_service = ConversationService(db)
    conversation = await conv_service.archive_conversation(UUID(conversation_id))

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.commit()
    conv_dict = conversation.to_dict()
    conv_dict["message_count"] = 0
    return ConversationResponse(**conv_dict)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    cascade_forks: bool = Query(False, description="Also delete all forked conversations"),
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation."""
    conv_service = ConversationService(db)
    deleted = await conv_service.delete_conversation(
        UUID(conversation_id), cascade_forks=cascade_forks
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.commit()
    return {"status": "deleted", "conversation_id": conversation_id}
