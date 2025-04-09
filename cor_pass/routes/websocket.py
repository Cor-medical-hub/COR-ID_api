from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from cor_pass.database.models import CorIdAuthSession, AuthSessionStatus
from cor_pass.services import websocket as ws
from datetime import datetime

from cor_pass.database.db import get_db


router = APIRouter(prefix="/websockets", tags=["Websockets"])

@router.websocket("/ws/auth/{session_token}")
async def websocket_endpoint(websocket: WebSocket, session_token: str, db: Session = Depends(get_db)):
    """
    WebSocket-эндпоинт для ожидания статуса подтверждения от Cor-ID.
    """
    await websocket.accept()
    ws.active_connections[session_token] = websocket
    try:
        while True:
            # Ожидаем сообщения от клиента (хотя в нашем случае клиент только подключается и ждет)
            data = await websocket.receive_text()
            print(f"Получено сообщение от клиента {session_token}: {data}")
            # В этом сценарии Cor-Energy только ждет, поэтому обработка входящих сообщений не нужна.
            # Но можно добавить логирование или обработку пингов, если потребуется.
    except WebSocketDisconnect:
        print(f"Клиент {session_token} отключился")
        del ws.active_connections[session_token]
    except Exception as e:
        print(f"Ошибка в WebSocket-соединении с {session_token}: {e}")
        del ws.active_connections[session_token]