"""
Personal AI OS - Rule Extractor Background Job

Handles asynchronous rule extraction for complex corrections.
"""
import asyncio
from datetime import datetime
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.interaction import Interaction
from app.models.rule import Rule
from app.core.extraction import process_correction
from app.services.rule_engine import RuleEngineService


async def process_pending_extractions():
    """
    Process any pending rule extractions.
    
    This is useful for retrying failed extractions or
    batch processing corrections during low-traffic periods.
    """
    print(f"[RuleExtractor] Starting extraction processing at {datetime.utcnow()}")
    
    async with async_session_maker() as db:
        try:
            # Find interactions that were corrected but have no extracted rule
            result = await db.execute(
                select(Interaction)
                .where(Interaction.was_corrected == True)
                .where(Interaction.extracted_rule_id == None)
                .where(Interaction.correction_text != None)
                .limit(50)  # Process in batches
            )
            interactions = result.scalars().all()
            
            if not interactions:
                print("[RuleExtractor] No pending extractions")
                return
            
            processed = 0
            successful = 0
            
            for interaction in interactions:
                try:
                    service = RuleEngineService(db)
                    
                    # Get existing rules for duplicate detection
                    existing_rules = await service.get_active_rules(interaction.user_id)
                    existing_rules_data = [r.to_dict() for r in existing_rules]
                    
                    # Process the correction
                    result = await process_correction(
                        user_correction=interaction.correction_text,
                        previous_response=interaction.assistant_response,
                        existing_rules=existing_rules_data
                    )
                    
                    if result["status"] == "rule_created":
                        rule_data = result["rule"]
                        rule = await service.create_rule(
                            user_id=interaction.user_id,
                            content=rule_data["content"],
                            category=rule_data["category"],
                            original_correction=rule_data["original_correction"],
                            embedding=rule_data.get("embedding")
                        )
                        
                        interaction.extracted_rule_id = rule.id
                        successful += 1
                    
                    processed += 1
                    
                except Exception as e:
                    print(f"[RuleExtractor] Error processing interaction {interaction.id}: {e}")
                    continue
            
            await db.commit()
            print(f"[RuleExtractor] Completed: {processed} processed, {successful} rules created")
            
        except Exception as e:
            print(f"[RuleExtractor] Error: {e}")
            await db.rollback()
            raise
