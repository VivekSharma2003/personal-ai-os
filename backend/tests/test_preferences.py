"""
Personal AI OS - Test User Preferences
"""
import pytest
import uuid
from app.services.preferences_service import PreferencesService, _deep_merge
from app.services.rule_engine import RuleEngineService


# ── Unit tests ─────────────────────────────────────────────────────────────────

def test_deep_merge_simple():
    base = {"a": 1, "b": {"x": 10, "y": 20}}
    patch = {"b": {"y": 99, "z": 30}, "c": 3}
    result = _deep_merge(base, patch)
    assert result == {"a": 1, "b": {"x": 10, "y": 99, "z": 30}, "c": 3}


def test_deep_merge_patch_wins_on_scalar():
    base = {"model": "gpt-3.5-turbo"}
    patch = {"model": "gpt-4o"}
    assert _deep_merge(base, patch)["model"] == "gpt-4o"


def test_deep_merge_empty_patch_leaves_base():
    base = {"theme": "dark"}
    assert _deep_merge(base, {}) == base


# ── Integration tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_or_create_is_idempotent(db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user(f"pref_user_{uuid.uuid4()}")
    await db_session.flush()

    service = PreferencesService(db_session)
    p1 = await service.get_or_create(user.id)
    p2 = await service.get_or_create(user.id)
    assert p1.id == p2.id


@pytest.mark.asyncio
async def test_patch_deep_merges(db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user(f"pref_patch_{uuid.uuid4()}")
    await db_session.flush()

    service = PreferencesService(db_session)
    await service.patch(user.id, llm={"provider": "openai", "temperature": 0.7})
    prefs = await service.patch(user.id, llm={"temperature": 0.9, "model": "gpt-4o"})

    assert prefs.llm["provider"] == "openai"   # preserved from first patch
    assert prefs.llm["temperature"] == 0.9     # updated
    assert prefs.llm["model"] == "gpt-4o"      # added


@pytest.mark.asyncio
async def test_reset_section(db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user(f"pref_reset_{uuid.uuid4()}")
    await db_session.flush()

    service = PreferencesService(db_session)
    await service.patch(user.id, ui={"theme": "dark", "language": "fr"})
    prefs = await service.reset_section(user.id, "ui")
    assert prefs.ui == {}


@pytest.mark.asyncio
async def test_reset_invalid_section(db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user(f"pref_inv_{uuid.uuid4()}")
    await db_session.flush()

    service = PreferencesService(db_session)
    with pytest.raises(ValueError):
        await service.reset_section(user.id, "nonexistent_key")


@pytest.mark.asyncio
async def test_preferences_api(client, db_session):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user(f"pref_api_{uuid.uuid4()}")
    await db_session.flush()
    await db_session.commit()
    headers = {"X-User-ID": user.external_id}

    # GET — creates blank prefs
    resp = await client.get("/api/preferences", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["llm"] == {}

    # PATCH
    resp = await client.patch("/api/preferences", json={
        "llm": {"provider": "anthropic", "model": "claude-3-opus"},
        "ui": {"theme": "dark"},
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["llm"]["provider"] == "anthropic"
    assert data["ui"]["theme"] == "dark"

    # PATCH again — deep merge
    resp = await client.patch("/api/preferences", json={
        "llm": {"temperature": 0.5}
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["llm"]["provider"] == "anthropic"   # preserved
    assert data["llm"]["temperature"] == 0.5        # added

    # DELETE section
    resp = await client.delete("/api/preferences/ui", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["ui"] == {}

    # DELETE invalid section
    resp = await client.delete("/api/preferences/bad_key", headers=headers)
    assert resp.status_code == 400
