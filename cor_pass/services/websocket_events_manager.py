from typing import List, Dict
import uuid
from fastapi import WebSocket, WebSocketDisconnect, status
import logging
import json

from fastapi.websockets import WebSocketState

from cor_pass.services.logger import logger


class WebSocketEventsManager:
    """
    Управляет активными WebSocket-подключениями и рассылкой событий.
    """
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        logger.info("WebSocketEventsManager initialized.")

    async def connect(self, websocket: WebSocket) -> str:
        """
        Устанавливает новое WebSocket-соединение и присваивает ему уникальный ID.
        Возвращает ID соединения.
        """
        await websocket.accept()
        connection_id = str(uuid.uuid4()) 
        self.active_connections[connection_id] = websocket
        logger.info(f"WebSocket connected: {websocket.client.host}:{websocket.client.port} with ID: {connection_id}. Total active: {len(self.active_connections)}")
        return connection_id

    def disconnect(self, connection_id: str):
        """
        Закрывает WebSocket-соединение по его ID.
        """
        websocket = self.active_connections.pop(connection_id, None)
        if websocket:
            try:
                logger.info(f"WebSocket with ID {connection_id} disconnected: {websocket.client.host}:{websocket.client.port}. Total active: {len(self.active_connections)}")
            except RuntimeError as e:
                logger.warning(f"Could not close WebSocket with ID {connection_id}, already closed or error: {e}")
        else:
            logger.warning(f"Attempted to disconnect non-existent WebSocket with ID: {connection_id}")

    async def disconnect_all(self):
        """
        Отключает все активные WebSocket-соединения.
        """
        connection_ids_to_disconnect = list(self.active_connections.keys())

        logger.info(f"Initiating disconnection of {len(connection_ids_to_disconnect)} active WebSocket connections.")

        for connection_id in connection_ids_to_disconnect:
            websocket = self.active_connections.get(connection_id)
            if websocket:
                try:
                    # Отправляем сообщение об отключении перед закрытием
                    await websocket.send_json({"event_type": "server_disconnect", "reason": "All connections reset by administrative action"})
                    await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                    logger.info(f"Force-disconnected WebSocket with ID {connection_id}: {websocket.client.host}:{websocket.client.port}")
                except RuntimeError as e:
                    logger.warning(f"Error closing WebSocket {connection_id} during disconnect_all: {e} (might be already closed)")
                except Exception as e:
                    logger.error(f"Unexpected error when closing WebSocket {connection_id} during disconnect_all: {e}", exc_info=True)
                finally:
                    self.active_connections.pop(connection_id, None)
            else:
                logger.warning(f"WebSocket with ID {connection_id} already removed from active_connections during disconnect_all.")

        logger.info(f"All WebSocket connections disconnection attempt complete. Total active: {len(self.active_connections)}")

    async def disconnect_by_id_internal(self, connection_id: str):
        """
        Внутренний метод для отключения по ID, безопасно удаляет из словаря.
        """
        websocket = self.active_connections.get(connection_id)
        if websocket:
            try:
                await websocket.send_json({"event_type": "disconnect_server_initiated", "reason": "Administrative action"})
                await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                logger.info(f"Force-disconnected WebSocket with ID {connection_id}: {websocket.client.host}:{websocket.client.port}")
            except RuntimeError as e:
                logger.warning(f"Error closing WebSocket {connection_id}: {e} (might be already closed)")
            except Exception as e:
                logger.error(f"Unexpected error when closing WebSocket {connection_id}: {e}")
            finally:
                self.active_connections.pop(connection_id, None)
        else:
            logger.warning(f"Attempted to disconnect non-existent WebSocket (internal) with ID: {connection_id}")


    def get_active_connection_info(self) -> List[Dict]:
        """
        Возвращает информацию обо всех активных соединениях.
        """
        info = []
        for conn_id, ws in self.active_connections.items():
            info.append({
                "connection_id": conn_id,
                "client_host": ws.client.host,
                "client_port": ws.client.port,
            })
        return info    
            
    async def broadcast_event(self, event_data: Dict):
        """
        Рассылает событие всем активным WebSocket-подключениям.
        """
        message = json.dumps(event_data)
        connections_to_check = list(self.active_connections.keys())
        for connection_id in connections_to_check:
            connection = self.active_connections.get(connection_id)
            if not connection:
                continue 

            if connection.client_state != WebSocketState.CONNECTED:
                logger.warning(f"Skipping disconnected/closing WebSocket ID {connection_id}. State: {connection.client_state}")
                self.active_connections.pop(connection_id, None)
                continue

            try:
                await connection.send_text(message)
                logger.debug(f"Event sent to {connection.client.host}:{connection.client.port}: {message}")
            except WebSocketDisconnect:
                logger.warning(f"WebSocket disconnected during broadcast: {connection.client.host}:{connection.client.port}. Removing from list.")
                self.active_connections.pop(connection_id, None)
            except RuntimeError as e:
                # Это может быть, если соединение закрывается одновременно с отправкой
                logger.warning(f"RuntimeError sending to WebSocket {connection.client.host}:{connection.client.port}: {e}. Removing.")
                self.active_connections.pop(connection_id, None)
            except Exception as e:
                logger.error(f"Error sending event to {connection.client.host}:{connection.client.port}: {e}", exc_info=True)
                self.active_connections.pop(connection_id, None)

        logger.info(f"Broadcast complete. Total active connections after cleanup: {len(self.active_connections)}")

websocket_events_manager = WebSocketEventsManager()