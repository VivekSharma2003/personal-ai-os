"""
Tests for Feature 30 - Dynamic Variables & Workspace Shared Parameters
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.variable_service import VariableService


@pytest_asyncio.fixture
async def var_user(db_session: AsyncSession):
    user = User(id=uuid4(), external_id=f"var-test-{uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()
    return user


class TestSharedVariables:
    @pytest.mark.asyncio
    async def test_variable_crud_and_resolving(
        self, client: AsyncClient, db_session: AsyncSession, var_user
    ):
        # 1. Create variable
        response = await client.post(
            "/api/variables",
            headers={"X-User-ID": str(var_user.id)},
            json={
                "name": "user_name",
                "value": "Vivek",
                "description": "The user's first name",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "user_name"
        assert data["value"] == "Vivek"

        # 2. List variables
        list_resp = await client.get(
            "/api/variables",
            headers={"X-User-ID": str(var_user.id)},
        )
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

        # 3. Test resolution via service directly
        service = VariableService(db_session)
        rules = [
            {"id": str(uuid4()), "content": "Hello {{user_name}}!"},
            {"id": str(uuid4()), "content": "Year is {{current_year}}"},
        ]
        resolved = await service.resolve_rules(var_user.id, rules)
        assert resolved[0]["content"] == "Hello Vivek!"
        assert str(datetime.utcnow().year) in resolved[1]["content"]

        # 4. Delete variable
        del_resp = await client.delete(
            "/api/variables/user_name",
            headers={"X-User-ID": str(var_user.id)},
        )
        assert del_resp.status_code == 200
