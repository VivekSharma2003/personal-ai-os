"""
Personal AI OS - Conversation Summarizer API Routes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.summarize import SummarizeRequest, SummaryResponse
from app.dependencies import get_db
from app.services.rule_engine import RuleEngineService
from app.models.interaction import Interaction
from app.core.llm import generate_response


router = APIRouter()


BRIEF_SYSTEM_PROMPT = """You are a conversation summarizer. Given a chat conversation, 
produce a concise summary. Also extract key topics and any action items.

Respond with a JSON object:
{
    "summary": "A brief 2-3 sentence summary of the conversation",
    "key_topics": ["topic1", "topic2"],
    "action_items": ["action1", "action2"]
}

Respond ONLY with valid JSON, no markdown formatting."""


DETAILED_SYSTEM_PROMPT = """You are a conversation summarizer. Given a chat conversation,
produce a detailed summary covering all key points discussed, decisions made, and insights shared.
Also extract key topics and any action items.

Respond with a JSON object:
{
    "summary": "A detailed multi-paragraph summary of the conversation",
    "key_topics": ["topic1", "topic2", "topic3"],
    "action_items": ["action1", "action2"]
}

Respond ONLY with valid JSON, no markdown formatting."""


@router.post("/summarize", response_model=SummaryResponse)
async def summarize_conversation(
    request: SummarizeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate an AI-powered summary of a conversation.

    Extracts key topics, decisions, and action items from the conversation.
    Supports 'brief' and 'detailed' summary lengths.
    """
    rule_engine = RuleEngineService(db)

    try:
        user = await rule_engine.get_or_create_user(request.user_id)

        # Get all interactions for this conversation
        result = await db.execute(
            select(Interaction)
            .where(Interaction.user_id == user.id)
            .where(Interaction.conversation_id == request.conversation_id)
            .order_by(Interaction.created_at.asc())
        )
        interactions = list(result.scalars().all())

        if not interactions:
            raise HTTPException(status_code=404, detail="Conversation not found or empty")

        # Build conversation text
        conv_text_parts = []
        total_rules = 0
        total_corrections = 0
        for inter in interactions:
            conv_text_parts.append(f"User: {inter.user_message}")
            conv_text_parts.append(f"AI: {inter.assistant_response}")
            total_rules += len(inter.rules_applied or [])
            if inter.was_corrected:
                total_corrections += 1

        conv_text = "\n".join(conv_text_parts)

        # Truncate if too long
        if len(conv_text) > 8000:
            conv_text = conv_text[:8000] + "\n[... conversation truncated ...]"

        # Calculate duration
        first_time = interactions[0].created_at
        last_time = interactions[-1].created_at
        if first_time and last_time:
            delta = last_time - first_time
            minutes = int(delta.total_seconds() / 60)
            if minutes < 1:
                duration_text = "< 1 minute"
            elif minutes < 60:
                duration_text = f"{minutes} minute{'s' if minutes != 1 else ''}"
            else:
                hours = minutes // 60
                remaining_mins = minutes % 60
                duration_text = f"{hours}h {remaining_mins}m"
        else:
            duration_text = "Unknown"

        # Generate summary via LLM
        system_prompt = DETAILED_SYSTEM_PROMPT if request.length == "detailed" else BRIEF_SYSTEM_PROMPT

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Summarize this conversation:\n\n{conv_text}"},
        ]

        response_text = await generate_response(messages, temperature=0.3)

        # Parse JSON response
        import json
        # Clean up potential markdown formatting
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        try:
            parsed = json.loads(text.strip())
        except json.JSONDecodeError:
            # Fallback: use the raw response as summary
            parsed = {
                "summary": response_text,
                "key_topics": [],
                "action_items": [],
            }

        return SummaryResponse(
            conversation_id=request.conversation_id,
            summary=parsed.get("summary", response_text),
            key_topics=parsed.get("key_topics", []),
            action_items=parsed.get("action_items", []),
            message_count=len(interactions),
            duration_text=duration_text,
            rules_applied_count=total_rules,
            corrections_count=total_corrections,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
