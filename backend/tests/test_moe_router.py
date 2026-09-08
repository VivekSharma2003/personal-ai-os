"""
Personal AI OS - Test MoE Router
"""
import pytest
from app.services.moe_router import MoERouterService

@pytest.mark.asyncio
async def test_moe_router_service(db_session):
    service = MoERouterService(db_session)
    
    # Configure some routes
    await service.configure_route("coding", "anthropic", "claude-3-opus")
    await service.configure_route("translation", "google", "gemini-1.5-pro")
    
    # Test intent classification and routing
    route = await service.get_route_for_prompt("Can you write a python script for me?")
    assert route["intent"] == "coding"
    assert route["provider"] == "anthropic"
    assert route["model"] == "claude-3-opus"
    
    route = await service.get_route_for_prompt("Please translate this to Spanish.")
    assert route["intent"] == "translation"
    assert route["provider"] == "google"
    assert route["model"] == "gemini-1.5-pro"
    
    # Default route
    route = await service.get_route_for_prompt("Who is the president of the US?")
    assert route["intent"] == "general"
    assert route["provider"] == "openai" # Default fallback
    assert route["model"] == "gpt-4o"

@pytest.mark.asyncio
async def test_moe_api(client, db_session):
    # Configure via API
    resp = await client.post(
        "/api/moe/configure",
        json={"intent": "summarization", "provider": "anthropic", "model": "claude-3-haiku-20240307"}
    )
    assert resp.status_code == 200
    
    # Test routing via API
    resp = await client.post(
        "/api/moe/route",
        json={"prompt": "Can you give me a tl;dr of this document?"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "summarization"
    assert data["provider"] == "anthropic"
