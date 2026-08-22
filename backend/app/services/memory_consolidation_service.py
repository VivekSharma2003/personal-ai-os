"""
Personal AI OS - Memory Consolidation Service
"""
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.interaction import Interaction
from app.models.episodic_memory import EpisodicMemory
from app.core.llm import extract_json_response, generate_embedding
from app.db.vector import add_embedding, search_similar

logger = logging.getLogger(__name__)

class MemoryConsolidationService:
    """
    Service for consolidating conversation threads into Episodic Memories.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _extract_memory_from_interactions(self, interactions: List[Interaction]) -> Dict[str, Any]:
        """Use LLM to summarize interactions and extract key takeaways."""
        
        # Format transcript
        transcript = []
        for i in interactions:
            transcript.append(f"User: {i.user_message}")
            transcript.append(f"Assistant: {i.assistant_response}")
            if i.correction_text:
                transcript.append(f"[Correction]: {i.correction_text}")
                
        text = "\n\n".join(transcript)
        
        prompt = f"""
        Analyze the following conversation transcript and consolidate it into a concise episodic memory.
        Extract the core topics, user preferences, factual information shared, and any significant decisions.
        
        TRANSCRIPT:
        {text}
        
        Respond with a JSON object containing:
        - "summary": A concise paragraph summarizing the entire conversation.
        - "key_takeaways": An array of bullet points highlighting the most important facts, preferences, or decisions.
        """
        
        system_prompt = "You are a specialized AI designed to compress and consolidate memories from conversations."
        
        result = await extract_json_response(prompt, system_prompt=system_prompt)
        return {
            "summary": result.get("summary", "No summary available."),
            "key_takeaways": result.get("key_takeaways", [])
        }

    async def consolidate_thread(self, user_id: UUID, thread_id: str) -> Optional[EpisodicMemory]:
        """Consolidate a specific conversation thread into a memory."""
        result = await self.db.execute(
            select(Interaction)
            .where(Interaction.user_id == user_id, Interaction.conversation_id == thread_id)
            .order_by(Interaction.created_at)
        )
        interactions = result.scalars().all()
        
        if not interactions:
            return None
            
        memory_data = await self._extract_memory_from_interactions(interactions)
        
        # Save to PostgreSQL
        memory = EpisodicMemory(
            user_id=user_id,
            summary=memory_data['summary'],
            key_takeaways=memory_data['key_takeaways'],
            interaction_count=len(interactions)
        )
        self.db.add(memory)
        await self.db.commit()
        await self.db.refresh(memory)
        
        # Generate embedding and save to Vector DB
        embedding_text = f"{memory_data['summary']}\n" + "\n".join(memory_data['key_takeaways'])
        embedding_vector = await generate_embedding(embedding_text)
        
        memory.embedding_id = f"mem_{memory.id}"
        await add_embedding(memory.embedding_id, embedding_vector)
        
        await self.db.commit()
        
        return memory

    async def consolidate_old_threads(self, user_id: UUID, days_old: int = 30) -> Dict[str, int]:
        """Consolidate all threads older than X days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Find distinct conversation_ids older than cutoff
        result = await self.db.execute(
            select(Interaction.conversation_id)
            .where(
                Interaction.user_id == user_id,
                Interaction.created_at <= cutoff_date,
                Interaction.conversation_id.isnot(None)
            )
            .group_by(Interaction.conversation_id)
        )
        thread_ids = result.scalars().all()
        
        memories_created = 0
        for tid in thread_ids:
            try:
                # In a real app we'd track if it was already processed.
                memory = await self.consolidate_thread(user_id, tid)
                if memory:
                    memories_created += 1
            except Exception as e:
                logger.error(f"Failed to consolidate thread {tid}: {str(e)}")
                
        return {
            "threads_processed": len(thread_ids),
            "memories_created": memories_created
        }
        
    async def search_memories(self, user_id: UUID, query: str, top_k: int = 5) -> List[EpisodicMemory]:
        """Search memories semantically using Vector DB."""
        query_embedding = await generate_embedding(query)
        
        # Over-fetch because we don't have native FAISS metadata filtering
        results = await search_similar(query_embedding, k=top_k * 5)
        
        if not results:
            return []
            
        # Filter for episodic memories matching this user
        memory_ids = []
        for embedding_id, _ in results:
            if embedding_id.startswith("mem_"):
                try:
                    memory_ids.append(UUID(embedding_id[4:]))
                except ValueError:
                    pass
                    
        if not memory_ids:
            return []
            
        db_result = await self.db.execute(
            select(EpisodicMemory)
            .where(
                EpisodicMemory.id.in_(memory_ids),
                EpisodicMemory.user_id == user_id
            )
        )
        
        memories = {m.id: m for m in db_result.scalars().all()}
        
        # Return in order of similarity, up to top_k
        ordered_memories = []
        for memory_id in memory_ids:
            if memory_id in memories and memories[memory_id] not in ordered_memories:
                ordered_memories.append(memories[memory_id])
                if len(ordered_memories) >= top_k:
                    break
                
        return ordered_memories
