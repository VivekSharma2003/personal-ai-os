"""
Personal AI OS - Main FastAPI Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import chat, feedback, rules
from app.db.session import init_db, close_db
from app.db.redis import init_redis, close_redis
from app.db.vector import init_vector_db
from app.jobs import start_scheduler, stop_scheduler


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    await init_db()
    await init_redis()
    await init_vector_db()
    await start_scheduler()
    
    yield
    
    # Shutdown
    await stop_scheduler()
    await close_redis()
    await close_db()


app = FastAPI(
    title="Personal AI OS",
    description="An AI assistant that learns user preferences from corrections",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(feedback.router, prefix="/api", tags=["feedback"])
app.include_router(rules.router, prefix="/api", tags=["rules"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
