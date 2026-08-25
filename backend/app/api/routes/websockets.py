"""
Personal AI OS - WebSocket Routes
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
from typing import Optional

from app.dependencies import get_db
from app.services.rule_engine import RuleEngineService
from app.services.websocket_manager import manager

router = APIRouter(tags=["WebSockets"])


async def get_user_from_token(token: str, db: AsyncSession) -> Optional[str]:
    """Validate a connection token. For this MVP, token = external_id."""
    service = RuleEngineService(db)
    try:
        user = await service.get_or_create_user(token)
        return str(user.id)
    except Exception:
        return None


@router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str, db: AsyncSession = Depends(get_db)):
    """
    WebSocket endpoint for real-time telemetry, rule application events,
    and system status updates.
    """
    user_id = await get_user_from_token(token, db)
    
    if not user_id:
        await websocket.close(code=1008)
        return
        
    await manager.connect(websocket, user_id)
    
    # Send a welcome event
    await manager.send_event("system_status", {"status": "connected", "message": "Connected to Personal AI OS Telemetry Stream"}, user_id)
    
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            
            # Simple echo/acknowledgment for client telemetry
            await manager.send_event("ack", {"received": data}, user_id)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
