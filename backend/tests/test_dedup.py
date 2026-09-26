"""
Personal AI OS - Test Semantic Rule Deduplication
"""
import pytest
import uuid
from app.services.dedup_service import DedupService, _jaccard, _trigrams
from app.services.rule_engine import RuleEngineService


# ── Unit tests (pure) ──────────────────────────────────────────────────────────

def test_trigrams_short_text():
    tg = _trigrams("hello world")
    assert tg == {"hello", "world"}


def test_jaccard_identical():
    assert _jaccard("always use single quotes", "always use single quotes") == 1.0


def test_jaccard_different():
    sim = _jaccard("always use single quotes", "never write spaghetti code")
    assert sim == 0.0


def test_jaccard_partial():
    sim = _jaccard(
        "always prefer single quotes for strings",
        "always prefer double quotes for strings",
    )
    # shares 'always prefer ... quotes for strings' trigrams — expect some overlap
    assert sim > 0.0
    assert sim < 1.0


# ── Integration tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_find_exact_duplicates(db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user(f"dedup_user_{uuid.uuid4()}")
    await db_session.flush()

    # Two identical rules
    await rule_engine.create_rule(user.id, "Always use single quotes", "style", "test")
    await rule_engine.create_rule(user.id, "always use single quotes", "style", "test")
    await db_session.commit()

    service = DedupService(db_session)
    groups = await service.find_duplicates(user.id)

    assert len(groups) >= 1
    assert groups[0]["reason"] == "exact"
    assert groups[0]["similarity"] == 1.0


@pytest.mark.asyncio
async def test_find_similar_duplicates(db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user(f"dedup_sim_{uuid.uuid4()}")
    await db_session.flush()

    await rule_engine.create_rule(user.id, "prefer single quotes for all Python strings", "style", "test")
    await rule_engine.create_rule(user.id, "prefer single quotes for all python code strings", "style", "test")
    await db_session.commit()

    service = DedupService(db_session)
    groups = await service.find_duplicates(user.id, similarity_threshold=0.5)

    assert len(groups) >= 1
    assert groups[0]["reason"] == "trigram"


@pytest.mark.asyncio
async def test_merge_duplicates(db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user(f"dedup_merge_{uuid.uuid4()}")
    await db_session.flush()

    r1 = await rule_engine.create_rule(user.id, "Use tabs for indentation", "style", "test")
    r2 = await rule_engine.create_rule(user.id, "Use tabs not spaces for indentation", "style", "test")
    await db_session.commit()

    service = DedupService(db_session)
    result = await service.merge(user.id, [r1.id, r2.id], "Use tabs for indentation always")

    assert result["new_rule_id"] is not None
    assert str(r1.id) in result["archived_ids"]
    assert str(r2.id) in result["archived_ids"]


@pytest.mark.asyncio
async def test_dedup_api_scan(client, db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user(f"dedup_api_{uuid.uuid4()}")
    await db_session.flush()

    await rule_engine.create_rule(user.id, "Always write descriptive variable names", "coding", "test")
    await rule_engine.create_rule(user.id, "always write descriptive variable names", "coding", "test")
    await db_session.commit()

    resp = await client.get("/api/dedup/scan", headers={"X-User-ID": user.external_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_dedup_api_merge(client, db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user(f"dedup_merge_api_{uuid.uuid4()}")
    await db_session.flush()

    r1 = await rule_engine.create_rule(user.id, "Avoid magic numbers", "coding", "test")
    r2 = await rule_engine.create_rule(user.id, "Never use magic numbers in code", "coding", "test")
    await db_session.commit()

    resp = await client.post(
        "/api/dedup/merge",
        json={
            "rule_ids": [str(r1.id), str(r2.id)],
            "merged_content": "Never use magic numbers; define named constants instead.",
        },
        headers={"X-User-ID": user.external_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["new_rule_id"] is not None
