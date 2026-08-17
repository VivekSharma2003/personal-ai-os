"""
Personal AI OS - Test LLM Fallbacks
"""
import pytest
from unittest.mock import patch, AsyncMock

from app.services.fallback_service import FallbackService
from app.models.llm_fallback import LLMFallbackPolicy
from app.services.rule_engine import RuleEngineService


@pytest.mark.asyncio
async def test_fallback_service_execution(db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("fallback_test_user")
    await db_session.flush()

    policy = LLMFallbackPolicy(
        user_id=user.id,
        primary_provider="openai",
        primary_model="gpt-4",
        fallback_provider="gemini",
        fallback_model="gemini-1.5-pro",
        max_retries=2,
        backoff_factor=0.1,  # Short backoff for tests
        is_active=True
    )
    db_session.add(policy)
    await db_session.commit()
    
    service = FallbackService(db_session)
    
    with patch("app.services.fallback_service.OpenAIProvider") as MockOpenAI, \
         patch("app.services.fallback_service.GeminiProvider") as MockGemini:
        
        mock_openai_inst = MockOpenAI.return_value
        # Fail twice
        mock_openai_inst.generate_response = AsyncMock(side_effect=[Exception("API Error"), Exception("API Error")])
        
        mock_gemini_inst = MockGemini.return_value
        mock_gemini_inst.generate_response = AsyncMock(return_value="Fallback response")
        
        response = await service.generate_response_with_fallback(
            user_id=user.id,
            messages=[{"role": "user", "content": "Hello"}],
            primary_provider_name="openai",
            primary_model_name="gpt-4"
        )
        
        assert response == "Fallback response"
        assert mock_openai_inst.generate_response.call_count == 2
        assert mock_gemini_inst.generate_response.call_count == 1


@pytest.mark.asyncio
async def test_create_and_list_fallback_policy(client, db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("api_fallback_user")
    await db_session.flush()

    payload = {
        "user_id": str(user.id),
        "primary_provider": "anthropic",
        "primary_model": "claude-3-opus",
        "fallback_provider": "openai",
        "fallback_model": "gpt-4o",
        "max_retries": 3,
        "backoff_factor": 1.5,
        "is_active": True
    }
    
    # Create policy
    create_response = await client.post(
        "/api/llm/fallbacks",
        json=payload,
        headers={"X-User-ID": "api_fallback_user"}
    )
    
    assert create_response.status_code == 200
    data = create_response.json()
    assert data["primary_provider"] == "anthropic"
    assert data["fallback_provider"] == "openai"
    policy_id = data["id"]
    
    # List policies
    list_response = await client.get(
        "/api/llm/fallbacks",
        headers={"X-User-ID": "api_fallback_user"}
    )
    
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert len(list_data) >= 1
    assert any(p["id"] == policy_id for p in list_data)
