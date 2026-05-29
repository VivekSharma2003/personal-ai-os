import pytest
from uuid import uuid4
from sqlalchemy import select
from app.models.user import User
from app.models.conversation import Conversation
from app.models.interaction import Interaction
from app.services.conversation_service import ConversationService

@pytest.mark.asyncio
async def test_conversation_crud_and_pin(db_session):
    user = User(external_id="conv_user")
    db_session.add(user)
    await db_session.flush()

    service = ConversationService(db_session)

    # 1. Create conversation
    conv = await service.create_conversation(user_id=user.id, title="Test Conv", description="Test desc")
    await db_session.flush()

    assert conv.id is not None
    assert conv.title == "Test Conv"

    # 2. Rename conversation
    renamed = await service.rename_conversation(conv.id, "Renamed Conv")
    await db_session.flush()
    assert renamed.title == "Renamed Conv"

    # 3. Pin conversation
    pinned = await service.toggle_pin(conv.id)
    await db_session.flush()
    assert pinned.is_pinned is True

    # 4. List conversations
    result = await service.list_conversations(user.id)
    assert result["total"] == 1
    assert result["conversations"][0]["title"] == "Renamed Conv"

    # 5. Archive conversation
    archived = await service.archive_conversation(conv.id)
    await db_session.flush()
    assert archived.is_archived is True

@pytest.mark.asyncio
async def test_conversation_forking(db_session):
    user = User(external_id="fork_user")
    db_session.add(user)
    await db_session.flush()

    service = ConversationService(db_session)

    # 1. Create a root conversation
    root_conv = await service.create_conversation(user_id=user.id, title="Root Conversation")
    await db_session.flush()

    # 2. Add some interactions to it
    interaction1 = Interaction(
        user_id=user.id,
        conversation_id=str(root_conv.id),
        user_message="Hello",
        assistant_response="Hi there!"
    )
    db_session.add(interaction1)
    await db_session.flush()

    # Wait a tiny bit or just create the second one with a guaranteed later timestamp
    interaction2 = Interaction(
        user_id=user.id,
        conversation_id=str(root_conv.id),
        user_message="How are you?",
        assistant_response="I'm doing well!"
    )
    db_session.add(interaction2)
    await db_session.flush()

    # 3. Fork at interaction1 (the first message)
    forked_conv = await service.fork_conversation(
        conversation_id=root_conv.id,
        at_interaction_id=interaction1.id,
        user_id=user.id,
        title="Forked timeline"
    )
    await db_session.flush()

    assert forked_conv is not None
    assert forked_conv.parent_id == root_conv.id
    assert forked_conv.title == "Forked timeline"

    # 4. Check interactions in the forked conversation (should only contain copy of interaction1)
    res = await db_session.execute(
        select(Interaction).where(Interaction.conversation_id == str(forked_conv.id))
    )
    forked_interactions = res.scalars().all()
    assert len(forked_interactions) == 1
    assert forked_interactions[0].user_message == "Hello"

    # 5. Check tree structure
    tree = await service.get_conversation_tree(root_conv.id)
    assert tree["id"] == str(root_conv.id)
    assert len(tree["forks"]) == 1
    assert tree["forks"][0]["id"] == str(forked_conv.id)

    # 6. Delete root with cascade
    deleted = await service.delete_conversation(root_conv.id, cascade_forks=True)
    await db_session.flush()
    assert deleted is True

    # Both should be deleted
    assert await db_session.get(Conversation, root_conv.id) is None
    assert await db_session.get(Conversation, forked_conv.id) is None
