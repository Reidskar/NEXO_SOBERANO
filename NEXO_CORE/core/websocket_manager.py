import logging
from typing import List, Dict
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, tenant: str):
        await websocket.accept()
        if tenant not in self.active_connections:
            self.active_connections[tenant] = []
        self.active_connections[tenant].append(websocket)
        logger.info(f"🔌 Cliente WS conectado a tenant: {tenant}")

    def disconnect(self, websocket: WebSocket, tenant: str):
        if tenant in self.active_connections:
            try:
                self.active_connections[tenant].remove(websocket)
            except ValueError:
                pass

    async def broadcast(self, tenant: str, message: dict):
        if tenant in self.active_connections:
            for connection in self.active_connections[tenant]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.debug(f"Failed to send WS message: {e}")

# Single global instance for all modules
manager = ConnectionManager()
