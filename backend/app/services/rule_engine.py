"""
Personal AI OS - Rule Engine Service

Handles all rule-related operations: CRUD, ranking, and application.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule, RuleStatus, RuleCategory
from app.models.audit_log import AuditLog, AuditEventType
from app.models.user import User
from app.core.algorithms import (
    calculate_confidence,
    rank_rules,
    select_rules_for_prompt
)
from app.core.llm import generate_embedding
from app.db.redis import RuleCache
from app.db.vector import add_embedding, search_similar


class RuleEngineService:
    """Service for managing user rules and preferences."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_or_create_user(self, external_id: str) -> User:
        """Get or create a user by external ID."""
        result = await self.db.execute(
            select(User).where(User.external_id == external_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(external_id=external_id)
            self.db.add(user)
            await self.db.flush()
        
        return user
    
    async def create_rule(
        self,
        user_id: UUID,
        content: str,
        category: str,
        original_correction: str,
        embedding: Optional[List[float]] = None
    ) -> Rule:
        """
        Create a new rule for a user.
        
        Args:
            user_id: UUID of the user
            content: The rule content
            category: Rule category (style, tone, formatting, logic, safety)
            original_correction: The original user correction
            embedding: Pre-computed embedding vector
        
        Returns:
            The created Rule object
        """
        rule = Rule(
            user_id=user_id,
            content=content,
            category=category,
            original_correction=original_correction,
            confidence=0.5,
            status=RuleStatus.ACTIVE.value
        )
        
        self.db.add(rule)
        await self.db.flush()
        
        # Store embedding in vector DB
        if embedding:
            embedding_id = f"rule_{rule.id}"
            await add_embedding(embedding_id, embedding)
            rule.embedding_id = embedding_id
        
        # Log the event
        await self._log_event(
            user_id=user_id,
            rule_id=rule.id,
            event_type=AuditEventType.RULE_CREATED,
            event_data={
                "content": content,
                "category": category,
                "original_correction": original_correction
            }
        )
        
        # Invalidate cache
        await RuleCache.invalidate_user_rules(str(user_id))
        
        return rule
    
    async def get_rule(self, rule_id: UUID) -> Optional[Rule]:
        """Get a rule by ID."""
        result = await self.db.execute(
            select(Rule).where(Rule.id == rule_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_rules(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Rule]:
        """
        Get all rules for a user with optional filters.
        
        Args:
            user_id: UUID of the user
            status: Filter by status (active, archived, disabled)
            category: Filter by category
        
        Returns:
            List of Rule objects
        """
        query = select(Rule).where(Rule.user_id == user_id)
        
        if status:
            query = query.where(Rule.status == status)
        if category:
            query = query.where(Rule.category == category)
        
        query = query.order_by(Rule.confidence.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_active_rules(self, user_id: UUID) -> List[Rule]:
        """Get all active rules for a user."""
        return await self.get_user_rules(user_id, status=RuleStatus.ACTIVE.value)
    
    async def get_rules_for_prompt(
        self,
        user_id: UUID,
        context: Optional[str] = None,
        max_rules: int = 10
    ) -> List[Rule]:
        """
        Get rules to include in the prompt, ranked by relevance.
        
        Args:
            user_id: UUID of the user
            context: Current context for relevance ranking
            max_rules: Maximum number of rules to return
        
        Returns:
            List of Rule objects sorted by relevance
        """
        # Check cache first
        cached = await RuleCache.get_user_rules(str(user_id))
        if cached:
            rules_data = cached
        else:
            rules = await self.get_active_rules(user_id)
            rules_data = [rule.to_dict() for rule in rules]
            await RuleCache.set_user_rules(str(user_id), rules_data)
        
        # Get context embedding for relevance ranking
        context_embedding = None
        if context:
            try:
                context_embedding = await generate_embedding(context)
            except Exception:
                pass
        
        # Rank and select
        selected = select_rules_for_prompt(rules_data, context_embedding)
        return selected[:max_rules]
    
    async def update_rule(
        self,
        rule_id: UUID,
        content: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None
    ) -> Optional[Rule]:
        """
        Update a rule's content or status.
        
        Args:
            rule_id: UUID of the rule
            content: New content (optional)
            status: New status (optional)
            category: New category (optional)
        
        Returns:
            Updated Rule object or None if not found
        """
        rule = await self.get_rule(rule_id)
        if not rule:
            return None
        
        old_content = rule.content
        old_status = rule.status
        
        if content:
            rule.content = content
            # Update embedding
            try:
                embedding = await generate_embedding(content)
                embedding_id = f"rule_{rule.id}"
                await add_embedding(embedding_id, embedding)
                rule.embedding_id = embedding_id
            except Exception:
                pass
        
        if status:
            rule.status = status
        
        if category:
            rule.category = category
        
        rule.updated_at = datetime.utcnow()
        
        # Log the event
        await self._log_event(
            user_id=rule.user_id,
            rule_id=rule.id,
            event_type=AuditEventType.RULE_EDITED,
            event_data={
                "old_content": old_content,
                "new_content": content or old_content,
                "old_status": old_status,
                "new_status": status or old_status
            }
        )
        
        # Invalidate cache
        await RuleCache.invalidate_user_rules(str(rule.user_id))
        
        return rule
    
    async def delete_rule(self, rule_id: UUID) -> bool:
        """
        Delete a rule.
        
        Args:
            rule_id: UUID of the rule
        
        Returns:
            True if deleted, False if not found
        """
        rule = await self.get_rule(rule_id)
        if not rule:
            return False
        
        user_id = rule.user_id
        
        # Log before deletion
        await self._log_event(
            user_id=user_id,
            rule_id=rule_id,
            event_type=AuditEventType.RULE_DELETED,
            event_data={"content": rule.content}
        )
        
        await self.db.delete(rule)
        
        # Invalidate cache
        await RuleCache.invalidate_user_rules(str(user_id))
        
        return True
    
    async def toggle_rule(self, rule_id: UUID) -> Optional[Rule]:
        """Toggle a rule between active and disabled."""
        rule = await self.get_rule(rule_id)
        if not rule:
            return None
        
        new_status = (
            RuleStatus.DISABLED.value 
            if rule.status == RuleStatus.ACTIVE.value 
            else RuleStatus.ACTIVE.value
        )
        
        return await self.update_rule(rule_id, status=new_status)
    
    async def reinforce_rule(self, rule_id: UUID) -> Optional[Rule]:
        """
        Reinforce a rule (increase confidence when user confirms it).
        
        Args:
            rule_id: UUID of the rule
        
        Returns:
            Updated Rule object
        """
        rule = await self.get_rule(rule_id)
        if not rule:
            return None
        
        rule.times_reinforced += 1
        rule.last_reinforced_at = datetime.utcnow()
        rule.confidence = calculate_confidence(
            base_confidence=0.5,
            times_reinforced=rule.times_reinforced,
            last_applied_at=rule.last_applied_at
        )
        rule.updated_at = datetime.utcnow()
        
        await self._log_event(
            user_id=rule.user_id,
            rule_id=rule.id,
            event_type=AuditEventType.RULE_REINFORCED,
            event_data={"new_confidence": rule.confidence}
        )
        
        await RuleCache.invalidate_user_rules(str(rule.user_id))
        
        return rule
    
    async def mark_rule_applied(self, rule_id: UUID) -> Optional[Rule]:
        """
        Mark a rule as applied (update last_applied_at and times_applied).
        
        Args:
            rule_id: UUID of the rule
        
        Returns:
            Updated Rule object
        """
        rule = await self.get_rule(rule_id)
        if not rule:
            return None
        
        rule.times_applied += 1
        rule.last_applied_at = datetime.utcnow()
        
        await self._log_event(
            user_id=rule.user_id,
            rule_id=rule.id,
            event_type=AuditEventType.RULE_APPLIED,
            event_data={"times_applied": rule.times_applied}
        )
        
        return rule
    
    async def archive_rule(self, rule_id: UUID, reason: str = "decay") -> Optional[Rule]:
        """Archive a rule (low confidence or not used)."""
        rule = await self.get_rule(rule_id)
        if not rule:
            return None
        
        rule.status = RuleStatus.ARCHIVED.value
        rule.updated_at = datetime.utcnow()
        
        await self._log_event(
            user_id=rule.user_id,
            rule_id=rule.id,
            event_type=AuditEventType.RULE_ARCHIVED,
            event_data={"reason": reason}
        )
        
        await RuleCache.invalidate_user_rules(str(rule.user_id))
        
        return rule
    
    async def _log_event(
        self,
        user_id: UUID,
        rule_id: UUID,
        event_type: AuditEventType,
        event_data: dict
    ):
        """Log an audit event."""
        log = AuditLog(
            user_id=user_id,
            rule_id=rule_id,
            event_type=event_type.value,
            event_data=event_data
        )
        self.db.add(log)
