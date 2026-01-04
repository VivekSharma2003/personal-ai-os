"""
Personal AI OS - Interaction Service

Main orchestration service for handling chat interactions.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rule_engine import RuleEngineService
from app.services.memory import MemoryService
from app.services.prompt_builder import PromptBuilderService
from app.core.llm import generate_response
from app.core.extraction import detect_correction, process_correction


class InteractionService:
    """
    Main service for handling chat interactions.
    
    Orchestrates rule application, response generation, and learning.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rule_engine = RuleEngineService(db)
        self.memory = MemoryService(db)
        self.prompt_builder = PromptBuilderService()
    
    async def process_chat(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message with rule application.
        
        Args:
            user_id: External user ID
            message: The user's message
            conversation_id: Optional conversation ID
        
        Returns:
            Dict with response, rules_applied count, and interaction_id
        """
        # Get or create user
        user = await self.rule_engine.get_or_create_user(user_id)
        
        # Get relevant rules for this context
        rules = await self.rule_engine.get_rules_for_prompt(
            user_id=user.id,
            context=message
        )
        
        # Build prompt with rules
        messages = await self.prompt_builder.build_chat_prompt(
            user_message=message,
            rules=rules,
            conversation_id=conversation_id
        )
        
        # Truncate if needed
        messages = self.prompt_builder.truncate_for_context(messages)
        
        # Generate response
        response = await generate_response(messages)
        
        # Store the interaction
        rule_ids = [UUID(r["id"]) for r in rules if "id" in r]
        interaction = await self.memory.store_interaction(
            user_id=user.id,
            user_message=message,
            assistant_response=response,
            conversation_id=conversation_id,
            rules_applied=rule_ids
        )
        
        # Mark rules as applied
        for rule in rules:
            if "id" in rule:
                await self.rule_engine.mark_rule_applied(UUID(rule["id"]))
        
        # Update conversation context
        if conversation_id:
            await self.prompt_builder.update_conversation_context(
                conversation_id=conversation_id,
                user_message=message,
                assistant_response=response
            )
        
        await self.db.commit()
        
        return {
            "response": response,
            "rules_applied": len(rules),
            "interaction_id": str(interaction.id)
        }
    
    async def process_feedback(
        self,
        interaction_id: str,
        correction: str
    ) -> Dict[str, Any]:
        """
        Process user feedback/correction on a previous response.
        
        Args:
            interaction_id: ID of the interaction being corrected
            correction: The user's correction text
        
        Returns:
            Dict with status, rule info, and message
        """
        # Get the original interaction
        interaction = await self.memory.get_interaction(UUID(interaction_id))
        if not interaction:
            return {
                "status": "error",
                "message": "Interaction not found"
            }
        
        # Detect if this is actually a correction
        is_correction, correction_type, confidence = await detect_correction(
            user_message=correction,
            previous_response=interaction.assistant_response
        )
        
        if not is_correction or confidence < 0.5:
            return {
                "status": "not_a_correction",
                "message": "This doesn't appear to be a correction"
            }
        
        # Get user's existing rules for duplicate detection
        existing_rules = await self.rule_engine.get_active_rules(interaction.user_id)
        existing_rules_data = [r.to_dict() for r in existing_rules]
        
        # Process the correction to extract a rule
        result = await process_correction(
            user_correction=correction,
            previous_response=interaction.assistant_response,
            existing_rules=existing_rules_data
        )
        
        if result["status"] == "rule_created":
            # Create the new rule
            rule_data = result["rule"]
            rule = await self.rule_engine.create_rule(
                user_id=interaction.user_id,
                content=rule_data["content"],
                category=rule_data["category"],
                original_correction=rule_data["original_correction"],
                embedding=rule_data.get("embedding")
            )
            
            # Mark the interaction as corrected
            await self.memory.mark_as_corrected(
                interaction_id=interaction.id,
                correction_text=correction,
                extracted_rule_id=rule.id
            )
            
            await self.db.commit()
            
            return {
                "status": "rule_created",
                "rule": rule.to_dict(),
                "message": result["message"]
            }
        
        elif result["status"] == "duplicate_found":
            # Reinforce the existing rule
            existing_rule = result["existing_rule"]
            if "id" in existing_rule:
                await self.rule_engine.reinforce_rule(UUID(existing_rule["id"]))
            
            await self.memory.mark_as_corrected(
                interaction_id=interaction.id,
                correction_text=correction,
                extracted_rule_id=UUID(existing_rule["id"]) if "id" in existing_rule else None
            )
            
            await self.db.commit()
            
            return {
                "status": "rule_reinforced",
                "rule": existing_rule,
                "message": "This preference already exists and has been reinforced"
            }
        
        else:
            return {
                "status": "extraction_failed",
                "message": result.get("message", "Could not extract a clear rule from this correction")
            }
