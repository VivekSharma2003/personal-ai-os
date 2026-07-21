"""
Personal AI OS - Rule Model Config Service

Manages CRUD operations for rule-specific LLM provider/model configuration overrides.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule_model_config import RuleModelConfig
from app.models.rule import Rule
from app.core.logging import get_logger

logger = get_logger("services.rule_model_config")


class RuleModelConfigService:
    """Service for managing model-specific overrides on user preference rules."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_or_update_override(
        self,
        user_id: UUID,
        rule_id: UUID,
        provider: str,
        model_name: str,
        temperature_override: Optional[float] = None,
        max_tokens_override: Optional[int] = None,
        optimized_content: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or update a model-specific configuration override for a rule."""
        # Verify ownership of the rule
        rule_check = await self.db.execute(
            select(Rule).where(and_(Rule.id == rule_id, Rule.user_id == user_id))
        )
        rule = rule_check.scalar_one_or_none()
        if not rule:
            return {"error": "Rule not found or not owned by user"}

        # Check if config override already exists for this model/provider
        existing_check = await self.db.execute(
            select(RuleModelConfig).where(
                and_(
                    RuleModelConfig.rule_id == rule_id,
                    RuleModelConfig.provider == provider,
                    RuleModelConfig.model_name == model_name,
                )
            )
        )
        config = existing_check.scalar_one_or_none()

        if config:
            # Update existing
            config.temperature_override = temperature_override
            config.max_tokens_override = max_tokens_override
            config.optimized_content = optimized_content
            action = "updated"
        else:
            # Create new
            config = RuleModelConfig(
                id=uuid4(),
                rule_id=rule_id,
                provider=provider,
                model_name=model_name,
                temperature_override=temperature_override,
                max_tokens_override=max_tokens_override,
                optimized_content=optimized_content,
            )
            self.db.add(config)
            action = "created"

        await self.db.flush()
        logger.info(
            f"Rule model override {action}",
            extra={"extra_data": {
                "rule_id": str(rule_id),
                "provider": provider,
                "model_name": model_name,
            }}
        )
        return {"action": action, "config": config.to_dict()}

    async def get_override(self, config_id: UUID) -> Optional[RuleModelConfig]:
        """Fetch override details."""
        result = await self.db.execute(
            select(RuleModelConfig).where(RuleModelConfig.id == config_id)
        )
        return result.scalar_one_or_none()

    async def list_overrides(self, rule_id: UUID, user_id: UUID) -> List[Dict[str, Any]]:
        """List all model configuration overrides for a specific rule."""
        # Verify rule ownership
        rule_check = await self.db.execute(
            select(Rule).where(and_(Rule.id == rule_id, Rule.user_id == user_id))
        )
        if not rule_check.scalar_one_or_none():
            return []

        result = await self.db.execute(
            select(RuleModelConfig)
            .where(RuleModelConfig.rule_id == rule_id)
            .order_by(RuleModelConfig.provider, RuleModelConfig.model_name)
        )
        return [c.to_dict() for c in result.scalars().all()]

    async def delete_override(self, config_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """Delete an override configuration."""
        # Retrieve config override join rule to check owner
        result = await self.db.execute(
            select(RuleModelConfig)
            .join(Rule)
            .where(and_(RuleModelConfig.id == config_id, Rule.user_id == user_id))
        )
        config = result.scalar_one_or_none()
        if not config:
            return {"error": "Override configuration not found or unauthorized"}

        await self.db.delete(config)
        await self.db.flush()
        logger.info(f"Deleted rule model override: {config_id}")
        return {"deleted": True, "id": str(config_id)}

    async def get_active_overrides(
        self, rule_ids: List[UUID], provider: str, model_name: str
    ) -> Dict[UUID, RuleModelConfig]:
        """Retrieve active configuration overrides for a set of rules and a target provider/model."""
        if not rule_ids:
            return {}

        # Fetch configurations matching the provider and either specific model name or wildcard '*'
        result = await self.db.execute(
            select(RuleModelConfig).where(
                and_(
                    RuleModelConfig.rule_id.in_(rule_ids),
                    RuleModelConfig.provider == provider,
                    RuleModelConfig.model_name.in_([model_name, "*"]),
                )
            )
        )
        configs = result.scalars().all()

        # Map by rule_id; specific model takes precedence over '*'
        mapped_configs: Dict[UUID, RuleModelConfig] = {}
        for c in configs:
            existing = mapped_configs.get(c.rule_id)
            if not existing or (existing.model_name == "*" and c.model_name != "*"):
                mapped_configs[c.rule_id] = c

        return mapped_configs
