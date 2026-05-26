"""
Personal AI OS - Webhook Dispatcher Background Job

Retries failed webhook deliveries with exponential backoff.
"""
from datetime import datetime

from app.db.session import async_session_maker
from app.services.webhook_service import WebhookService


async def retry_failed_webhooks():
    """
    Background job: Retry failed webhook deliveries.

    Runs every 5 minutes. Picks up failed deliveries that
    haven't exceeded their max attempts and retries them.
    """
    print(f"[WebhookDispatcher] Starting retry run at {datetime.utcnow()}")

    async with async_session_maker() as db:
        try:
            webhook_service = WebhookService(db)
            retried = await webhook_service.retry_failed_deliveries()

            await db.commit()
            print(f"[WebhookDispatcher] Completed: retried {retried} deliveries")

        except Exception as e:
            print(f"[WebhookDispatcher] Error: {e}")
            await db.rollback()
            raise
