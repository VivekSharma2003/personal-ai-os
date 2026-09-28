"""
Personal AI OS - Idempotency Routes

POST /api/idempotency/check   — query if a key has already been processed
POST /api/idempotency/store   — manually store a result for a key
DELETE /api/idempotency/{key} — expire a key early
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional

from app.services.idempotency import IdempotencyService

router = APIRouter(prefix="/api/idempotency", tags=["Idempotency"])


class IdempotencyCheckRequest(BaseModel):
    key: str


class IdempotencyStoreRequest(BaseModel):
    key: str
    response: Dict[str, Any]
    ttl: int = 86_400


@router.post("/check")
async def check_idempotency(req: IdempotencyCheckRequest):
    """
    Check whether a request with the given Idempotency-Key was already processed.
    Returns the cached response if found.
    """
    service = IdempotencyService()
    cached = await service.get(req.key)
    return {"hit": cached is not None, "response": cached}


@router.post("/store")
async def store_idempotency(req: IdempotencyStoreRequest):
    """
    Manually register a response for an Idempotency-Key.
    """
    service = IdempotencyService()
    await service.store(req.key, req.response, req.ttl)
    return {"status": "stored", "key": req.key}


@router.delete("/{key}")
async def delete_idempotency(key: str):
    """
    Expire an Idempotency-Key before its natural TTL (e.g. on confirmed failure).
    """
    service = IdempotencyService()
    deleted = await service.delete(key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"status": "deleted", "key": key}
