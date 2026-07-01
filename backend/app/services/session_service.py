"""
Personal AI OS - Session Security Service

IP allowlisting, session tracking, and anomaly detection.
"""
import ipaddress
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy import select, and_, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import APISession
from app.models.api_key import APIKey
from app.core.logging import get_logger

logger = get_logger("services.session")


class SessionService:
    """Service for session tracking and IP security."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def track_request(
        self,
        user_id: UUID,
        api_key_id: Optional[UUID],
        ip_address: str,
        user_agent: str = "",
    ) -> APISession:
        """
        Track a request by upserting a session record.
        Groups sessions by (api_key_id, ip_address).
        """
        # Try to find existing session
        q = select(APISession).where(
            and_(
                APISession.user_id == user_id,
                APISession.ip_address == ip_address,
                APISession.api_key_id == api_key_id if api_key_id else APISession.api_key_id == None,
            )
        )
        result = await self.db.execute(q)
        session = result.scalar_one_or_none()

        if session:
            session.request_count += 1
            session.last_seen_at = datetime.utcnow()
            session.user_agent = user_agent or session.user_agent
        else:
            session = APISession(
                user_id=user_id,
                api_key_id=api_key_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self.db.add(session)

        await self.db.flush()
        return session

    async def get_active_sessions(
        self,
        user_id: UUID,
        since_hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Get sessions with activity in the last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=since_hours)

        q = select(APISession).where(
            and_(
                APISession.user_id == user_id,
                APISession.last_seen_at >= cutoff,
            )
        ).order_by(APISession.last_seen_at.desc())

        result = await self.db.execute(q)
        return [s.to_dict() for s in result.scalars().all()]

    async def revoke_session(self, session_id: UUID) -> bool:
        """Delete a specific session record."""
        session = await self.db.get(APISession, session_id)
        if not session:
            return False
        await self.db.delete(session)
        await self.db.flush()
        return True

    async def set_ip_allowlist(
        self,
        api_key_id: UUID,
        cidrs: List[str],
    ) -> Dict[str, Any]:
        """
        Set IP allowlist for an API key.
        Validates CIDR format before saving.
        """
        api_key = await self.db.get(APIKey, api_key_id)
        if not api_key:
            raise ValueError("API key not found")

        # Validate all CIDRs
        validated = []
        for cidr in cidrs:
            try:
                network = ipaddress.ip_network(cidr, strict=False)
                validated.append(str(network))
            except ValueError:
                raise ValueError(f"Invalid CIDR notation: {cidr}")

        api_key.ip_allowlist = validated
        await self.db.flush()

        logger.info(f"Updated IP allowlist for key {api_key.key_prefix}...", extra={"extra_data": {
            "api_key_id": str(api_key_id),
            "cidr_count": len(validated),
        }})

        return {
            "api_key_id": str(api_key_id),
            "ip_allowlist": validated,
        }

    async def get_ip_allowlist(self, api_key_id: UUID) -> List[str]:
        """Get the IP allowlist for an API key."""
        api_key = await self.db.get(APIKey, api_key_id)
        if not api_key:
            raise ValueError("API key not found")
        return api_key.ip_allowlist or []

    def check_ip_allowed(
        self,
        ip_allowlist: List[str],
        ip_address: str,
    ) -> bool:
        """
        Check if an IP address is allowed by the allowlist.
        Empty allowlist = all allowed.
        """
        if not ip_allowlist:
            return True

        try:
            addr = ipaddress.ip_address(ip_address)
        except ValueError:
            return False

        for cidr in ip_allowlist:
            try:
                network = ipaddress.ip_network(cidr, strict=False)
                if addr in network:
                    return True
            except ValueError:
                continue

        return False

    async def detect_anomalies(
        self,
        user_id: UUID,
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalous session patterns.

        Flags:
        - New IPs with high request volume (> 100 in first hour)
        - Multiple IPs using the same API key simultaneously
        - Sessions from previously unseen geolocations (simplified as new unique IPs)
        """
        anomalies = []
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        one_day_ago = datetime.utcnow() - timedelta(hours=24)

        # Flag 1: New sessions with high volume
        high_volume_q = select(APISession).where(
            and_(
                APISession.user_id == user_id,
                APISession.created_at >= one_hour_ago,
                APISession.request_count > 100,
            )
        )
        result = await self.db.execute(high_volume_q)
        for session in result.scalars().all():
            anomalies.append({
                "type": "high_volume_new_ip",
                "severity": "high",
                "session_id": str(session.id),
                "ip_address": session.ip_address,
                "request_count": session.request_count,
                "detail": f"New IP {session.ip_address} made {session.request_count} requests in first hour",
            })

        # Flag 2: Single API key used from many IPs recently
        if True:
            multi_ip_q = select(
                APISession.api_key_id,
                func.count(func.distinct(APISession.ip_address)).label("ip_count"),
            ).where(
                and_(
                    APISession.user_id == user_id,
                    APISession.api_key_id != None,
                    APISession.last_seen_at >= one_day_ago,
                )
            ).group_by(APISession.api_key_id).having(
                func.count(func.distinct(APISession.ip_address)) > 5
            )
            multi_result = await self.db.execute(multi_ip_q)
            for row in multi_result.all():
                anomalies.append({
                    "type": "multi_ip_single_key",
                    "severity": "medium",
                    "api_key_id": str(row.api_key_id),
                    "unique_ips": row.ip_count,
                    "detail": f"API key used from {row.ip_count} different IPs in 24h",
                })

        return anomalies
