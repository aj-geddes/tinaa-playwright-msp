"""WebSocket connection manager and endpoint for real-time TINAA updates."""

import logging
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info("WebSocket client connected: %s", client_id)

    async def disconnect(self, client_id: str) -> None:
        """Remove a connection from the registry; no-op for unknown IDs."""
        self.active_connections.pop(client_id, None)
        logger.info("WebSocket client disconnected: %s", client_id)

    async def send_update(self, client_id: str, data: dict[str, Any]) -> None:
        """Send a JSON message to a specific client; silently drops unknown IDs."""
        websocket = self.active_connections.get(client_id)
        if websocket is None:
            return
        await websocket.send_json(data)

    async def broadcast(self, data: dict[str, Any]) -> None:
        """Send a JSON message to every connected client."""
        for websocket in list(self.active_connections.values()):
            await websocket.send_json(data)

    async def send_test_progress(
        self, client_id: str, run_id: str, progress: dict[str, Any]
    ) -> None:
        """Push a test_progress message to a specific client."""
        await self.send_update(
            client_id,
            {"type": "test_progress", "run_id": run_id, "progress": progress},
        )


def setup_websocket(app: FastAPI) -> None:
    """Register the /ws/{client_id} WebSocket endpoint on the application."""
    manager = ConnectionManager()

    @app.websocket("/ws/{client_id}")
    async def websocket_endpoint(websocket: WebSocket, client_id: str) -> None:
        """WebSocket endpoint for real-time TINAA updates.

        Supported client message types:
        - ``{"type": "ping"}`` — receives ``{"type": "pong"}``
        - ``{"type": "subscribe", "product_id": str}`` — subscribes to a product;
          receives ``{"type": "subscribed", "product_id": str}``

        Server push types:
        - ``test_progress`` — live test run progress
        - ``quality_update`` — quality score change
        - ``alert`` — system alert
        - ``deployment`` — deployment event
        """
        await manager.connect(client_id, websocket)
        try:
            while True:
                message = await websocket.receive_json()
                msg_type = message.get("type")

                if msg_type == "ping":
                    await manager.send_update(client_id, {"type": "pong"})

                elif msg_type == "subscribe":
                    product_id = message.get("product_id", "")
                    await manager.send_update(
                        client_id,
                        {"type": "subscribed", "product_id": product_id},
                    )

        except WebSocketDisconnect:
            await manager.disconnect(client_id)
