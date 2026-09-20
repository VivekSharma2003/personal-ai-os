"""
Personal AI OS - LLM Cache Routes

GET  /api/llm-cache/stats       — entry count
POST /api/llm-cache/lookup      — cache get (try)
POST /api/llm-cache/store       — cache store
POST /api/llm-cache/invalidate  — delete one entry
DELETE /api/llm-cache/flush     — flush all entries
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from app.services.llm_cache import LLMCacheService

router = APIRouter(prefix="/api/llm-cache", tags=["LLM Cache"])


class CacheLookupRequest(BaseModel):
    provider: str
    model: str
    prompt: str


class CacheStoreRequest(BaseModel):
    provider: str
    model: str
    prompt: str
    response: str
    ttl: int = Field(default=3600, ge=1, le=86400)


@router.get("/stats")
async def cache_stats():
    """Return the current number of cached LLM responses."""
    service = LLMCacheService()
    return await service.stats()


@router.post("/lookup")
async def lookup_cache(req: CacheLookupRequest):
    """Try to retrieve a cached LLM response."""
    service = LLMCacheService()
    response = await service.get(req.provider, req.model, req.prompt)
    return {"hit": response is not None, "response": response}


@router.post("/store")
async def store_cache(req: CacheStoreRequest):
    """Store an LLM response in the cache."""
    service = LLMCacheService()
    await service.store(req.provider, req.model, req.prompt, req.response, req.ttl)
    return {"status": "stored"}


@router.post("/invalidate")
async def invalidate_cache(req: CacheLookupRequest):
    """Delete one specific cached entry."""
    service = LLMCacheService()
    deleted = await service.invalidate(req.provider, req.model, req.prompt)
    return {"deleted": deleted}


@router.delete("/flush")
async def flush_cache():
    """Flush all cached LLM responses (e.g. after a model rollout)."""
    service = LLMCacheService()
    count = await service.flush_all()
    return {"flushed": count}
