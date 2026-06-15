"""
Tests for API Key Management.
"""
import pytest
import pytest_asyncio
from uuid import uuid4

from app.models.user import User
from app.services.api_key_service import APIKeyService


@pytest_asyncio.fixture
async def api_key_user(db_session):
    """Create a test user for API key tests."""
    user = User(external_id=f"apikey_test_{uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.mark.asyncio
async def test_create_and_validate_key(db_session, api_key_user):
    """Test creating an API key and validating it."""
    service = APIKeyService(db_session)

    api_key, raw_key = await service.create_key(
        user_id=api_key_user.id,
        name="Test Key",
        scopes=["chat", "rules"],
    )

    assert api_key is not None
    assert raw_key.startswith("paios_")
    assert api_key.name == "Test Key"
    assert api_key.scopes == ["chat", "rules"]
    assert api_key.is_active is True

    # Validate the key
    validated = await service.validate_key(raw_key)
    assert validated is not None
    assert validated.id == api_key.id


@pytest.mark.asyncio
async def test_invalid_key_returns_none(db_session):
    """Test that an invalid key returns None."""
    service = APIKeyService(db_session)
    result = await service.validate_key("paios_invalid_key_that_does_not_exist")
    assert result is None


@pytest.mark.asyncio
async def test_revoke_key(db_session, api_key_user):
    """Test revoking an API key."""
    service = APIKeyService(db_session)

    api_key, raw_key = await service.create_key(
        user_id=api_key_user.id,
        name="Revocable Key",
    )

    # Revoke
    revoked = await service.revoke_key(api_key.id, api_key_user.id)
    assert revoked is not None
    assert revoked.is_active is False

    # Validating revoked key should fail
    result = await service.validate_key(raw_key)
    assert result is None


@pytest.mark.asyncio
async def test_rotate_key(db_session, api_key_user):
    """Test rotating an API key."""
    service = APIKeyService(db_session)

    old_key, old_raw = await service.create_key(
        user_id=api_key_user.id,
        name="Rotatable Key",
        scopes=["chat"],
    )

    result = await service.rotate_key(old_key.id, api_key_user.id)
    assert result is not None

    new_key, new_raw = result
    assert new_key.name == "Rotatable Key"
    assert new_key.scopes == ["chat"]
    assert new_raw != old_raw

    # Old key should be revoked
    old_validated = await service.validate_key(old_raw)
    assert old_validated is None

    # New key should work
    new_validated = await service.validate_key(new_raw)
    assert new_validated is not None


@pytest.mark.asyncio
async def test_list_keys(db_session, api_key_user):
    """Test listing API keys for a user."""
    service = APIKeyService(db_session)

    await service.create_key(user_id=api_key_user.id, name="Key 1")
    await service.create_key(user_id=api_key_user.id, name="Key 2")

    keys = await service.list_keys(api_key_user.id)
    assert len(keys) >= 2
    names = {k.name for k in keys}
    assert "Key 1" in names
    assert "Key 2" in names


@pytest.mark.asyncio
async def test_scope_checking(db_session, api_key_user):
    """Test scope validation on API keys."""
    service = APIKeyService(db_session)

    # Key with specific scopes
    key, _ = await service.create_key(
        user_id=api_key_user.id,
        name="Scoped Key",
        scopes=["chat", "rules"],
    )
    assert service.check_scope(key, "chat") is True
    assert service.check_scope(key, "rules") is True
    assert service.check_scope(key, "admin") is False

    # Key with wildcard scope
    wildcard_key, _ = await service.create_key(
        user_id=api_key_user.id,
        name="Admin Key",
        scopes=["*"],
    )
    assert service.check_scope(wildcard_key, "anything") is True
