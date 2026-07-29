"""
Personal AI OS - Streaming Chat API Route (SSE)

Server-Sent Events endpoint for real-time token streaming.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.api.schemas.chat import ChatRequest
from app.dependencies import get_db
from app.services.rule_engine import RuleEngineService
from app.services.memory import MemoryService
from app.services.prompt_builder import PromptBuilderService
from app.core.streaming import stream_chat_response
from app.config import get_settings


settings = get_settings()
router = APIRouter()


@router.post("/chat/stream")
async def stream_chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Stream a chat response using Server-Sent Events.

    Returns a text/event-stream with the following event types:
    - rule_applied: Emitted for each rule being applied
    - token: Individual text tokens as they are generated
    - done: Final event with interaction metadata
    - error: Emitted if an error occurs during streaming

    Example SSE output:
        data: {"type": "rule_applied", "rule_id": "...", "content": "...", "category": "style"}
        data: {"type": "token", "content": "Hello"}
        data: {"type": "token", "content": " world"}
        data: {"type": "done", "interaction_id": "...", "rules_applied": 2}
    """
    rule_engine = RuleEngineService(db)
    memory = MemoryService(db)
    prompt_builder = PromptBuilderService()

    try:
        # Get or create user
        user = await rule_engine.get_or_create_user(request.user_id)

        # Get relevant rules
        rules = await rule_engine.get_rules_for_prompt(
            user_id=user.id,
            context=request.message
        )

        # Build prompt
        messages = await prompt_builder.build_chat_prompt(
            user_message=request.message,
            rules=rules,
            conversation_id=request.conversation_id,
            db=db,
            user_id=user.id
        )
        messages = prompt_builder.truncate_for_context(messages)

        # We'll collect the full response for storage after streaming
        collected_response = []

        async def event_generator():
            """Generate SSE events."""
            full_response = ""

            async for event in stream_chat_response(
                messages=messages,
                rules_applied=rules,
                provider_name=settings.llm_provider,
            ):
                if event.type == "token":
                    full_response += event.data.get("content", "")

                yield event.to_sse()

            # After streaming completes, store the interaction
            try:
                rule_ids = [UUID(r["id"]) for r in rules if "id" in r]
                interaction = await memory.store_interaction(
                    user_id=user.id,
                    user_message=request.message,
                    assistant_response=full_response,
                    conversation_id=request.conversation_id,
                    rules_applied=rule_ids
                )

                # Mark rules as applied
                for rule in rules:
                    if "id" in rule:
                        await rule_engine.mark_rule_applied(UUID(rule["id"]))

                # Update conversation context
                if request.conversation_id:
                    await prompt_builder.update_conversation_context(
                        conversation_id=request.conversation_id,
                        user_message=request.message,
                        assistant_response=full_response
                    )

                await db.commit()

                # Send final done event with interaction ID
                import json
                yield f"data: {json.dumps({'type': 'done', 'interaction_id': str(interaction.id), 'rules_applied': len(rules)})}\n\n"

            except Exception as e:
                import json
                yield f"data: {json.dumps({'type': 'error', 'message': f'Post-stream storage failed: {str(e)}'})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
