"""
Personal AI OS - Variable Service

Manages dynamic placeholders and workspace shared parameters, replacing them in rules.
"""
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shared_variable import SharedVariable
from app.core.logging import get_logger

logger = get_logger("services.variable")


class VariableService:
    """Service to perform CRUD operations on shared variables and resolve placeholders in rules."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def set_variable(
        self,
        user_id: UUID,
        name: str,
        value: str,
        description: Optional[str] = None,
    ) -> SharedVariable:
        """Create or update a shared variable for a user."""
        # Validate name: alphanumeric + underscores only
        if not re.match(r"^[a-zA-Z0-9_]+$", name):
            raise ValueError("Variable name must be alphanumeric with underscores only")

        stmt = select(SharedVariable).where(
            and_(SharedVariable.user_id == user_id, SharedVariable.name == name)
        )
        result = await self.db.execute(stmt)
        variable = result.scalar_one_or_none()

        if variable:
            variable.value = value
            variable.description = description
        else:
            variable = SharedVariable(
                id=uuid4(),
                user_id=user_id,
                name=name,
                value=value,
                description=description,
            )
            self.db.add(variable)

        await self.db.flush()
        logger.info(f"Variable set: {name}={value[:30]}")
        return variable

    async def list_variables(self, user_id: UUID) -> List[SharedVariable]:
        """List all shared variables for a user."""
        stmt = select(SharedVariable).where(SharedVariable.user_id == user_id).order_by(SharedVariable.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_variable(self, user_id: UUID, name: str) -> Dict[str, Any]:
        """Delete a shared variable by name."""
        stmt = delete(SharedVariable).where(
            and_(SharedVariable.user_id == user_id, SharedVariable.name == name)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return {"deleted": True, "count": result.rowcount}

    async def resolve_rules(self, user_id: UUID, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Replace all variable placeholders (e.g. {{user_name}}) in rules.
        Also resolves standard variables like {{current_year}}.
        """
        if not rules:
            return []

        # Fetch all variables
        vars_list = await self.list_variables(user_id)
        var_map = {v.name: v.value for v in vars_list}

        # Add system variables
        var_map["current_year"] = str(datetime.utcnow().year)

        resolved_rules = []
        for r in rules:
            rule_copy = dict(r)
            content = rule_copy.get("content", "")

            # Regex replacement: find all {{name}}
            def replacer(match):
                var_name = match.group(1)
                return var_map.get(var_name, match.group(0))

            resolved_content = re.sub(r"\{\{([a-zA-Z0-9_]+)\}\}", replacer, content)
            rule_copy["content"] = resolved_content
            resolved_rules.append(rule_copy)

        return resolved_rules
