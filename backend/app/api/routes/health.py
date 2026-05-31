"""
Personal AI OS - Health & Diagnostics API Routes

Comprehensive health monitoring for PostgreSQL, Redis, Vector DB,
LLM provider, scheduler, and system metrics.
"""
import os
import sys
import time
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.config import get_settings
from app.db.redis import get_redis
from app.db.vector import vector_index, embedding_map

settings = get_settings()
router = APIRouter()

# Track startup time for uptime calculation
_startup_time = time.time()


def set_startup_time():
    """Called during app lifespan to set accurate startup time."""
    global _startup_time
    _startup_time = time.time()


@router.get("/health")
async def comprehensive_health(
    db: AsyncSession = Depends(get_db)
):
    """
    Comprehensive health check with component-level diagnostics.

    Returns status for each subsystem:
    - PostgreSQL (connection pool, response time)
    - Redis (ping latency, memory usage, key count)
    - Vector DB (index size, entries)
    - LLM Provider (configured provider/model)
    - Scheduler (running jobs)
    - System (uptime, Python version, memory)
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "components": {},
    }

    errors = []

    # --- PostgreSQL ---
    try:
        start = time.time()
        result = await db.execute(text("SELECT 1"))
        pg_latency = round((time.time() - start) * 1000, 2)

        health["components"]["postgresql"] = {
            "status": "healthy",
            "latency_ms": pg_latency,
            "database_url": _mask_url(settings.database_url),
        }
    except Exception as e:
        errors.append("postgresql")
        health["components"]["postgresql"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # --- Redis ---
    try:
        redis = get_redis()
        start = time.time()
        await redis.ping()  # pyrefly: ignore
        redis_latency = round((time.time() - start) * 1000, 2)

        # Get memory info
        info = await redis.info("memory")  # pyrefly: ignore
        memory_used = info.get("used_memory_human", "unknown")

        # Get key count
        db_size = await redis.dbsize()  # pyrefly: ignore

        health["components"]["redis"] = {
            "status": "healthy",
            "latency_ms": redis_latency,
            "memory_used": memory_used,
            "total_keys": db_size,
            "url": _mask_url(settings.redis_url),
        }
    except Exception as e:
        errors.append("redis")
        health["components"]["redis"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # --- Vector DB (FAISS) ---
    try:
        if vector_index is not None:
            index_size = vector_index.ntotal
            num_entries = len(embedding_map)

            health["components"]["vector_db"] = {
                "status": "healthy",
                "index_size": index_size,
                "entries": num_entries,
                "dimension": vector_index.d if hasattr(vector_index, 'd') else 0,
                "path": settings.vector_db_path,
            }
        else:
            health["components"]["vector_db"] = {
                "status": "not_initialized",
                "message": "Vector index is None (may not have been initialized yet)",
            }
    except Exception as e:
        errors.append("vector_db")
        health["components"]["vector_db"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # --- LLM Provider ---
    try:
        provider_info = {
            "status": "configured",
            "provider": settings.llm_provider,
        }

        if settings.llm_provider == "openai":
            provider_info["model"] = settings.openai_model
            provider_info["has_api_key"] = bool(settings.openai_api_key)
        elif settings.llm_provider == "gemini":
            provider_info["model"] = settings.gemini_model
            provider_info["has_api_key"] = bool(settings.google_api_key)
        elif settings.llm_provider == "anthropic":
            provider_info["model"] = settings.anthropic_model
            provider_info["has_api_key"] = bool(settings.anthropic_api_key)

        provider_info["temperature"] = settings.llm_temperature
        provider_info["max_tokens"] = settings.llm_max_tokens

        health["components"]["llm_provider"] = provider_info
    except Exception as e:
        health["components"]["llm_provider"] = {
            "status": "error",
            "error": str(e),
        }

    # --- Scheduler ---
    try:
        from app.jobs.scheduler import get_scheduler
        scheduler = get_scheduler()

        if scheduler and scheduler.running:
            jobs = []
            for job in scheduler.get_jobs():
                next_run = job.next_run_time
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run": next_run.isoformat() if next_run else "paused",
                })

            health["components"]["scheduler"] = {
                "status": "running",
                "jobs": jobs,
                "total_jobs": len(jobs),
            }
        else:
            health["components"]["scheduler"] = {
                "status": "stopped",
            }
    except Exception as e:
        health["components"]["scheduler"] = {
            "status": "error",
            "error": str(e),
        }

    # --- System ---
    try:
        uptime_seconds = int(time.time() - _startup_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        system_info = {
            "status": "healthy",
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
            "uptime": f"{hours}h {minutes}m {seconds}s",
            "uptime_seconds": uptime_seconds,
            "pid": os.getpid(),
        }

        # Try to get memory usage via psutil
        try:
            import psutil
            process = psutil.Process()
            memory = process.memory_info()
            system_info["memory_rss_mb"] = round(memory.rss / 1024 / 1024, 1)
            system_info["memory_vms_mb"] = round(memory.vms / 1024 / 1024, 1)
            system_info["cpu_percent"] = process.cpu_percent(interval=0.1)
        except ImportError:
            system_info["memory_note"] = "Install psutil for detailed memory metrics"

        health["components"]["system"] = system_info
    except Exception as e:
        health["components"]["system"] = {
            "status": "error",
            "error": str(e),
        }

    # --- Overall status ---
    if errors:
        health["status"] = "degraded"
        health["unhealthy_components"] = errors

    return health


@router.get("/health/ready")
async def readiness_probe(
    db: AsyncSession = Depends(get_db)
):
    """
    Lightweight readiness probe (k8s-compatible).

    Returns 200 if the app can serve requests (DB + Redis are reachable).
    Returns 503 if any critical dependency is down.
    """
    try:
        # Check DB
        await db.execute(text("SELECT 1"))

        # Check Redis
        redis = get_redis()
        await redis.ping()  # pyrefly: ignore

        return {"ready": True}

    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"ready": False, "error": str(e)}
        )


@router.get("/health/live")
async def liveness_probe():
    """
    Lightweight liveness probe (k8s-compatible).

    Always returns 200 if the process is alive.
    """
    return {"alive": True, "timestamp": datetime.utcnow().isoformat()}


def _mask_url(url: str) -> str:
    """Mask sensitive parts of connection URLs."""
    if "@" in url:
        # Mask password in URLs like postgresql://user:pass@host:port/db
        parts = url.split("@")
        prefix = parts[0].rsplit(":", 1)[0]  # Remove password
        return f"{prefix}:***@{parts[1]}"
    return url
