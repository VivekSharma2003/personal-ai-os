"""
Personal AI OS - Test Rule Compression
"""
import pytest
import uuid
from app.services.rule_compressor import RuleCompressorService
from app.services.rule_engine import RuleEngineService
from app.models.rule import RuleStatus

@pytest.mark.asyncio
async def test_rule_compression_service(db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user(f"compression_test_user_{uuid.uuid4()}")
    await db_session.flush()
    
    # Create rules for user in "style" category
    await rule_engine.create_rule(user.id, "Always use single quotes", "style", "test")
    await rule_engine.create_rule(user.id, "Use 4 spaces for indentation", "style", "test")
    await rule_engine.create_rule(user.id, "Prefer list comprehensions", "style", "test")
    
    # Create rule in "general" category (won't be compressed since count < 2)
    await rule_engine.create_rule(user.id, "Be polite", "general", "test")
    
    await db_session.commit()
    
    service = RuleCompressorService(db_session)
    
    # Try compressing "general"
    res1 = await service.compress_category(user.id, "general")
    assert res1["status"] == "skipped"
    
    # Compress "style"
    res2 = await service.compress_category(user.id, "style")
    assert res2["status"] == "success"
    assert res2["compressed_count"] == 3
    assert res2["new_rule_id"] is not None
    
    # Verify the old rules are archived
    style_rules = await rule_engine.get_user_rules(user.id, category="style", status=RuleStatus.ACTIVE.value)
    assert len(style_rules) == 1
    assert str(style_rules[0].id) == res2["new_rule_id"]

@pytest.mark.asyncio
async def test_rule_compression_api(client, db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user(f"api_comp_user_{uuid.uuid4()}")
    await db_session.flush()
    
    await rule_engine.create_rule(user.id, "Write code efficiently", "coding", "test")
    await rule_engine.create_rule(user.id, "Use descriptive variables", "coding", "test")
    await db_session.commit()
    
    response = await client.post(
        "/api/compression/compress",
        json={"category": "coding"},
        headers={"X-User-ID": user.external_id}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["compressed_count"] == 2
