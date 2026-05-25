"""
Personal AI OS - Streaming Response Orchestration

Wraps each LLM provider's streaming API and yields structured stream events
for SSE delivery to the frontend.
"""
import json
from typing import AsyncIterator, Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class StreamEvent:
    """A single event in the chat stream."""
    type: str  # "token" | "rule_applied" | "metadata" | "done" | "error"
    data: Dict[str, Any]

    def to_sse(self) -> str:
        """Format as Server-Sent Event string."""
        return f"data: {json.dumps({'type': self.type, **self.data})}\n\n"


async def stream_chat_response(
    messages: List[Dict[str, str]],
    rules_applied: List[dict],
    provider_name: str,
    interaction_id: Optional[str] = None,
) -> AsyncIterator[StreamEvent]:
    """
    Stream a chat response with structured events.

    Yields:
        StreamEvent objects in order:
        1. rule_applied events (one per rule)
        2. token events (one per token chunk)
        3. done event with final metadata

    Args:
        messages: LLM message list
        rules_applied: List of rule dicts that were applied
        provider_name: Which LLM provider to use
        interaction_id: Optional interaction ID for the done event
    """
    # Step 1: Emit rules that were applied
    for rule in rules_applied:
        yield StreamEvent(
            type="rule_applied",
            data={
                "rule_id": rule.get("id", ""),
                "content": rule.get("content", ""),
                "category": rule.get("category", ""),
            }
        )

    # Step 2: Stream tokens from LLM
    full_response = ""
    token_count = 0

    try:
        async for chunk in _stream_from_provider(messages, provider_name):
            full_response += chunk
            token_count += 1
            yield StreamEvent(
                type="token",
                data={"content": chunk}
            )

        # Step 3: Emit done event
        yield StreamEvent(
            type="done",
            data={
                "interaction_id": interaction_id or "",
                "rules_applied": len(rules_applied),
                "total_tokens": token_count,
                "full_response_length": len(full_response),
            }
        )

    except Exception as e:
        yield StreamEvent(
            type="error",
            data={"message": str(e)}
        )


async def _stream_from_provider(
    messages: List[Dict[str, str]],
    provider_name: str,
) -> AsyncIterator[str]:
    """
    Stream tokens from the configured LLM provider.

    Each provider's streaming API is wrapped to yield raw text chunks.
    """
    from app.config import get_settings
    settings = get_settings()

    if provider_name == "openai":
        async for chunk in _stream_openai(messages, settings):
            yield chunk
    elif provider_name == "gemini":
        async for chunk in _stream_gemini(messages, settings):
            yield chunk
    elif provider_name == "anthropic":
        async for chunk in _stream_anthropic(messages, settings):
            yield chunk
    else:
        raise ValueError(f"Unknown provider: {provider_name}")


async def _stream_openai(messages, settings) -> AsyncIterator[str]:
    """Stream from OpenAI's chat completions API."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    stream = await client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        stream=True,
    )

    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


async def _stream_gemini(messages, settings) -> AsyncIterator[str]:
    """Stream from Google Gemini API."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.google_api_key)

    # Extract system instruction and convert messages
    system_instruction = None
    contents = []
    for msg in messages:
        if msg["role"] == "system":
            system_instruction = msg["content"]
        elif msg["role"] == "user":
            contents.append(types.Content(
                role="user",
                parts=[types.Part(text=msg["content"])]
            ))
        elif msg["role"] == "assistant":
            contents.append(types.Content(
                role="model",
                parts=[types.Part(text=msg["content"])]
            ))

    config = types.GenerateContentConfig(
        temperature=settings.llm_temperature,
        max_output_tokens=settings.llm_max_tokens,
        system_instruction=system_instruction,
    )

    async for chunk in client.aio.models.generate_content_stream(
        model=settings.gemini_model,
        contents=contents,
        config=config,
    ):
        if chunk.text:
            yield chunk.text


async def _stream_anthropic(messages, settings) -> AsyncIterator[str]:
    """Stream from Anthropic's messages API."""
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Extract system message
    system = ""
    chat_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system = msg["content"]
        else:
            chat_messages.append(msg)

    async with client.messages.stream(
        model=settings.anthropic_model,
        system=system,
        messages=chat_messages,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    ) as stream:
        async for text in stream.text_stream:
            yield text
