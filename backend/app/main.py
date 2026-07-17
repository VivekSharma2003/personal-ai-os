"""
Personal AI OS - Main FastAPI Application
"""
from contextlib import asynccontextmanager
# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import chat, feedback, rules, analytics, search, suggestions, summarize, export
from app.api.routes import conflicts, versions, stream, webhooks, conversations, rule_import, health
from app.api.routes import rate_limit, schedules, audit, tags
from app.api.routes import effectiveness, api_keys, dependencies, jobs, retention
from app.api.routes import costs, experiments, profiles, lifecycle, sessions
from app.api.routes import clusters, shared_library, replay, notifications, simulation
from app.db.session import init_db, close_db
from app.db.redis import init_redis, close_redis
from app.db.vector import init_vector_db
from app.jobs import start_scheduler, stop_scheduler
from app.core.events import get_event_bus
from app.core.logging import setup_logging, get_logger

# Import new models so Base.metadata.create_all picks them up
import app.models.rule_schedule  # noqa: F401
import app.models.rule_tag  # noqa: F401
import app.models.api_key  # noqa: F401
import app.models.rule_dependency  # noqa: F401
import app.models.retention  # noqa: F401
import app.models.llm_usage  # noqa: F401
import app.models.experiment  # noqa: F401
import app.models.prompt_profile  # noqa: F401
import app.models.session  # noqa: F401
import app.models.rule_cluster  # noqa: F401
import app.models.shared_rule  # noqa: F401
import app.models.replay  # noqa: F401
import app.models.notification  # noqa: F401


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Configure structured logging
    setup_logging()
    logger = get_logger("app.lifecycle")
    logger.info("Starting Personal AI OS...")

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

    logger.info("Personal AI OS started successfully")
    yield

    # Shutdown
    logger.info("Shutting down Personal AI OS...")
    event_bus.clear()
    await stop_scheduler()
    await close_redis()
    await close_db()
    logger.info("Shutdown complete")


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
            logger = get_logger("app.events.webhook")
            logger.error(
                f"Webhook delivery error for '{event_type}': {e}",
                extra={"extra_data": {"event_type": event_type}},
            )

    # Subscribe to all events for webhook delivery
    event_bus.subscribe("*", webhook_delivery_handler)


app = FastAPI(
    title="Personal AI OS",
    description="An AI assistant that learns user preferences from corrections",
    version="1.0.0",
    lifespan=lifespan
)

# --- Middleware Stack ---
# NOTE: Middleware is applied in reverse order (last added = first executed)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware (Redis-backed sliding window)
from app.core.rate_limiter import RateLimitMiddleware  # noqa: E402
app.add_middleware(RateLimitMiddleware)

# API key authentication middleware
from app.core.api_key_auth import APIKeyMiddleware  # noqa: E402
app.add_middleware(APIKeyMiddleware)

# Request tracing middleware (X-Request-ID correlation)
from app.core.logging import RequestTracingMiddleware  # noqa: E402
app.add_middleware(RequestTracingMiddleware)

# --- Existing Routers ---
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(feedback.router, prefix="/api", tags=["feedback"])
app.include_router(lifecycle.router, prefix="/api", tags=["lifecycle"])
app.include_router(rules.router, prefix="/api", tags=["rules"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(suggestions.router, prefix="/api", tags=["suggestions"])
app.include_router(summarize.router, prefix="/api", tags=["summarize"])
app.include_router(export.router, prefix="/api", tags=["export"])

# --- Feature Routers (Batch 1) ---
app.include_router(conflicts.router, prefix="/api", tags=["conflicts"])
app.include_router(versions.router, prefix="/api", tags=["versions"])
app.include_router(stream.router, prefix="/api", tags=["streaming"])
app.include_router(webhooks.router, prefix="/api", tags=["webhooks"])
app.include_router(conversations.router, prefix="/api", tags=["conversations"])
app.include_router(rule_import.router, prefix="/api", tags=["import"])
app.include_router(health.router, prefix="/api", tags=["health"])

# --- Feature Routers (Batch 2) ---
app.include_router(rate_limit.router, prefix="/api", tags=["rate-limiting"])
app.include_router(schedules.router, prefix="/api", tags=["schedules"])
app.include_router(audit.router, prefix="/api", tags=["audit"])
app.include_router(tags.router, prefix="/api", tags=["tags"])

# --- Feature Routers (Batch 3) ---
app.include_router(effectiveness.router, prefix="/api", tags=["effectiveness"])
app.include_router(api_keys.router, prefix="/api", tags=["api-keys"])
app.include_router(dependencies.router, prefix="/api", tags=["dependencies"])
app.include_router(jobs.router, prefix="/api", tags=["jobs"])
app.include_router(retention.router, prefix="/api", tags=["retention"])

# --- Feature Routers (Batch 4) ---
app.include_router(costs.router, prefix="/api", tags=["costs"])
app.include_router(experiments.router, prefix="/api", tags=["experiments"])
app.include_router(profiles.router, prefix="/api", tags=["profiles"])
app.include_router(sessions.router, prefix="/api", tags=["sessions"])

# --- Feature Routers (Batch 5) ---
app.include_router(clusters.router, prefix="/api", tags=["clusters"])
app.include_router(shared_library.router, prefix="/api", tags=["shared-library"])
app.include_router(replay.router, prefix="/api", tags=["replay"])
app.include_router(notifications.router, prefix="/api", tags=["notifications"])
app.include_router(simulation.router, prefix="/api", tags=["simulation"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
