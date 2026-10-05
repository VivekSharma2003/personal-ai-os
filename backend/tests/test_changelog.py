"""
Personal AI OS - Test Rule Changelog
"""
import pytest
import uuid
from app.services.changelog_service import ChangelogService, _unified_diff
from app.services.rule_engine import RuleEngineService


# ── Unit tests ─────────────────────────────────────────────────────────────────

def test_unified_diff_shows_change():
    patch = _unified_diff("Always use tabs.", "Always use spaces.")
    assert "-Always use tabs." in patch
    assert "+Always use spaces." in patch


def test_unified_diff_no_change():
    patch = _unified_diff("Same content", "Same content")
    assert patch == "(no change)"


def test_unified_diff_from_none():
    patch = _unified_diff(None, "First version of the rule.")
    assert "+First version of the rule." in patch


# ── Integration tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_and_history(db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user(f"cl_user_{uuid.uuid4()}")
    await db_session.flush()
    rule = await rule_engine.create_rule(user.id, "Use tabs for indentation", "style", "test")
    await db_session.commit()

    service = ChangelogService(db_session)

    # Record version 1 (creation)
    e1 = await service.record(rule.id, "Use tabs for indentation", changed_by=user.external_id, change_reason="created")
    await db_session.commit()

    # Record version 2 (edit)
    e2 = await service.record(
        rule.id,
        "Use 4 spaces for indentation",
        old_content="Use tabs for indentation",
        changed_by=user.external_id,
        change_reason="style guide updated",
    )
    await db_session.commit()

    # History returns both, in order
    history = await service.get_history(rule.id)
    assert len(history) == 2
    assert history[0].version == 1
    assert history[1].version == 2

    # Fetch specific version
    v1 = await service.get_version(rule.id, 1)
    assert v1.new_content == "Use tabs for indentation"


@pytest.mark.asyncio
async def test_diff_between_versions(db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user(f"cl_diff_{uuid.uuid4()}")
    await db_session.flush()
    rule = await rule_engine.create_rule(user.id, "Original rule content", "general", "test")
    await db_session.commit()

    service = ChangelogService(db_session)
    await service.record(rule.id, "Original rule content")
    await service.record(rule.id, "Updated rule content", old_content="Original rule content")
    await db_session.commit()

    diff = await service.diff(rule.id, 1, 2)
    assert diff["from_version"] == 1
    assert diff["to_version"] == 2
    assert "-Original rule content" in diff["patch"]
    assert "+Updated rule content" in diff["patch"]


@pytest.mark.asyncio
async def test_changelog_api(client, db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user(f"cl_api_{uuid.uuid4()}")
    await db_session.flush()
    rule = await rule_engine.create_rule(user.id, "Be concise in your answers", "general", "test")
    await db_session.commit()

    rule_id = str(rule.id)

    # Record via API
    resp = await client.post(f"/api/changelog/{rule_id}", json={
        "new_content": "Be concise in your answers",
        "changed_by": user.external_id,
        "change_reason": "initial creation",
    })
    assert resp.status_code == 200
    assert resp.json()["version"] == 1

    resp = await client.post(f"/api/changelog/{rule_id}", json={
        "old_content": "Be concise in your answers",
        "new_content": "Be concise and clear in your answers",
        "changed_by": user.external_id,
        "change_reason": "clarification",
    })
    assert resp.status_code == 200
    assert resp.json()["version"] == 2

    # History
    resp = await client.get(f"/api/changelog/{rule_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # Specific version
    resp = await client.get(f"/api/changelog/{rule_id}/1")
    assert resp.status_code == 200
    assert resp.json()["version"] == 1

    # Diff
    resp = await client.get(f"/api/changelog/{rule_id}/diff?from=1&to=2")
    assert resp.status_code == 200
    data = resp.json()
    assert "patch" in data
    assert "-Be concise in your answers" in data["patch"]
