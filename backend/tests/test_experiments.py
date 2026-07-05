"""
Tests for Rule A/B Testing (Experiments).
"""
import pytest
import pytest_asyncio
from uuid import uuid4

from app.models.user import User
from app.models.rule import Rule, RuleStatus
from app.services.experiment_service import ExperimentService


@pytest_asyncio.fixture
async def exp_user(db_session):
    """Create a test user."""
    user = User(external_id=f"exp_test_{uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_rules(db_session, exp_user):
    """Create two test rules to compare."""
    rule_a = Rule(
        user_id=exp_user.id,
        content="Use Python for data analysis",
        category="logic",
        status=RuleStatus.ACTIVE.value,
    )
    rule_b = Rule(
        user_id=exp_user.id,
        content="Use R for data analysis",
        category="logic",
        status=RuleStatus.ACTIVE.value,
    )
    db_session.add(rule_a)
    db_session.add(rule_b)
    await db_session.flush()
    return rule_a, rule_b


@pytest.mark.asyncio
async def test_create_and_run_experiment(db_session, exp_user, test_rules):
    """Test A/B experiment creation and flow."""
    rule_a, rule_b = test_rules
    service = ExperimentService(db_session)

    experiment = await service.create_experiment(
        user_id=exp_user.id,
        name="Data Analysis Language A/B",
        rule_a_id=rule_a.id,
        rule_b_id=rule_b.id,
        min_sample_size=10,
    )

    assert experiment is not None
    assert experiment.name == "Data Analysis Language A/B"
    assert experiment.status == "running"
    assert experiment.winner is None

    # Test variant assignment
    variant = await service.assign_variant(experiment.id)
    assert variant in ("a", "b")

    # Record outcomes to trigger completion
    # Create 10 positive outcomes for A, 0 for B to make it statistically significant
    for _ in range(10):
        # We need impressions
        experiment.variant_a_impressions += 1
        await db_session.flush()
        await service.record_outcome(experiment.id, variant="a", positive=True)

    for _ in range(10):
        experiment.variant_b_impressions += 1
        await db_session.flush()
        await service.record_outcome(experiment.id, variant="b", positive=False)

    # Force manual evaluation or rely on auto-evaluation
    eval_res = await service.evaluate_experiment(experiment.id)
    assert eval_res["status"] == "completed"
    assert eval_res["winner"] == "a"


@pytest.mark.asyncio
async def test_experiment_routes(client, db_session, exp_user, test_rules):
    """Test A/B experiment HTTP routes."""
    rule_a, rule_b = test_rules
    headers = {"X-User-ID": str(exp_user.id)}

    # 1. Create experiment
    payload = {
        "name": "HTTP Route Test",
        "rule_a_id": str(rule_a.id),
        "rule_b_id": str(rule_b.id),
        "min_sample_size": 20,
    }
    response = await client.post("/api/experiments", json=payload, headers=headers)
    assert response.status_code == 200
    exp_data = response.json()
    assert exp_data["name"] == "HTTP Route Test"

    # 2. Get experiment details
    exp_id = exp_data["id"]
    response = await client.get(f"/api/experiments/{exp_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == exp_id

    # 3. List experiments
    response = await client.get("/api/experiments", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1

    # 4. Record outcome
    outcome_payload = {
        "variant": "a",
        "positive": True,
    }
    response = await client.post(f"/api/experiments/{exp_id}/outcome", json=outcome_payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["variant_a_positive"] >= 1

    # 5. Pause experiment
    response = await client.patch(f"/api/experiments/{exp_id}/pause", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "paused"

    response = await client.patch(f"/api/experiments/{exp_id}/pause", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "running"

    # 6. Conclude experiment
    response = await client.post(f"/api/experiments/{exp_id}/conclude", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
