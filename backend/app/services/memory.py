"""
Personal AI OS - Memory Service

Handles vector-based semantic memory for context-aware rule application.
"""
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interaction import Interaction
from app.core.llm import generate_embedding
from app.db.vector import add_embedding, search_similar


class MemoryService:
    """Service for managing semantic memory via vector search."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def store_interaction(
        self,
        user_id: UUID,
        user_message: str,
        assistant_response: str,
        conversation_id: Optional[str] = None,
        rules_applied: Optional[List[UUID]] = None
    ) -> Interaction:
        """
        Store an interaction and its embedding for future retrieval.
        
        Args:
            user_id: UUID of the user
            user_message: The user's message
            assistant_response: The AI's response
            conversation_id: Optional conversation ID
            rules_applied: List of rule IDs that were applied
        
        Returns:
            The created Interaction object
        """
        interaction = Interaction(
            user_id=user_id,
            user_message=user_message,
            assistant_response=assistant_response,
            conversation_id=conversation_id,
            rules_applied=rules_applied or []
        )
        
        self.db.add(interaction)
        await self.db.flush()
        
        # Generate and store embedding for the interaction
        try:
            # Combine user message and response for richer embedding
            combined_text = f"User: {user_message}\nAssistant: {assistant_response}"
            embedding = await generate_embedding(combined_text[:2000])  # Truncate for token limit
            
            embedding_id = f"interaction_{interaction.id}"
            await add_embedding(embedding_id, embedding)
            interaction.embedding_id = embedding_id
        except Exception as e:
            print(f"Failed to store interaction embedding: {e}")
        
        return interaction
    
    async def mark_as_corrected(
        self,
        interaction_id: UUID,
        correction_text: str,
        extracted_rule_id: Optional[UUID] = None
    ) -> Optional[Interaction]:
        """
        Mark an interaction as corrected.
        
        Args:
            interaction_id: UUID of the interaction
            correction_text: The user's correction
            extracted_rule_id: ID of the rule extracted from this correction
        
        Returns:
            Updated Interaction object or None if not found
        """
        result = await self.db.execute(
            select(Interaction).where(Interaction.id == interaction_id)
        )
        interaction = result.scalar_one_or_none()
        
        if not interaction:
            return None
        
        interaction.was_corrected = True
        interaction.correction_text = correction_text
        if extracted_rule_id:
            interaction.extracted_rule_id = extracted_rule_id
        
        return interaction
    
    async def find_similar_interactions(
        self,
        query: str,
        user_id: UUID,
        k: int = 5,
        threshold: float = 0.7
    ) -> List[Tuple[Interaction, float]]:
        """
        Find similar past interactions using semantic search.
        
        Args:
            query: The query text to search for
            user_id: UUID of the user
            k: Maximum number of results
            threshold: Minimum similarity threshold
        
        Returns:
            List of (Interaction, similarity_score) tuples
        """
        try:
            query_embedding = await generate_embedding(query)
            similar_ids = await search_similar(query_embedding, k=k, threshold=threshold)
            
            if not similar_ids:
                return []
            
            # Filter to only interaction embeddings and get IDs
            interaction_ids = []
            scores = {}
            for embedding_id, score in similar_ids:
                if embedding_id.startswith("interaction_"):
                    int_id = UUID(embedding_id.replace("interaction_", ""))
                    interaction_ids.append(int_id)
                    scores[int_id] = score
            
            if not interaction_ids:
                return []
            
            # Fetch interactions from DB
            result = await self.db.execute(
                select(Interaction)
                .where(Interaction.id.in_(interaction_ids))
                .where(Interaction.user_id == user_id)
            )
            interactions = result.scalars().all()
            
            # Return with scores
            return [(i, scores.get(i.id, 0.0)) for i in interactions]
        
        except Exception as e:
            print(f"Similar interaction search failed: {e}")
            return []
    
    async def get_conversation_history(
        self,
        user_id: UUID,
        conversation_id: str,
        limit: int = 20
    ) -> List[Interaction]:
        """
        Get recent interactions from a conversation.
        
        Args:
            user_id: UUID of the user
            conversation_id: The conversation ID
            limit: Maximum number of interactions to return
        
        Returns:
            List of Interaction objects, ordered by time
        """
        result = await self.db.execute(
            select(Interaction)
            .where(Interaction.user_id == user_id)
            .where(Interaction.conversation_id == conversation_id)
            .order_by(Interaction.created_at.desc())
            .limit(limit)
        )
        
        interactions = list(result.scalars().all())
        interactions.reverse()  # Oldest first
        return interactions
    
    async def get_correction_examples(
        self,
        user_id: UUID,
        limit: int = 10
    ) -> List[Interaction]:
        """
        Get past interactions where the user made corrections.
        
        Useful for understanding user preferences and rule context.
        
        Args:
            user_id: UUID of the user
            limit: Maximum number of corrections to return
        
        Returns:
            List of corrected Interaction objects
        """
        result = await self.db.execute(
            select(Interaction)
            .where(Interaction.user_id == user_id)
            .where(Interaction.was_corrected == True)
            .order_by(Interaction.created_at.desc())
            .limit(limit)
        )
        
        return list(result.scalars().all())
    
    async def get_interaction(self, interaction_id: UUID) -> Optional[Interaction]:
        """Get a specific interaction by ID."""
        result = await self.db.execute(
            select(Interaction).where(Interaction.id == interaction_id)
        )
        return result.scalar_one_or_none()
