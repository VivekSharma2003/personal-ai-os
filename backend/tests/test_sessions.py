"""
Tests for IP Allowlisting and Session Security.
"""
import pytest
import pytest_asyncio
from uuid import uuid4

from app.models.user import User
from app.services.api_key_service import APIKeyService
from app.services.session_service import SessionService


@pytest_asyncio.fixture
async def session_user(db_session):
    """Create a test user."""
    user = User(external_id=f"session_test_{uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def session_api_key(db_session, session_user):
    """Create an API key for the user."""
    service = APIKeyService(db_session)
    api_key, raw_key = await service.create_key(
        user_id=session_user.id,
        name="Session Key",
    )
    return api_key, raw_key


@pytest.mark.asyncio
async def test_session_tracking_and_allowlist(db_session, session_user, session_api_key):
    """Test IP allowlisting validation and session tracking."""
    api_key, raw_key = session_api_key
    service = SessionService(db_session)

    # 1. Test check_ip_allowed with empty allowlist (all allowed)
    assert service.check_ip_allowed([], "192.168.1.10") is True

    # 2. Configure allowlist
    res = await service.set_ip_allowlist(api_key.id, ["192.168.1.0/24", "10.0.0.1/32"])
    assert "192.168.1.0/24" in res["ip_allowlist"]

    # 3. Test check_ip_allowed validation
    assert service.check_ip_allowed(res["ip_allowlist"], "192.168.1.10") is True
    assert service.check_ip_allowed(res["ip_allowlist"], "10.0.0.1") is True
    assert service.check_ip_allowed(res["ip_allowlist"], "8.8.8.8") is False

    # 4. Test tracking request (upsert session)
    sess = await service.track_request(
        user_id=session_user.id,
        api_key_id=api_key.id,
        ip_address="192.168.1.10",
        user_agent="Mozilla/5.0",
    )
    assert sess.request_count == 1
    assert sess.ip_address == "192.168.1.10"

    # Repeat request from same IP should increment count
    sess2 = await service.track_request(
        user_id=session_user.id,
        api_key_id=api_key.id,
        ip_address="192.168.1.10",
    )
    assert sess2.id == sess.id
    assert sess2.request_count == 2


@pytest.mark.asyncio
async def test_session_routes(client, db_session, session_user, session_api_key):
    """Test session REST endpoints."""
    api_key, raw_key = session_api_key
    headers = {"X-User-ID": str(session_user.id)}

    # Set IP allowlist
    payload = {"cidrs": ["192.168.1.0/24"]}
    response = await client.put(f"/api/keys/{api_key.id}/ip-allowlist", json=payload, headers=headers)
    assert response.status_code == 200
    assert "192.168.1.0/24" in response.json()["ip_allowlist"]

    # Get IP allowlist
    response = await client.get(f"/api/keys/{api_key.id}/ip-allowlist", headers=headers)
    assert response.status_code == 200
    assert response.json()["ip_allowlist"] == ["192.168.1.0/24"]

    # List active sessions (should be empty initially)
    response = await client.get("/api/sessions", headers=headers)
    assert response.status_code == 200
    assert response.json()["total"] == 0

    # Detect anomalies
    response = await client.get("/api/sessions/anomalies", headers=headers)
    assert response.status_code == 200
    assert "anomalies" in response.json()
