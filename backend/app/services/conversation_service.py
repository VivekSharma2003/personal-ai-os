"""
Personal AI OS - Conversation Service

Manages first-class conversation entities with branching/forking support.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation
from app.models.interaction import Interaction
from app.services.rule_engine import RuleEngineService


class ConversationService:
    """Service for managing conversations with branching support."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_conversation(
        self,
        user_id: UUID,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> Conversation:
        """
        Create a new conversation.

        Args:
            user_id: UUID of the user (internal)
            title: Optional title, defaults to "New Conversation"
            description: Optional description

        Returns:
            The created Conversation object
        """
        conversation = Conversation(
            user_id=user_id,
            title=title or "New Conversation",
            description=description,
        )
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    async def get_conversation(self, conversation_id: UUID) -> Optional[Conversation]:
        """Get a conversation by ID."""
        return await self.db.get(Conversation, conversation_id)

    async def list_conversations(
        self,
        user_id: UUID,
        include_archived: bool = False,
        include_forks: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List conversations for a user with metadata.

        Args:
            user_id: UUID of the user
            include_archived: Whether to include archived conversations
            include_forks: Whether to include forked conversations
            limit: Max results per page
            offset: Pagination offset

        Returns:
            Dict with conversations list and total count
        """
        query = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
        )

        if not include_archived:
            query = query.where(Conversation.is_archived == False)

        if not include_forks:
            query = query.where(Conversation.parent_id.is_(None))

        # Count total
        count_query = (
            select(func.count(Conversation.id))
            .where(Conversation.user_id == user_id)
        )
        if not include_archived:
            count_query = count_query.where(Conversation.is_archived == False)
        if not include_forks:
            count_query = count_query.where(Conversation.parent_id.is_(None))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get conversations with message counts
        query = (
            query
            .order_by(Conversation.is_pinned.desc(), Conversation.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(query)
        conversations = list(result.scalars().all())

        # Enrich with message counts
        enriched = []
        for conv in conversations:
            msg_count = await self._get_message_count(conv.id)
            conv_dict = conv.to_dict()
            conv_dict["message_count"] = msg_count
            enriched.append(conv_dict)

        return {
            "conversations": enriched,
            "total": total,
        }

    async def fork_conversation(
        self,
        conversation_id: UUID,
        at_interaction_id: UUID,
        user_id: UUID,
        title: Optional[str] = None
    ) -> Optional[Conversation]:
        """
        Fork a conversation at a specific message, creating a branch.

        Copies all interactions up to (and including) the specified interaction
        into a new conversation, preserving the original.

        Args:
            conversation_id: UUID of the original conversation
            at_interaction_id: UUID of the interaction to fork at
            user_id: UUID of the user
            title: Optional title for the fork

        Returns:
            The new forked Conversation, or None on error
        """
        # Get original conversation
        original = await self.get_conversation(conversation_id)
        if not original:
            return None

        # Get the fork point interaction
        fork_interaction = await self.db.get(Interaction, at_interaction_id)
        if not fork_interaction:
            return None

        # Get all interactions up to and including the fork point
        result = await self.db.execute(
            select(Interaction)
            .where(Interaction.conversation_id == str(conversation_id))
            .where(Interaction.user_id == user_id)
            .where(Interaction.created_at <= fork_interaction.created_at)
            .order_by(Interaction.created_at.asc())
        )
        source_interactions = list(result.scalars().all())

        # Create the forked conversation
        fork_title = title or f"Fork of {original.title}"
        fork = Conversation(
            user_id=user_id,
            title=fork_title,
            parent_id=conversation_id,
            forked_at_interaction_id=at_interaction_id,
        )
        self.db.add(fork)
        await self.db.flush()

        # Copy interactions to the new conversation
        for interaction in source_interactions:
            new_interaction = Interaction(
                user_id=user_id,
                conversation_id=str(fork.id),
                user_message=interaction.user_message,
                assistant_response=interaction.assistant_response,
                rules_applied=interaction.rules_applied,
                was_corrected=interaction.was_corrected,
                correction_text=interaction.correction_text,
                extracted_rule_id=interaction.extracted_rule_id,
            )
            self.db.add(new_interaction)

        return fork

    async def get_conversation_tree(
        self,
        conversation_id: UUID
    ) -> Dict[str, Any]:
        """
        Get a conversation and all its forks as a tree structure.

        Args:
            conversation_id: UUID of the root conversation

        Returns:
            Dict with conversation data and nested forks
        """
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return {}

        # Find the root — walk up the parent chain
        root = conversation
        while root.parent_id:
            parent = await self.get_conversation(root.parent_id)
            if parent:
                root = parent
            else:
                break

        # Build tree from root
        return await self._build_tree(root)

    async def rename_conversation(
        self,
        conversation_id: UUID,
        title: str
    ) -> Optional[Conversation]:
        """Rename a conversation."""
        conversation = await self.get_conversation(conversation_id)
        if conversation:
            conversation.title = title
            conversation.updated_at = datetime.utcnow()
        return conversation

    async def toggle_pin(self, conversation_id: UUID) -> Optional[Conversation]:
        """Toggle a conversation's pinned status."""
        conversation = await self.get_conversation(conversation_id)
        if conversation:
            conversation.is_pinned = not conversation.is_pinned
            conversation.updated_at = datetime.utcnow()
        return conversation

    async def archive_conversation(self, conversation_id: UUID) -> Optional[Conversation]:
        """Archive a conversation."""
        conversation = await self.get_conversation(conversation_id)
        if conversation:
            conversation.is_archived = True
            conversation.updated_at = datetime.utcnow()
        return conversation

    async def delete_conversation(
        self,
        conversation_id: UUID,
        cascade_forks: bool = False
    ) -> bool:
        """
        Delete a conversation.

        Args:
            conversation_id: UUID of the conversation
            cascade_forks: If True, also delete all forked conversations

        Returns:
            True if deleted
        """
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return False

        if cascade_forks:
            # Delete all forks recursively
            await self._delete_forks(conversation_id)

        # Delete associated interactions
        result = await self.db.execute(
            select(Interaction)
            .where(Interaction.conversation_id == str(conversation_id))
        )
        for interaction in result.scalars().all():
            await self.db.delete(interaction)

        await self.db.delete(conversation)
        return True

    # --- Internal helpers ---

    async def _get_message_count(self, conversation_id: UUID) -> int:
        """Get the number of messages in a conversation."""
        result = await self.db.execute(
            select(func.count(Interaction.id))
            .where(Interaction.conversation_id == str(conversation_id))
        )
        return result.scalar() or 0

    async def _build_tree(self, conversation: Conversation) -> Dict[str, Any]:
        """Recursively build a conversation tree."""
        msg_count = await self._get_message_count(conversation.id)
        node = conversation.to_dict()
        node["message_count"] = msg_count

        # Find forks
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.parent_id == conversation.id)
            .order_by(Conversation.created_at.asc())
        )
        forks = list(result.scalars().all())

        node["forks"] = []
        for fork in forks:
            fork_tree = await self._build_tree(fork)
            node["forks"].append(fork_tree)

        return node

    async def _delete_forks(self, conversation_id: UUID):
        """Recursively delete all forks of a conversation."""
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.parent_id == conversation_id)
        )
        forks = list(result.scalars().all())

        for fork in forks:
            await self._delete_forks(fork.id)

            # Delete interactions
            interactions = await self.db.execute(
                select(Interaction)
                .where(Interaction.conversation_id == str(fork.id))
            )
            for interaction in interactions.scalars().all():
                await self.db.delete(interaction)

            await self.db.delete(fork)
