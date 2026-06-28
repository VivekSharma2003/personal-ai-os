"""
Tests for Prompt Profiles.
"""
import pytest
import pytest_asyncio
from uuid import uuid4

from app.models.user import User
from app.services.profile_service import ProfileService
from app.services.prompt_builder import PromptBuilderService


@pytest_asyncio.fixture
async def profile_user(db_session):
    """Create a test user."""
    user = User(external_id=f"profile_test_{uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.mark.asyncio
async def test_profile_crud_and_apply(db_session, profile_user):
    """Test creating, cloning, and applying prompt profiles."""
    service = ProfileService(db_session)

    # 1. Create profile
    profile = await service.create_profile(
        user_id=profile_user.id,
        name="Coding Profile",
        description="Optimize for software development",
        rule_filter_categories=["logic"],
        system_preamble="You are an expert software developer.",
        temperature=0.2,
        max_tokens=4000,
        is_default=True,
    )

    assert profile is not None
    assert profile.name == "Coding Profile"
    assert profile.is_default is True

    # 2. Check defaults management (creating another default should unset previous default)
    another = await service.create_profile(
        user_id=profile_user.id,
        name="Writing Profile",
        is_default=True,
    )
    await db_session.refresh(profile)
    assert profile.is_default is False
    assert another.is_default is True

    # 3. Clone profile
    cloned = await service.clone_profile(profile.id, "Cloned Coding Profile")
    assert cloned.name == "Cloned Coding Profile"
    assert cloned.temperature == 0.2

    # 4. Apply profile
    rules = [
        {"id": "r1", "content": "Write tests", "category": "logic", "tag_ids": []},
        {"id": "r2", "content": "Be polite", "category": "tone", "tag_ids": []},
    ]

    applied = await service.apply_profile(profile.id, rules)
    assert len(applied["filtered_rules"]) == 1
    assert applied["filtered_rules"][0]["id"] == "r1"
    assert applied["system_preamble"] == "You are an expert software developer."
    assert applied["temperature"] == 0.2
    assert applied["max_tokens"] == 4000


@pytest.mark.asyncio
async def test_prompt_builder_integration(db_session, profile_user):
    """Test PromptBuilderService using a prompt profile."""
    profile_service = ProfileService(db_session)
    prompt_service = PromptBuilderService()

    profile = await profile_service.create_profile(
        user_id=profile_user.id,
        name="Tech Writer",
        rule_filter_categories=["style"],
        system_preamble="You are a tech writer.",
    )

    rules = [
        {"id": "r1", "content": "Use active voice", "category": "style", "tag_ids": []},
        {"id": "r2", "content": "Keep it long", "category": "length", "tag_ids": []},
    ]

    # Build prompt without profile
    messages_no_profile = await prompt_service.build_chat_prompt(
        user_message="Hello",
        rules=rules,
    )
    assert "active voice" in messages_no_profile[0]["content"]
    assert "Keep it long" in messages_no_profile[0]["content"]
    assert "You are a tech writer" not in messages_no_profile[0]["content"]

    # Build prompt with profile
    messages_with_profile = await prompt_service.build_chat_prompt(
        user_message="Hello",
        rules=rules,
        db=db_session,
        profile_id=str(profile.id),
    )
    assert "active voice" in messages_with_profile[0]["content"]
    assert "Keep it long" not in messages_with_profile[0]["content"]
    assert "You are a tech writer" in messages_with_profile[0]["content"]


@pytest.mark.asyncio
async def test_profile_routes(client, db_session, profile_user):
    """Test profile REST endpoints."""
    headers = {"X-User-ID": str(profile_user.id)}

    # Create profile
    payload = {
        "name": "Route Profile",
        "description": "Created via routes",
        "system_preamble": "Pre",
        "temperature": 0.5,
    }
    response = await client.post("/api/profiles", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Route Profile"

    # Get details
    profile_id = data["id"]
    response = await client.get(f"/api/profiles/{profile_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == profile_id

    # List profiles
    response = await client.get("/api/profiles", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1

    # Clone profile
    response = await client.post(f"/api/profiles/{profile_id}/clone", json={"new_name": "ClonedRoute"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "ClonedRoute"

    # Delete profile
    response = await client.delete(f"/api/profiles/{profile_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
