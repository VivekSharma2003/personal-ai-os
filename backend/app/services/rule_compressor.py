"""
Personal AI OS - Adaptive Rule Compressor
"""
import logging
from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.rule import Rule, RuleStatus
from app.services.rule_engine import RuleEngineService

logger = logging.getLogger(__name__)

class RuleCompressorService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rule_engine = RuleEngineService(db)

    async def _mock_llm_compress(self, rules: List[Rule]) -> str:
        """
        Simulates an LLM call to compress multiple rules into one terse rule.
        """
        return "Merged rules: " + ", ".join([r.content[:20] + "..." for r in rules])

    async def compress_category(self, user_id: UUID, category: str) -> Dict[str, Any]:
        """
        Compresses all active rules in a specific category for a user.
        """
        rules = await self.rule_engine.get_user_rules(user_id, status=RuleStatus.ACTIVE.value)
        
        category_rules = [r for r in rules if r.category == category]
        
        if len(category_rules) < 2:
            return {"status": "skipped", "message": "Not enough rules to compress."}
            
        compressed_content = await self._mock_llm_compress(category_rules)
        
        # Archive old rules
        for r in category_rules:
            await self.rule_engine.update_rule_status(r.id, RuleStatus.ARCHIVED.value)
            
        # Create new compressed rule
        new_rule = await self.rule_engine.create_rule(
            user_id=user_id,
            content=compressed_content,
            category=category,
            original_correction="Auto-compressed from multiple rules"
        )
        
        await self.db.commit()
        
        return {
            "status": "success",
            "compressed_count": len(category_rules),
            "new_rule_id": str(new_rule.id)
        }
