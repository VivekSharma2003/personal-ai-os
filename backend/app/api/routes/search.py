"""
Personal AI OS - Search API Routes
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.search import SearchResponse, SearchResult
from app.dependencies import get_db
from app.services.rule_engine import RuleEngineService
from app.models.interaction import Interaction


router = APIRouter()


def create_snippet(text: str, query: str, max_length: int = 200) -> str:
    """Create a highlighted snippet around the matching query term."""
    lower_text = text.lower()
    lower_query = query.lower()
    idx = lower_text.find(lower_query)

    if idx == -1:
        # No exact match, return start of text
        return text[:max_length] + ("..." if len(text) > max_length else "")

    # Get surrounding context
    start = max(0, idx - 60)
    end = min(len(text), idx + len(query) + 60)

    snippet = ""
    if start > 0:
        snippet += "..."
    snippet += text[start:end]
    if end < len(text):
        snippet += "..."

    return snippet


@router.get("/search", response_model=SearchResponse)
async def search_interactions(
    user_id: str = Query(..., description="External user ID"),
    q: str = Query(..., description="Search query", min_length=1, max_length=500),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    corrected_only: bool = Query(False, description="Only show corrected interactions"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search through past conversations using full-text search.

    Searches both user messages and assistant responses.
    Returns matching interactions with context snippets.
    """
    rule_engine = RuleEngineService(db)

    try:
        user = await rule_engine.get_or_create_user(user_id)
        offset = (page - 1) * page_size

        # Build search query — case-insensitive ILIKE
        search_filter = or_(
            Interaction.user_message.ilike(f"%{q}%"),
            Interaction.assistant_response.ilike(f"%{q}%"),
        )

        query = (
            select(Interaction)
            .where(Interaction.user_id == user.id)
            .where(search_filter)
        )

        if corrected_only:
            query = query.where(Interaction.was_corrected == True)

        # Get total count
        count_query = (
            select(func.count(Interaction.id))
            .where(Interaction.user_id == user.id)
            .where(search_filter)
        )
        if corrected_only:
            count_query = count_query.where(Interaction.was_corrected == True)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.order_by(Interaction.created_at.desc()).offset(offset).limit(page_size)
        result = await db.execute(query)
        interactions = result.scalars().all()

        # Build response
        results = []
        for inter in interactions:
            # Determine which field matched for snippet
            user_match = q.lower() in (inter.user_message or "").lower()
            ai_match = q.lower() in (inter.assistant_response or "").lower()

            if user_match:
                snippet = create_snippet(inter.user_message, q)
            elif ai_match:
                snippet = create_snippet(inter.assistant_response, q)
            else:
                snippet = inter.user_message[:200]

            # Simple relevance scoring
            score = 0.5
            if user_match and ai_match:
                score = 1.0
            elif user_match:
                score = 0.8
            elif ai_match:
                score = 0.6

            results.append(SearchResult(
                interaction_id=str(inter.id),
                conversation_id=inter.conversation_id,
                user_message=inter.user_message[:500],
                assistant_response=inter.assistant_response[:500],
                snippet=snippet,
                relevance_score=score,
                was_corrected=inter.was_corrected or False,
                rules_applied_count=len(inter.rules_applied or []),
                created_at=inter.created_at.isoformat() if inter.created_at else None,
            ))

        return SearchResponse(
            query=q,
            results=results,
            total=total,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
