"""
Personal AI OS - Main FastAPI Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import chat, feedback, rules, analytics, search, suggestions, summarize, export
from app.api.routes import conflicts, versions, stream, webhooks, conversations, rule_import, health
from app.db.session import init_db, close_db
from app.db.redis import init_redis, close_redis
from app.db.vector import init_vector_db
from app.jobs import start_scheduler, stop_scheduler
from app.core.events import get_event_bus


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    await init_db()
    await init_redis()
    await init_vector_db()
    await start_scheduler()

    # Initialize EventBus and wire webhook delivery listener
    event_bus = get_event_bus()
    _register_event_listeners(event_bus)

    # Set startup time for health endpoint
    from app.api.routes.health import set_startup_time
    set_startup_time()

    yield

    # Shutdown
    event_bus.clear()
    await stop_scheduler()
    await close_redis()
    await close_db()


def _register_event_listeners(event_bus):
    """Register internal event listeners on the EventBus."""

    async def webhook_delivery_handler(event_type: str, payload: dict):
        """Deliver events to registered webhooks."""
        # Avoid internal/meta events
        if event_type.startswith("webhook."):
            return

        user_id = payload.get("user_id")
        if not user_id:
            return

        try:
            from app.db.session import async_session_maker
            from app.services.webhook_service import WebhookService
            from uuid import UUID

            async with async_session_maker() as db:
                webhook_service = WebhookService(db)
                await webhook_service.deliver_event(
                    event_type=event_type,
                    payload={k: v for k, v in payload.items() if not k.startswith("_")},
                    user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
                )
                await db.commit()
        except Exception as e:
            print(f"[EventBus] Webhook delivery error for '{event_type}': {e}")

    # Subscribe to all events for webhook delivery
    event_bus.subscribe("*", webhook_delivery_handler)


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

# --- Existing Routers ---
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(feedback.router, prefix="/api", tags=["feedback"])
app.include_router(rules.router, prefix="/api", tags=["rules"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(suggestions.router, prefix="/api", tags=["suggestions"])
app.include_router(summarize.router, prefix="/api", tags=["summarize"])
app.include_router(export.router, prefix="/api", tags=["export"])

# --- New Feature Routers ---
app.include_router(conflicts.router, prefix="/api", tags=["conflicts"])
app.include_router(versions.router, prefix="/api", tags=["versions"])
app.include_router(stream.router, prefix="/api", tags=["streaming"])
app.include_router(webhooks.router, prefix="/api", tags=["webhooks"])
app.include_router(conversations.router, prefix="/api", tags=["conversations"])
app.include_router(rule_import.router, prefix="/api", tags=["import"])
app.include_router(health.router, prefix="/api", tags=["health"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
