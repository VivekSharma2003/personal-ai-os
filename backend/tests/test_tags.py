"""
Tests for Rule Tagging & Grouping (Feature 5).
"""
import pytest
import pytest_asyncio

from app.models.rule_tag import Tag, rule_tags
from app.services.tag_service import TagService
from app.services.rule_engine import RuleEngineService


@pytest.mark.asyncio
async def test_create_tag(db_session):
    """Should create a tag for a user."""
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("tag_test_user")
    await db_session.flush()

    tag_service = TagService(db_session)
    tag = await tag_service.create_tag(
        user_id=user.id,
        name="work",
        color="#3b82f6",
    )

    assert tag.id is not None
    assert tag.name == "work"
    assert tag.color == "#3b82f6"
    assert tag.user_id == user.id


@pytest.mark.asyncio
async def test_list_tags(db_session):
    """Should list all tags for a user."""
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("tag_list_user")
    await db_session.flush()

    tag_service = TagService(db_session)
    await tag_service.create_tag(user_id=user.id, name="creative")
    await tag_service.create_tag(user_id=user.id, name="email")
    await db_session.flush()

    tags = await tag_service.list_tags(user.id)
    assert len(tags) >= 2
    tag_names = [t.name for t in tags]
    assert "creative" in tag_names
    assert "email" in tag_names


@pytest.mark.asyncio
async def test_tag_and_untag_rule(db_session):
    """Should attach and remove tags from a rule."""
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("tag_rule_user")
    rule = await rule_engine.create_rule(
        user_id=user.id,
        content="Taggable rule",
        category="style",
        original_correction="test",
    )
    await db_session.flush()

    tag_service = TagService(db_session)
    tag1 = await tag_service.create_tag(user_id=user.id, name="important")
    tag2 = await tag_service.create_tag(user_id=user.id, name="draft")
    await db_session.flush()

    # Tag the rule
    attached = await tag_service.tag_rule(rule.id, [tag1.id, tag2.id])
    assert len(attached) == 2
    assert "important" in attached
    assert "draft" in attached

    # Untag one tag
    removed = await tag_service.untag_rule(rule.id, [tag1.id])
    assert len(removed) == 1
    assert "important" in removed


@pytest.mark.asyncio
async def test_get_rules_by_tag(db_session):
    """Should return all rules with a specific tag."""
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("rules_by_tag_user")
    rule1 = await rule_engine.create_rule(
        user_id=user.id,
        content="Rule A",
        category="style",
        original_correction="test",
    )
    rule2 = await rule_engine.create_rule(
        user_id=user.id,
        content="Rule B",
        category="tone",
        original_correction="test",
    )
    await db_session.flush()

    tag_service = TagService(db_session)
    tag = await tag_service.create_tag(user_id=user.id, name="group1")
    await db_session.flush()

    await tag_service.tag_rule(rule1.id, [tag.id])
    await tag_service.tag_rule(rule2.id, [tag.id])
    await db_session.flush()

    rules = await tag_service.get_rules_by_tag(tag.id)
    assert len(rules) == 2


@pytest.mark.asyncio
async def test_bulk_tag(db_session):
    """Should bulk-tag multiple rules."""
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("bulk_tag_user")
    rule1 = await rule_engine.create_rule(
        user_id=user.id,
        content="Bulk rule 1",
        category="style",
        original_correction="test",
    )
    rule2 = await rule_engine.create_rule(
        user_id=user.id,
        content="Bulk rule 2",
        category="style",
        original_correction="test",
    )
    await db_session.flush()

    tag_service = TagService(db_session)
    tag = await tag_service.create_tag(user_id=user.id, name="bulk_group")
    await db_session.flush()

    result = await tag_service.bulk_tag(
        rule_ids=[rule1.id, rule2.id],
        tag_ids=[tag.id],
    )

    assert result["rules_tagged"] == 2
    assert result["total_rules"] == 2


@pytest.mark.asyncio
async def test_delete_tag(db_session):
    """Deleting a tag should cascade-remove associations."""
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("delete_tag_user")
    await db_session.flush()

    tag_service = TagService(db_session)
    tag = await tag_service.create_tag(user_id=user.id, name="temporary")
    await db_session.flush()

    deleted = await tag_service.delete_tag(tag.id)
    assert deleted is True

    result = await tag_service.get_tag(tag.id)
    assert result is None


@pytest.mark.asyncio
async def test_tags_api_endpoint(client):
    """The /api/tags endpoint should work end-to-end."""
    # Create a tag
    response = await client.post(
        "/api/tags",
        json={"user_id": "api_tag_user", "name": "api_test", "color": "#ef4444"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "api_test"
    assert data["color"] == "#ef4444"

    # List tags
    response = await client.get(
        "/api/tags",
        params={"user_id": "api_tag_user"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
