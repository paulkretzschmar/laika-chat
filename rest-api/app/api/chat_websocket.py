from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, List, Optional
from .auth import get_current_user_for_websocket
from ..db import repository as repo
from ..db.models import Message
from ..config import settings
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, chat_id: str, websocket: WebSocket):
        await websocket.accept()
        logger.info(f"websocket connected")
        self.active_connections.setdefault(chat_id, []).append(websocket)

    def disconnect(self, chat_id: str, websocket: WebSocket):
        self.active_connections[chat_id].remove(websocket)
        logger.info(f"websocket disconnected")
        if not self.active_connections[chat_id]:
            del self.active_connections[chat_id]

    async def broadcast(self, chat_id: str, message: Message):
        for connection in self.active_connections.get(chat_id, []):
            await connection.send_json(message)

manager = ConnectionManager()
router = APIRouter()

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM

@router.websocket("/chat/{chat_id}")
async def websocket_connection(websocket: WebSocket, chat_id: str, token: Optional[str] = Query(None)):
    header_token = websocket.headers.get("Authorization")
    if header_token and header_token.startswith("Bearer "):
        token = header_token[7:]
    if not token:
        await websocket.close(code=1008)
        return
    user_id = await get_current_user_for_websocket(token)
    if not user_id:
        await websocket.close(code=1008)
        return
    await manager.connect(chat_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            message_content = data.get("content")
            logger.info(f"[WS RECEIVE] Chat {chat_id}, User {user_id}, Content: {message_content}")
            result = await repo.check_message(
                websocket.app.database,
                chat_id,
                user_id,
                message_content
            )
            for res in result:
                await manager.broadcast(chat_id, res)
    except WebSocketDisconnect:
        manager.disconnect(chat_id, websocket)
