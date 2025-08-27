import asyncio
from datetime import datetime, timezone
import socket
from typing import List, Dict
import uuid
from fastapi import WebSocket, WebSocketDisconnect, status
import json
from cor_pass.database.redis_db import redis_client
from fastapi.websockets import WebSocketState

from loguru import logger


def get_websocket_client_ip(websocket: WebSocket) -> str:
    """
    Получение реального IP-адреса клиента WebSocket из scope.
    Аналогично get_client_ip для HTTP-запросов, но адаптировано под WebSocket.
    """
    scope = websocket.scope
    headers = {k.decode("utf-8"): v.decode("utf-8") for k, v in scope["headers"]}

    if "x-forwarded-for" in headers:
        client_ip = headers["x-forwarded-for"].split(",")[0].strip()
    elif "x-real-ip" in headers:
        client_ip = headers["x-real-ip"].strip()
    elif "http_client_ip" in headers:
        client_ip = headers["http_client_ip"].strip()
    else:
        client = scope.get("client")
        if client:
            client_ip = client[0]
        else:
            client_ip = "unknown"

    return client_ip


class WebSocketEventsManager:
    """Менеджер WebSocket с Redis для многоворкеров."""

    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        self.active_connections: Dict[str, WebSocket] = {}  
        logger.info(f"WebSocketEventsManager initialized for worker {worker_id}")

    async def init_redis_listener(self):
        """Запуск подписки на глобальный Redis канал."""
        asyncio.create_task(self._listen_pubsub())

    async def _listen_pubsub(self):
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("ws:broadcast", f"ws:direct:{self.worker_id}")

        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                event = json.loads(message["data"])
                if message["channel"] == b"ws:broadcast":
                    await self._send_to_local(event)
                elif message["channel"] == f"ws:direct:{self.worker_id}".encode():
                    await self._send_direct_local(event)
            except Exception as e:
                logger.error(f"Failed to handle pubsub message: {e}", exc_info=True)

    async def connect(self, websocket: WebSocket, session_token: str | None = None) -> str:
        """Подключение клиента. Привязка connection_id к session_token в Redis."""
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        connected_at = datetime.now(timezone.utc).isoformat()
        client_ip = get_websocket_client_ip(websocket)

        if not session_token:
            session_token = str(uuid.uuid4())
        logger.debug(f"self.active_connections[connection_id] = websocket {connection_id}")
        logger.debug(f"session_token {session_token}")
        self.active_connections[connection_id] = websocket

        await redis_client.hset(
            f"ws:connection:{connection_id}",
            mapping={
                "worker_id": self.worker_id,
                "session_token": session_token,
                "connected_at": connected_at,
                "client_ip": client_ip,
            },
        )
        logger.debug(f"redis_client.hset")
        await redis_client.sadd("ws:connections", connection_id)
        logger.debug(f"redis_client.sadd")


        # связь session_token -> connection_id
        await redis_client.hset(
            f"ws:session:{session_token}",
            mapping={
                "worker_id": self.worker_id,
                "connection_id": connection_id,
                "connected_at": connected_at,
                "client_ip": client_ip,
            },
        )
        logger.debug(f"redis_client.hset {session_token}")

        logger.info(f"WS connected {connection_id} (session={session_token}) from {client_ip}")
        return connection_id

    async def disconnect(self, connection_id: str):
        """Отключение WebSocket клиента."""
        websocket = self.active_connections.pop(connection_id, None)
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)

        await redis_client.delete(f"ws:connection:{connection_id}")
        await redis_client.srem("ws:connections", connection_id)

        logger.info(f"WS disconnected {connection_id}")

    async def broadcast_event(self, event_data: dict) -> None:
        """
        Шлём всем: сразу локально (быстрый путь) + публикуем в Redis для других воркеров.
        Логируем число подписчиков, чтобы сразу видеть проблему (0 → никто не слушает).
        """
        await self._send_to_local(event_data)
        payload = json.dumps(event_data)
        try:
            receivers = await redis_client.publish("ws:broadcast", payload)
            logger.debug(f"Published to ws:broadcast; receivers={receivers}")
            if receivers == 0:
                logger.warning("No Redis subscribers on ws:broadcast (receivers=0)")
        except Exception as e:
            logger.error(f"publish failed: {e}", exc_info=True)

    async def _send_to_local(self, event: Dict):
        """Отправка события всем локальным подключенным клиентам этого воркера."""
        dead_ids = []

        for connection_id, websocket in self.active_connections.items():
            if websocket.client_state != WebSocketState.CONNECTED:
                dead_ids.append(connection_id)
                continue
            try:
                await websocket.send_text(json.dumps(event))
            except Exception as e:
                logger.warning(f"Error sending to {connection_id}: {e}")
                dead_ids.append(connection_id)

        for cid in dead_ids:
            self.active_connections.pop(cid, None)
            await redis_client.delete(f"ws:connection:{cid}")
            await redis_client.srem("ws:connections", cid)

        logger.info(f"Local broadcast complete. Active connections: {len(self.active_connections)}")

    async def send_to_client(self, session_token: str, event: Dict):
        """Отправка сообщения конкретному клиенту по его session_token."""
        meta = await redis_client.hgetall(f"ws:session:{session_token}")
        if not meta:
            logger.warning(f"Session {session_token} not found in Redis")
            return

        target_worker = meta.get("worker_id")
        connection_id = meta.get("connection_id")

        if not target_worker or not connection_id:
            logger.warning(f"Invalid meta for session {session_token}: {meta}")
            return

        message = json.dumps({
            "type": "direct",
            "connection_id": connection_id,
            "event": event,
        })

        if target_worker == self.worker_id:
            ws = self.active_connections.get(connection_id)
            if ws and ws.client_state == WebSocketState.CONNECTED:
                await ws.send_text(message)
            else:
                logger.warning(f"Local client {connection_id} not connected")
        else:
            await redis_client.publish(f"ws:direct:{target_worker}", message)

    async def send_to_client_cor_energy(self, session_token: str, event: Dict):
        """Отправка сообщения конкретному клиенту по его session_token."""
        meta = await redis_client.hgetall(f"ws:session:{session_token}")
        if not meta:
            logger.warning(f"Session {session_token} not found in Redis")
            return

        target_worker = meta.get("worker_id")
        connection_id = meta.get("connection_id")

        if not target_worker or not connection_id:
            logger.warning(f"Invalid meta for session {session_token}: {meta}")
            return
        
        message = json.dumps(event)

        if target_worker == self.worker_id:
            ws = self.active_connections.get(connection_id)
            if ws and ws.client_state == WebSocketState.CONNECTED:
                await ws.send_text(message)
            else:
                logger.warning(f"Local client {connection_id} not connected")
        else:
            await redis_client.publish(f"ws:direct:{target_worker}", message)

    async def _send_direct_local(self, event: Dict):
        """Отправка события конкретному локальному клиенту."""
        connection_id = event.get("connection_id")
        ws = self.active_connections.get(connection_id)

        if not ws or ws.client_state != WebSocketState.CONNECTED:
            logger.warning(f"Direct send failed, no local client {connection_id}")
            return

        try:
            await ws.send_text(json.dumps(event["event"]))
        except Exception as e:
            logger.error(f"Error sending direct to {connection_id}: {e}")
            await self.disconnect(connection_id)


websocket_events_manager = WebSocketEventsManager(worker_id=socket.gethostname())
