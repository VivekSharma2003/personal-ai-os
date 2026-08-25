"""
Personal AI OS - WebSocket Manager
"""
import json
import logging
import asyncio
from typing import Dict, Set, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Maps user_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"User {user_id} connected to WebSocket. Total connections: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected from WebSocket.")

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            for connection in list(self.active_connections[user_id]):
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error sending message to {user_id}: {e}")
                    self.disconnect(connection, user_id)

    async def send_event(self, event_type: str, data: Any, user_id: str):
        """Helper to send structured JSON events."""
        payload = json.dumps({
            "type": event_type,
            "data": data
        })
        await self.send_personal_message(payload, user_id)

    async def broadcast(self, message: str):
        """Broadcast to all connected users."""
        for user_id, connections in self.active_connections.items():
            for connection in list(connections):
                try:
                    await connection.send_text(message)
                except Exception:
                    self.disconnect(connection, user_id)


# Global manager instance
manager = ConnectionManager()
