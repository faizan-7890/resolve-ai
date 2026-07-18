import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ws"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket client connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Active: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        logger.info(f"Broadcasting message: {message} to {len(self.active_connections)} clients")
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                self.disconnect(connection)

manager = ConnectionManager()

@router.websocket("/ws/tickets")
async def websocket_ticket_updates(
    websocket: WebSocket,
    token: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint that streams ticket status changes.
    Authenticates using token query parameter.
    """
    await manager.connect(websocket)
    
    if not token:
        logger.warning("WebSocket connection attempt missing authentication token.")
        await websocket.close(code=4008)  # Policy Violation
        manager.disconnect(websocket)
        return

    email = decode_access_token(token)
    if not email:
        logger.warning("WebSocket connection attempt with invalid token.")
        await websocket.close(code=4008)  # Policy Violation
        manager.disconnect(websocket)
        return

    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.warning("WebSocket connection: authenticated user not found in DB.")
        await websocket.close(code=4008)  # Policy Violation
        manager.disconnect(websocket)
        return

    logger.info(f"WebSocket client authenticated successfully for user: {user.email}")
    
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error in websocket loop: {e}")
        manager.disconnect(websocket)
