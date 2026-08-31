"""
Personal AI OS - Test Quota Manager
"""
import pytest
from app.services.quota_manager import QuotaManagerService
from app.services.rule_engine import RuleEngineService

@pytest.mark.asyncio
async def test_quota_manager_service(db_session):
    service = QuotaManagerService()
    service.default_hourly_tokens = 100
    service.default_daily_requests = 2
    
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("quota_test_user")
    await db_session.flush()
    
    # Check status initially
    status = await service.get_quota_status(user.id)
    assert status["allowed"] is True
    
    # Consume 1 request and 50 tokens
    allowed, details = await service.check_and_consume_quota(user.id, tokens=50)
    assert allowed is True
    assert details["requests"]["used"] >= 1
    assert details["tokens"]["used"] >= 50
    
    # Consume 1 request and 60 tokens -> should fail on tokens
    allowed, details = await service.check_and_consume_quota(user.id, tokens=60)
    assert allowed is False
    assert details["reason"] == "Token limit exceeded"
    
    # Consume 1 request and 40 tokens -> should succeed
    allowed, details = await service.check_and_consume_quota(user.id, tokens=40)
    assert allowed is True
    assert details["requests"]["used"] >= 2
    assert details["tokens"]["used"] >= 90
    
    # Consume 1 request and 0 tokens -> should fail on requests
    allowed, details = await service.check_and_consume_quota(user.id, tokens=0)
    assert allowed is False
    assert details["reason"] == "Request limit exceeded"

@pytest.mark.asyncio
async def test_quota_api(client, db_session):
    response = await client.get(
        "/api/quotas/status",
        headers={"X-User-ID": "api_quota_user"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is True
    
    # Consume some tokens via API
    response = await client.post(
        "/api/quotas/consume?tokens=5000",
        headers={"X-User-ID": "api_quota_user"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["details"]["tokens"]["used"] >= 5000
