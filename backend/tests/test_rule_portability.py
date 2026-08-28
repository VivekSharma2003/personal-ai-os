"""
Personal AI OS - Test Rule Portability
"""
import pytest
from app.services.portability_service import PortabilityService
from app.services.rule_engine import RuleEngineService


@pytest.mark.asyncio
async def test_portability_service(db_session):
    rule_engine = RuleEngineService(db_session)
    user1 = await rule_engine.get_or_create_user("portability_user_1")
    user2 = await rule_engine.get_or_create_user("portability_user_2")
    await db_session.flush()
    
    # Create rules for user1
    await rule_engine.create_rule(
        user_id=user1.id,
        content="Always write in Python",
        category="style",
        original_correction="test"
    )
    await db_session.commit()
    
    service = PortabilityService(db_session)
    
    # Export encrypted
    payload = await service.export_rules(user1.id, encrypt=True)
    assert "Always write in Python" not in payload # Should be encrypted
    
    # Import to user2
    result = await service.import_rules(user2.id, payload, is_encrypted=True)
    assert result["status"] == "success"
    assert result["imported_count"] == 1
    
    # Verify user2 has the rule
    rules2 = await rule_engine.get_user_rules(user2.id)
    assert len(rules2) == 1
    assert rules2[0].content == "Always write in Python"


@pytest.mark.asyncio
async def test_portability_api(client, db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("api_port_user")
    await db_session.flush()
    
    await rule_engine.create_rule(
        user_id=user.id,
        content="Test API export",
        category="style",
        original_correction="test"
    )
    await db_session.commit()
    
    # Export unencrypted via API
    response = await client.post(
        "/api/portability/export",
        json={"encrypt": False},
        headers={"X-User-ID": "api_port_user"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_encrypted"] is False
    assert "Test API export" in data["payload"]
    
    payload = data["payload"]
    
    # Import via API (unencrypted)
    response = await client.post(
        "/api/portability/import",
        json={"payload": payload, "is_encrypted": False},
        headers={"X-User-ID": "api_port_user"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["imported_count"] == 1
