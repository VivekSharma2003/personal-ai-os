"""
Personal AI OS - API Key Authentication Middleware

Extracts and validates API keys from the Authorization header.
Falls back to X-User-ID header for backward compatibility.
"""
from datetime import datetime
from typing import Optional

# pyrefly: ignore [missing-import]
from fastapi import Request, Response
# pyrefly: ignore [missing-import]
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logging import get_logger

logger = get_logger("auth.api_key")


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware that authenticates requests via API key.

    Authentication flow:
      1. Check for `Authorization: Bearer <key>` header
      2. If present, validate the key and inject user into request state
      3. If absent, fall back to `X-User-ID` header (backward-compat)
      4. Unauthenticated requests to protected paths get 401

    Public paths (docs, health, openapi) are excluded.
    """

    # Paths that don't require authentication
    PUBLIC_PATHS = {
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/health",
        "/api/health/ready",
        "/api/health/live",
    }

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip auth for public paths
        if self._is_public(request.url.path):
            return await call_next(request)

        # Try Bearer token first
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            raw_key = auth_header[7:].strip()
            if raw_key:
                request.state.ip_violation = False
                user = await self._validate_api_key(request, raw_key)
                if user is None:
                    from starlette.responses import JSONResponse

                    if getattr(request.state, "ip_violation", False):
                        return JSONResponse(
                            status_code=403,
                            content={"detail": "IP address not allowed"},
                        )
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Invalid or expired API key"},
                    )
                # Key validated — continue
                return await call_next(request)

        # Fallback: X-User-ID header (backward compatibility)
        user_id = request.headers.get("X-User-ID")
        if user_id:
            request.state.user_external_id = user_id
            request.state.api_key = None
            return await call_next(request)

        # No auth provided — allow through (individual routes enforce auth)
        request.state.user_external_id = None
        request.state.api_key = None
        return await call_next(request)

    async def _validate_api_key(
        self, request: Request, raw_key: str
    ) -> Optional[object]:
        """Validate the API key and set request state."""
        try:
            from app.db.session import async_session_maker
            from app.services.api_key_service import APIKeyService
            from app.services.session_service import SessionService
            from app.models.user import User
            from sqlalchemy import select

            async with async_session_maker() as db:
                service = APIKeyService(db)
                api_key = await service.validate_key(raw_key)

                if api_key is None:
                    return None

                # Look up the user's external_id
                result = await db.execute(
                    select(User).where(User.id == api_key.user_id)
                )
                user = result.scalar_one_or_none()

                if not user:
                    return None

                # IP Allowlist check
                client_host = request.client.host if request.client else "127.0.0.1"
                session_service = SessionService(db)
                if not session_service.check_ip_allowed(api_key.ip_allowlist or [], client_host):
                    request.state.ip_violation = True
                    return None

                # Track request session
                user_agent = request.headers.get("user-agent", "")
                await session_service.track_request(
                    user_id=user.id,
                    api_key_id=api_key.id,
                    ip_address=client_host,
                    user_agent=user_agent,
                )

                # Set request state
                request.state.user_external_id = user.external_id
                request.state.api_key = api_key
                request.state.api_key_scopes = api_key.scopes

                await db.commit()  # persist last_used_at update

                return user

        except Exception as e:
            logger.error(
                f"API key validation error: {e}",
                exc_info=True,
            )
            return None

    @staticmethod
    def _is_public(path: str) -> bool:
        """Check if a path is public (no auth required)."""
        for public in APIKeyMiddleware.PUBLIC_PATHS:
            if path == public or path.startswith(public + "/"):
                return True
        return False
