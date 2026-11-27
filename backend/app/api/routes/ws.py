import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ws"])


class ConnectionManager:
    """Tracks authenticated WebSocket clients and scopes ticket broadcasts."""

    def __init__(self):
        self.active_connections: list[dict] = []

    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[int] = None,
        role: Optional[str] = None,
    ):
        await websocket.accept()
        self.active_connections.append({
            "ws": websocket,
            "user_id": user_id,
            "role": role,
        })
        logger.info("New WebSocket client connected. Active: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        before = len(self.active_connections)
        self.active_connections = [
            conn for conn in self.active_connections if conn["ws"] is not websocket
        ]
        if len(self.active_connections) < before:
            logger.info("WebSocket client disconnected. Active: %d", len(self.active_connections))

    async def broadcast(self, message: dict, owner_id: Optional[int] = None):
        """Send event to admins and the owning user (or all clients if owner_id is None)."""
        logger.info(
            "Broadcasting message %s (owner_id=%s) across %d clients",
            message,
            owner_id,
            len(self.active_connections),
        )
        for conn in list(self.active_connections):
            if owner_id is not None and conn["role"] != "admin" and conn["user_id"] != owner_id:
                continue
            ws = conn["ws"]
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error("Error broadcasting to connection: %s", e)
                self.disconnect(ws)


manager = ConnectionManager()


@router.websocket("/ws/tickets")
async def websocket_ticket_updates(
    websocket: WebSocket,
    token: str = Query(None),
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint that streams ticket status changes.
    Authenticates the JWT token prior to registering the socket.
    """
    if not token:
        logger.warning("WebSocket connection attempt missing authentication token.")
        await websocket.close(code=4008)
        return

    email = decode_access_token(token)
    if not email:
        logger.warning("WebSocket connection attempt with invalid token.")
        await websocket.close(code=4008)
        return

    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.warning("WebSocket connection: authenticated user not found in DB.")
        await websocket.close(code=4008)
        return

    await manager.connect(websocket, user_id=user.id, role=user.role)
    logger.info("WebSocket client authenticated successfully for user: %s", user.email)

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("Error in websocket loop: %s", e)
        manager.disconnect(websocket)
