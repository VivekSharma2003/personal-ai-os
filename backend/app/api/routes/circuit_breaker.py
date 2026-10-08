"""
Personal AI OS - Circuit Breaker Routes

GET    /api/circuit-breaker/{service}/{resource}         — status
POST   /api/circuit-breaker/{service}/{resource}/success — record success
POST   /api/circuit-breaker/{service}/{resource}/failure — record failure
POST   /api/circuit-breaker/{service}/{resource}/open    — force open
POST   /api/circuit-breaker/{service}/{resource}/close   — force close
"""
from fastapi import APIRouter

from app.services.circuit_breaker import CircuitBreaker

router = APIRouter(prefix="/api/circuit-breaker", tags=["Circuit Breaker"])


@router.get("/{service}/{resource}")
async def get_status(service: str, resource: str):
    """Return the current circuit breaker state for a service/resource pair."""
    cb = CircuitBreaker(service, resource)
    return await cb.get_status()


@router.post("/{service}/{resource}/success")
async def record_success(service: str, resource: str):
    """Inform the circuit breaker that a call succeeded."""
    cb = CircuitBreaker(service, resource)
    await cb.record_success()
    return await cb.get_status()


@router.post("/{service}/{resource}/failure")
async def record_failure(service: str, resource: str):
    """Inform the circuit breaker that a call failed."""
    cb = CircuitBreaker(service, resource)
    await cb.record_failure()
    return await cb.get_status()


@router.post("/{service}/{resource}/open")
async def force_open(service: str, resource: str):
    """Manually open the circuit (e.g. during planned maintenance)."""
    cb = CircuitBreaker(service, resource)
    await cb.force_open()
    return await cb.get_status()


@router.post("/{service}/{resource}/close")
async def force_close(service: str, resource: str):
    """Manually reset the circuit to CLOSED."""
    cb = CircuitBreaker(service, resource)
    await cb.force_close()
    return await cb.get_status()
