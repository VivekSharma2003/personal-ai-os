import asyncio
import os
import shutil
# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
import pytest_asyncio
from typing import AsyncGenerator, Generator
# pyrefly: ignore [missing-import]
from httpx import AsyncClient, ASGITransport
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import get_settings
from app.db.session import Base
from app.main import app
from app.dependencies import get_db

settings = get_settings()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    """Create all tables in the test database once before the test session."""
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

@pytest_asyncio.fixture(autouse=True)
async def setup_redis():
    """Initialize and clean up Redis connection for each test function."""
    from app.db.redis import init_redis, close_redis
    await init_redis()
    yield
    await close_redis()

@pytest_asyncio.fixture(autouse=True)
async def setup_vector_db():
    """Initialize and clean up temporary vector database for each test function."""
    test_db_path = "/Users/VivekSharma/.gemini/antigravity-ide/scratch/test_vector_store"
    original_path = settings.vector_db_path
    settings.vector_db_path = test_db_path
    
    # Clean up previous test files
    if os.path.exists(test_db_path):
        shutil.rmtree(test_db_path)
    os.makedirs(test_db_path, exist_ok=True)
    
    from app.db.vector import init_vector_db
    import app.db.vector as vector_module
    
    await init_vector_db()
    
    yield
    
    # Clear index and maps
    vector_module.vector_index = None
    vector_module.embedding_map = {}
    vector_module.index_to_id = {}
    
    # Clean up test files
    if os.path.exists(test_db_path):
        try:
            shutil.rmtree(test_db_path)
        except Exception:
            pass
            
    settings.vector_db_path = original_path

@pytest_asyncio.fixture
async def test_engine():
    """Create a function-scoped engine for the test case."""
    engine = create_async_engine(settings.database_url, echo=False)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session that rolls back after each test."""
    async with test_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(bind=connection, expire_on_commit=False)
        
        yield session
        
        await session.close()
        await transaction.rollback()

@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an AsyncClient configured to use the transactional db_session."""
    async def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
        
    app.dependency_overrides.clear()
