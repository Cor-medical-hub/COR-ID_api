from typing import List, Dict
from fastapi import WebSocket, WebSocketDisconnect
import logging
import json

from cor_pass.services.logger import logger


class WebSocketEventsManager:
    """
    Управляет активными WebSocket-подключениями и рассылкой событий.
    """
    def __init__(self):
        # Список активных WebSocket-подключений.
        # В более сложных сценариях можно использовать Dict[str, WebSocket]
        # чтобы идентифицировать клиентов, но для начала список подойдет.
        self.active_connections: List[WebSocket] = []
        logger.info("WebSocketEventsManager initialized.")

    async def connect(self, websocket: WebSocket):
        """
        Устанавливает новое WebSocket-соединение.
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected: {websocket.client.host}:{websocket.client.port}. Total active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """
        Закрывает WebSocket-соединение.
        """
        try:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected: {websocket.client.host}:{websocket.client.port}. Total active: {len(self.active_connections)}")
        except ValueError:
            # Если по какой-то причине уже удален из списка
            logger.warning(f"Attempted to disconnect a WebSocket not in active connections: {websocket.client.host}:{websocket.client.port}")


    async def broadcast_event(self, event_data: Dict):
        """
        Рассылает событие всем активным WebSocket-подключениям.
        """
        message = json.dumps(event_data)
        disconnected_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
                logger.debug(f"Event sent to {connection.client.host}:{connection.client.port}: {message}")
            except WebSocketDisconnect:
                # Если клиент отключился во время отправки
                logger.warning(f"WebSocket disconnected during broadcast: {connection.client.host}:{connection.client.port}. Removing from list.")
                disconnected_connections.append(connection)
            except Exception as e:
                # Обработка других ошибок отправки (например, если соединение оборвалось)
                logger.error(f"Error sending event to {connection.client.host}:{connection.client.port}: {e}", exc_info=True)
                disconnected_connections.append(connection)

        # Удаляем отключившиеся соединения после завершения итерации
        for connection in disconnected_connections:
            self.active_connections.remove(connection)
        logger.info(f"Broadcast complete. Total active connections after cleanup: {len(self.active_connections)}")

# Инициализируем менеджер подключений как синглтон
websocket_events_manager = WebSocketEventsManager()