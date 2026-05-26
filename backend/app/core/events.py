"""
Personal AI OS - Event Bus

In-process async event system for internal listeners and webhook dispatch.
Supports subscribe/emit pattern with async handlers.
"""
import asyncio
from typing import Callable, Dict, List, Any, Optional
from datetime import datetime


class EventBus:
    """
    Singleton event bus for pub/sub within the application.

    Event types follow dot-notation convention:
        - rule.created, rule.updated, rule.archived, rule.conflict_detected
        - chat.completed, chat.streamed
        - feedback.processed
        - webhook.delivered, webhook.failed

    Usage:
        event_bus.subscribe("rule.created", my_handler)
        await event_bus.emit("rule.created", {"rule_id": "...", "content": "..."})
    """

    _instance: Optional["EventBus"] = None
    _handlers: Dict[str, List[Callable]]
    _wildcard_handlers: List[Callable]

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers = {}
            cls._instance._wildcard_handlers = []
        return cls._instance

    def subscribe(self, event_type: str, handler: Callable):
        """
        Subscribe a handler to an event type.

        Args:
            event_type: The event type to listen for (e.g., "rule.created").
                        Use "*" to subscribe to all events.
            handler: Async callable receiving (event_type: str, payload: dict)
        """
        if event_type == "*":
            self._wildcard_handlers.append(handler)
        else:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable):
        """Remove a handler from an event type."""
        if event_type == "*":
            if handler in self._wildcard_handlers:
                self._wildcard_handlers.remove(handler)
        elif event_type in self._handlers:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)

    async def emit(self, event_type: str, payload: Dict[str, Any]):
        """
        Emit an event to all subscribed handlers.

        Handlers are called concurrently. Failures in one handler
        don't affect others.

        Args:
            event_type: The event type (e.g., "rule.created")
            payload: Event data dict
        """
        # Enrich payload with metadata
        enriched_payload = {
            **payload,
            "_event_type": event_type,
            "_emitted_at": datetime.utcnow().isoformat(),
        }

        # Collect all matching handlers
        handlers = list(self._wildcard_handlers)
        if event_type in self._handlers:
            handlers.extend(self._handlers[event_type])

        # Also match prefix handlers (e.g., "rule.*" matches "rule.created")
        prefix = event_type.rsplit(".", 1)[0] + ".*" if "." in event_type else None
        if prefix and prefix in self._handlers:
            handlers.extend(self._handlers[prefix])

        if not handlers:
            return

        # Execute all handlers concurrently, capturing errors
        tasks = []
        for handler in handlers:
            tasks.append(_safe_call(handler, event_type, enriched_payload))

        await asyncio.gather(*tasks)

    def clear(self):
        """Remove all handlers. Useful for testing."""
        self._handlers.clear()
        self._wildcard_handlers.clear()

    @property
    def registered_events(self) -> List[str]:
        """List all event types with registered handlers."""
        return list(self._handlers.keys())


async def _safe_call(handler: Callable, event_type: str, payload: dict):
    """Call a handler safely, catching and logging any errors."""
    try:
        if asyncio.iscoroutinefunction(handler):
            await handler(event_type, payload)
        else:
            handler(event_type, payload)
    except Exception as e:
        print(f"[EventBus] Handler error for '{event_type}': {e}")


# Module-level convenience functions
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global EventBus singleton."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


async def emit_event(event_type: str, payload: Dict[str, Any]):
    """Convenience function to emit an event."""
    bus = get_event_bus()
    await bus.emit(event_type, payload)
