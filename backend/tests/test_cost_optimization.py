"""
Personal AI OS - Test Cost Optimization
"""
import pytest

from app.models.rule import Rule, RuleStatus
from app.services.cost_optimizer import CostOptimizerService
from app.services.rule_engine import RuleEngineService


@pytest.mark.asyncio
async def test_cost_optimizer_service(db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("cost_opt_test_user")
    await db_session.flush()

    # Create rules with different confidence and usage
    rule1 = await rule_engine.create_rule(
        user_id=user.id,
        content="This is a very short rule.",
        category="style",
        original_correction="test1"
    )
    # Update stats
    rule1.confidence = 0.9
    rule1.times_applied = 10
    rule1.times_reinforced = 5
    
    rule2 = await rule_engine.create_rule(
        user_id=user.id,
        content="This is a very long rule. " * 20,
        category="style",
        original_correction="test2"
    )
    rule2.confidence = 0.2
    rule2.times_applied = 0
    rule2.times_reinforced = 0
    
    await db_session.commit()

    service = CostOptimizerService(db_session)
    
    # Test review_savings
    savings = await service.review_savings(user.id)
    assert savings["total_active_rules"] == 2
    assert savings["prunable_rules_count"] >= 1
    # The long rule with low confidence should be a prunable candidate
    candidate_ids = [c["id"] for c in savings["prunable_candidates"]]
    assert str(rule2.id) in candidate_ids
    
    # Test prune_rules
    # Set a very low token limit to force dropping the long rule
    prune_result = await service.prune_rules(user.id, max_tokens=10)
    assert prune_result["accepted_rules_count"] == 1
    assert prune_result["dropped_rules_count"] == 1
    assert str(rule1.id) in prune_result["accepted_rules"]
    assert str(rule2.id) in prune_result["dropped_rules"]


@pytest.mark.asyncio
async def test_cost_optimization_api(client, db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("api_cost_user")
    await db_session.flush()
    
    await rule_engine.create_rule(
        user_id=user.id,
        content="Short rule.",
        category="style",
        original_correction="test1"
    )
    await db_session.commit()

    # GET /api/analytics/cost-optimization
    response = await client.get(
        "/api/analytics/cost-optimization",
        headers={"X-User-ID": "api_cost_user"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_active_rules"] >= 1

    # POST /api/analytics/cost-optimization/prune
    response = await client.post(
        "/api/analytics/cost-optimization/prune",
        json={"max_tokens": 1000},
        headers={"X-User-ID": "api_cost_user"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["accepted_rules_count"] >= 1
    assert data["dropped_rules_count"] == 0
