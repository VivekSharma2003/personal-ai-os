"""
Personal AI OS - Test A/B Testing
"""
import pytest
import uuid
from app.services.ab_testing import ABTestingService
from app.services.rule_engine import RuleEngineService


@pytest.mark.asyncio
async def test_ab_experiment_flow(db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user(f"ab_test_{uuid.uuid4()}")
    await db_session.flush()

    service = ABTestingService(db_session)

    # Create experiment
    experiment = await service.create_experiment(
        user_id=user.id,
        name="Tone Test",
        variants=[
            {"label": "control", "prompt_template": "Answer formally: {query}"},
            {"label": "variant_a", "prompt_template": "Answer casually: {query}"},
        ],
    )
    assert experiment.id is not None

    # Select a variant (stochastic – just assert it's one of the two)
    variant = await service.select_variant(experiment.id)
    assert variant is not None
    assert variant.label in ("control", "variant_a")

    # Record a result
    result = await service.record_result(
        variant_id=variant.id,
        user_id=user.id,
        score=0.85,
        feedback="Great response!"
    )
    assert result.score == 0.85

    # Stats
    stats = await service.get_experiment_stats(experiment.id)
    assert len(stats) == 2
    responding = [s for s in stats if s["responses"] > 0]
    assert len(responding) == 1
    assert responding[0]["avg_score"] == 0.85


@pytest.mark.asyncio
async def test_ab_api(client, db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user(f"ab_api_user_{uuid.uuid4()}")
    await db_session.flush()
    await db_session.commit()

    headers = {"X-User-ID": user.external_id}

    # Create
    resp = await client.post(
        "/api/ab-testing/experiments",
        json={
            "name": "Greeting Test",
            "variants": [
                {"label": "formal", "prompt_template": "Dear user, {query}"},
                {"label": "casual", "prompt_template": "Hey! {query}"},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    experiment_id = resp.json()["experiment_id"]

    # Select variant
    resp = await client.get(f"/api/ab-testing/experiments/{experiment_id}/variant")
    assert resp.status_code == 200
    variant_id = resp.json()["variant_id"]

    # Record result
    resp = await client.post(
        "/api/ab-testing/results",
        json={"variant_id": variant_id, "score": 0.9},
        headers=headers,
    )
    assert resp.status_code == 200

    # Stats
    resp = await client.get(f"/api/ab-testing/experiments/{experiment_id}/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert len(stats) == 2
