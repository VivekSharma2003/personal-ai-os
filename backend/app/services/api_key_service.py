"""
Personal AI OS - API Key Management Service
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey
from app.core.logging import get_logger

logger = get_logger("services.api_key")


class APIKeyService:
    """
    Manages API key lifecycle: creation, validation, rotation, revocation.

    Keys are generated as 48-character random hex strings, SHA-256 hashed
    before storage. The raw key is returned to the user exactly once at
    creation time.
    """

    KEY_LENGTH = 48  # characters of hex = 24 bytes of entropy
    PREFIX_LENGTH = 8

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    async def create_key(
        self,
        user_id: UUID,
        name: str,
        scopes: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None,
    ) -> Tuple[APIKey, str]:
        """
        Create a new API key.

        Returns (APIKey model, raw_key). The raw key is shown once and
        never stored.
        """
        raw_key = f"paios_{secrets.token_hex(self.KEY_LENGTH // 2)}"
        key_hash = self._hash_key(raw_key)
        key_prefix = raw_key[: self.PREFIX_LENGTH]

        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        api_key = APIKey(
            user_id=user_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            scopes=scopes or ["*"],
            expires_at=expires_at,
        )

        self.db.add(api_key)
        await self.db.flush()

        logger.info(
            f"API key created: {key_prefix}***",
            extra={"extra_data": {"user_id": str(user_id), "name": name}},
        )

        return api_key, raw_key

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    async def validate_key(self, raw_key: str) -> Optional[APIKey]:
        """
        Validate a raw API key.

        Returns the APIKey if valid, None if invalid/expired/revoked.
        Also updates `last_used_at` on success.
        """
        key_hash = self._hash_key(raw_key)

        result = await self.db.execute(
            select(APIKey).where(APIKey.key_hash == key_hash)
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            return None

        if not api_key.is_active:
            return None

        if api_key.is_expired:
            return None

        # Update last used
        api_key.last_used_at = datetime.utcnow()
        return api_key

    def check_scope(self, api_key: APIKey, required_scope: str) -> bool:
        """Check if an API key has the required scope."""
        if "*" in api_key.scopes:
            return True
        return required_scope in api_key.scopes

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    async def list_keys(self, user_id: UUID) -> List[APIKey]:
        """List all API keys for a user (active and inactive)."""
        result = await self.db.execute(
            select(APIKey)
            .where(APIKey.user_id == user_id)
            .order_by(APIKey.created_at.desc())
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Revocation
    # ------------------------------------------------------------------

    async def revoke_key(self, key_id: UUID, user_id: UUID) -> Optional[APIKey]:
        """Soft-revoke an API key."""
        result = await self.db.execute(
            select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user_id)
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            return None

        api_key.is_active = False

        logger.info(
            f"API key revoked: {api_key.key_prefix}***",
            extra={"extra_data": {"key_id": str(key_id)}},
        )

        return api_key

    # ------------------------------------------------------------------
    # Rotation
    # ------------------------------------------------------------------

    async def rotate_key(
        self, key_id: UUID, user_id: UUID
    ) -> Optional[Tuple[APIKey, str]]:
        """
        Rotate an API key: revoke the old one and create a new one
        with the same name and scopes.
        """
        result = await self.db.execute(
            select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user_id)
        )
        old_key = result.scalar_one_or_none()

        if not old_key:
            return None

        # Revoke old key
        old_key.is_active = False

        # Compute remaining expiry
        expires_in_days = None
        if old_key.expires_at:
            remaining = (old_key.expires_at - datetime.utcnow()).days
            expires_in_days = max(remaining, 1)

        # Create new key with same metadata
        new_key, raw_key = await self.create_key(
            user_id=user_id,
            name=old_key.name,
            scopes=old_key.scopes,
            expires_in_days=expires_in_days,
        )

        logger.info(
            f"API key rotated: {old_key.key_prefix}*** → {new_key.key_prefix}***",
            extra={"extra_data": {"old_key_id": str(key_id), "new_key_id": str(new_key.id)}},
        )

        return new_key, raw_key

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_key(raw_key: str) -> str:
        """SHA-256 hash a raw API key."""
        return hashlib.sha256(raw_key.encode()).hexdigest()
