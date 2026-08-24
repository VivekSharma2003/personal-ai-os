"""
Personal AI OS - Test Memory Consolidation
"""
import pytest
from unittest.mock import patch
from sqlalchemy import select

from app.models.interaction import Interaction
from app.models.episodic_memory import EpisodicMemory
from app.services.memory_consolidation_service import MemoryConsolidationService
from app.services.rule_engine import RuleEngineService


@pytest.fixture
def mock_generate_embedding():
    with patch("app.services.memory_consolidation_service.generate_embedding") as mock_gen:
        mock_gen.return_value = [0.1] * 1536
        yield mock_gen


@pytest.fixture
def mock_extract_json():
    with patch("app.services.memory_consolidation_service.extract_json_response") as mock_ext:
        mock_ext.return_value = {
            "summary": "This is a summary of the conversation.",
            "key_takeaways": ["Takeaway 1", "Takeaway 2"]
        }
        yield mock_ext


@pytest.fixture
def mock_vector_db():
    with patch("app.services.memory_consolidation_service.add_embedding") as mock_add, \
         patch("app.services.memory_consolidation_service.search_similar") as mock_search:
        
        mock_add.return_value = 1
        # Default mock search returns nothing
        mock_search.return_value = []
        
        yield {"add": mock_add, "search": mock_search}


@pytest.mark.asyncio
async def test_consolidate_thread(db_session, mock_generate_embedding, mock_extract_json, mock_vector_db):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("memory_test_user")
    await db_session.flush()

    # Create interactions
    i1 = Interaction(
        user_id=user.id,
        conversation_id="thread_abc",
        user_message="Hello",
        assistant_response="Hi there"
    )
    i2 = Interaction(
        user_id=user.id,
        conversation_id="thread_abc",
        user_message="What is the weather?",
        assistant_response="It is sunny."
    )
    db_session.add_all([i1, i2])
    await db_session.commit()

    service = MemoryConsolidationService(db_session)
    
    # Consolidate thread
    memory = await service.consolidate_thread(user.id, "thread_abc")
    
    assert memory is not None
    assert memory.summary == "This is a summary of the conversation."
    assert len(memory.key_takeaways) == 2
    assert memory.interaction_count == 2
    
    # Check that vector DB add was called
    assert mock_vector_db["add"].called
    
    
@pytest.mark.asyncio
async def test_memory_consolidation_api(client, db_session, mock_generate_embedding, mock_extract_json, mock_vector_db):
    rule_engine = RuleEngineService(db_session)
    user = await rule_engine.get_or_create_user("api_memory_user")
    await db_session.flush()
    
    i1 = Interaction(
        user_id=user.id,
        conversation_id="thread_xyz",
        user_message="Hello api",
        assistant_response="Hi api"
    )
    db_session.add(i1)
    await db_session.commit()

    # POST /api/memory/consolidate
    response = await client.post(
        "/api/memory/consolidate",
        json={"thread_id": "thread_xyz"},
        headers={"X-User-ID": "api_memory_user"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["memories_created"] == 1
    
    # Check search API with mock search result
    memory = await db_session.execute(
        select(EpisodicMemory).where(EpisodicMemory.user_id == user.id)
    )
    memory = memory.scalars().first()
    
    mock_vector_db["search"].return_value = [(memory.embedding_id, 0.9)]
    
    response = await client.get(
        "/api/memory/search?q=hello",
        headers={"X-User-ID": "api_memory_user"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["summary"] == "This is a summary of the conversation."
