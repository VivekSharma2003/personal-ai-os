"""
Personal AI OS - Webhook Service

Manages webhook registration, HMAC-signed delivery, and retry logic.
"""
import hashlib
import hmac
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

import httpx

from app.models.webhook import Webhook, WebhookDelivery
from app.config import get_settings


settings = get_settings()


class WebhookService:
    """Service for managing webhooks and delivering events."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # --- CRUD ---

    async def create_webhook(
        self,
        user_id: UUID,
        url: str,
        events: List[str],
        description: Optional[str] = None
    ) -> Webhook:
        """
        Register a new webhook.

        Args:
            user_id: UUID of the user
            url: The webhook URL to POST to
            events: List of event types to subscribe to
            description: Optional human-readable description

        Returns:
            The created Webhook object (with secret included)
        """
        webhook = Webhook(
            user_id=user_id,
            url=url,
            events=events,
            description=description,
        )
        self.db.add(webhook)
        await self.db.flush()
        return webhook

    async def get_webhooks(self, user_id: UUID) -> List[Webhook]:
        """Get all webhooks for a user."""
        result = await self.db.execute(
            select(Webhook)
            .where(Webhook.user_id == user_id)
            .order_by(Webhook.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_webhook(self, webhook_id: UUID) -> Optional[Webhook]:
        """Get a specific webhook."""
        return await self.db.get(Webhook, webhook_id)

    async def update_webhook(
        self,
        webhook_id: UUID,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        active: Optional[bool] = None,
        description: Optional[str] = None
    ) -> Optional[Webhook]:
        """Update a webhook's configuration."""
        webhook = await self.get_webhook(webhook_id)
        if not webhook:
            return None

        if url is not None:
            webhook.url = url
        if events is not None:
            webhook.events = events
        if active is not None:
            webhook.active = active
        if description is not None:
            webhook.description = description
        webhook.updated_at = datetime.utcnow()

        return webhook

    async def delete_webhook(self, webhook_id: UUID) -> bool:
        """Delete a webhook and its delivery history."""
        webhook = await self.get_webhook(webhook_id)
        if not webhook:
            return False
        await self.db.delete(webhook)
        return True

    # --- Delivery ---

    async def deliver_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        user_id: UUID
    ) -> List[WebhookDelivery]:
        """
        Deliver an event to all matching webhooks for a user.

        Args:
            event_type: The event type (e.g., "rule.created")
            payload: Event data
            user_id: UUID of the user

        Returns:
            List of WebhookDelivery records
        """
        # Find matching webhooks
        result = await self.db.execute(
            select(Webhook)
            .where(Webhook.user_id == user_id)
            .where(Webhook.active == True)
        )
        webhooks = result.scalars().all()

        deliveries = []
        for webhook in webhooks:
            # Check if this webhook subscribes to this event type
            if webhook.events and event_type not in webhook.events:
                # Also check for wildcard subscriptions (e.g., "rule.*")
                prefix = event_type.rsplit(".", 1)[0] + ".*" if "." in event_type else None
                if not prefix or prefix not in webhook.events:
                    continue

            delivery = await self._send_webhook(webhook, event_type, payload)
            deliveries.append(delivery)

        return deliveries

    async def get_deliveries(
        self,
        webhook_id: UUID,
        limit: int = 50
    ) -> List[WebhookDelivery]:
        """Get recent delivery history for a webhook."""
        result = await self.db.execute(
            select(WebhookDelivery)
            .where(WebhookDelivery.webhook_id == webhook_id)
            .order_by(WebhookDelivery.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def retry_failed_deliveries(self) -> int:
        """
        Retry failed webhook deliveries.

        Returns the number of retried deliveries.
        """
        # Find failed deliveries that haven't exceeded max attempts
        result = await self.db.execute(
            select(WebhookDelivery)
            .where(WebhookDelivery.success == False)
            .where(WebhookDelivery.attempt_number < WebhookDelivery.max_attempts)
            .order_by(WebhookDelivery.created_at.asc())
            .limit(50)
        )
        failed = list(result.scalars().all())

        retried = 0
        for delivery in failed:
            webhook = await self.get_webhook(delivery.webhook_id)
            if not webhook or not webhook.active:
                continue

            # Retry the delivery
            delivery.attempt_number += 1
            success = await self._attempt_delivery(
                webhook, delivery.event_type, delivery.payload, delivery
            )

            if success:
                retried += 1

        return retried

    async def send_test_event(self, webhook_id: UUID) -> Optional[WebhookDelivery]:
        """Send a test event to a webhook."""
        webhook = await self.get_webhook(webhook_id)
        if not webhook:
            return None

        test_payload = {
            "test": True,
            "message": "This is a test webhook delivery from Personal AI OS",
            "timestamp": datetime.utcnow().isoformat(),
        }

        return await self._send_webhook(webhook, "webhook.test", test_payload)

    # --- Internal ---

    async def _send_webhook(
        self,
        webhook: Webhook,
        event_type: str,
        payload: Dict[str, Any]
    ) -> WebhookDelivery:
        """Send a webhook and record the delivery."""
        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event_type=event_type,
            payload=payload,
        )
        self.db.add(delivery)
        await self.db.flush()

        await self._attempt_delivery(webhook, event_type, payload, delivery)

        return delivery

    async def _attempt_delivery(
        self,
        webhook: Webhook,
        event_type: str,
        payload: dict,
        delivery: WebhookDelivery
    ) -> bool:
        """
        Attempt to deliver a webhook payload with HMAC-SHA256 signing.

        Returns True if delivery was successful.
        """
        # Build the full payload
        body = json.dumps({
            "event": event_type,
            "data": payload,
            "timestamp": datetime.utcnow().isoformat(),
            "webhook_id": str(webhook.id),
        }, default=str)

        # Compute HMAC-SHA256 signature
        signature = hmac.new(
            webhook.secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-Event": event_type,
            "X-Webhook-Id": str(webhook.id),
            "User-Agent": "PersonalAIOS/1.0",
        }

        timeout = getattr(settings, 'webhook_timeout', 10)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    webhook.url,
                    content=body,
                    headers=headers,
                )

                delivery.status_code = response.status_code
                delivery.response_body = response.text[:1000]  # Truncate
                delivery.success = 200 <= response.status_code < 300
                delivery.delivered_at = datetime.utcnow()

                # Reset or increment failure counter
                if delivery.success:
                    webhook.consecutive_failures = 0
                else:
                    webhook.consecutive_failures += 1

                # Auto-disable after too many consecutive failures
                max_retries = getattr(settings, 'webhook_max_retries', 3)
                if webhook.consecutive_failures >= max_retries * 3:
                    webhook.active = False

                return delivery.success

        except Exception as e:
            delivery.error_message = str(e)[:500]
            delivery.success = False
            webhook.consecutive_failures += 1
            return False
