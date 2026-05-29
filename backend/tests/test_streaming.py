# pyrefly: ignore [missing-import]
import pytest
import json
from unittest.mock import patch, AsyncMock
from uuid import uuid4
from app.models.user import User
from app.models.rule import Rule

# Async generator helper for mocking stream
async def mock_stream_generator(*args, **kwargs):
    yield "Hello"
    yield " world"
    yield "!"

@pytest.mark.asyncio
@patch("app.core.streaming._stream_from_provider", new_callable=lambda: mock_stream_generator)
async def test_chat_stream_endpoint(mock_stream, client, db_session):
    # 1. Create a user
    user = User(external_id="stream_user")
    db_session.add(user)
    await db_session.flush()

    # 2. Add an active rule that should get applied
    rule = Rule(
        user_id=user.id,
        content="Keep responses brief",
        category="style",
        confidence=0.9
    )
    db_session.add(rule)
    await db_session.flush()

    # 3. Request payload
    payload = {
        "user_id": "stream_user",
        "message": "Write a short poem",
        "conversation_id": str(uuid4())
    }

    # 4. Call the stream endpoint
    response = await client.post("/api/chat/stream", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    # 5. Parse SSE events
    events = []
    async for line in response.aiter_lines():
        if line.startswith("data: "):
            data = json.loads(line[6:])
            events.append(data)

    # 6. Verify SSE events in order:
    # First: rule_applied
    assert len(events) >= 5  # rule_applied, token (x3), done (or maybe more if rules list is long)
    
    rule_events = [e for e in events if e["type"] == "rule_applied"]
    assert len(rule_events) == 1
    assert rule_events[0]["content"] == "Keep responses brief"

    # Next: tokens
    token_events = [e for e in events if e["type"] == "token"]
    assert len(token_events) == 3
    assert token_events[0]["content"] == "Hello"
    assert token_events[1]["content"] == " world"
    assert token_events[2]["content"] == "!"

    # Last: done
    done_events = [e for e in events if e["type"] == "done"]
    assert len(done_events) == 2
    assert done_events[-1]["interaction_id"] != ""
