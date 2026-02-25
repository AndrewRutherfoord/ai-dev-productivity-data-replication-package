import logging
import json

from fastapi import WebSocketDisconnect, WebSocket

from common.util import DateTimeEncoder

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Stores connected notification websockets so that on message queue responses a notification can be sent"""

    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket connected")

    def disconnect(self, websocket: WebSocket):
        self.active_connections = [
            ws for ws in self.active_connections if ws != websocket
        ]
        logger.info("WebSocket disconnected")

    async def send_message(self, data: dict):
        logger.warning("WS Sending message")
        logger.warning(self.active_connections)
        for socket in self.active_connections:
            msg = json.dumps(data, cls=DateTimeEncoder)
            try:
                await socket.send_text(msg)
            except WebSocketDisconnect:
                self.disconnect(socket)
            except RuntimeError:
                self.disconnect(socket)


# Global socket connection manager
socket_connections = ConnectionManager()
