import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from cor_pass.database.models import CorIdAuthSession, AuthSessionStatus
from datetime import datetime, timedelta

from cor_pass.database.db import SessionLocal

# Словарь для хранения активных WebSocket-соединений (session_token -> WebSocket)
active_connections: dict[str, WebSocket] = {}


async def send_websocket_message(session_token: str, message: dict):
    """Отправляет сообщение через WebSocket конкретному клиенту."""
    if session_token in active_connections:
        await active_connections[session_token].send_json(message)


async def close_websocket_connection(session_token: str):
    """Закрывает WebSocket-соединение и удаляет его из активных."""
    if session_token in active_connections:
        await active_connections[session_token].close()
        del active_connections[session_token]
        print(f"WebSocket соединение для {session_token} закрыто из-за таймаута.")


async def check_session_timeouts():
    """Фоновая задача для проверки и обработки таймаутов сессий."""
    while True:
        db = SessionLocal()  # Создаем новую сессию внутри задачи
        try:
            now = datetime.utcnow()
            expired_sessions = (
                db.query(CorIdAuthSession)
                .filter(
                    CorIdAuthSession.status == AuthSessionStatus.PENDING,
                    CorIdAuthSession.expires_at < now,
                )
                .all()
            )

            for session in expired_sessions:
                session.status = AuthSessionStatus.TIMEOUT
                db.commit()
                await send_websocket_message(
                    session.session_token, {"status": "timeout"}
                )
                await close_websocket_connection(
                    session.session_token
                )  # Закрываем соединение

            db.close()  # Закрываем сессию после использования
        except Exception as e:
            print(f"Ошибка в фоновой задаче проверки таймаутов: {e}")
            if db:
                db.rollback()
                db.close()

        await asyncio.sleep(60)  # Проверять каждую минуту


async def cleanup_auth_sessions():
    """Фоновая задача для удаления старых сессий авторизации."""
    while True:
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            # Удаляем сессии, которые истекли
            expired_sessions = (
                db.query(CorIdAuthSession)
                .filter(CorIdAuthSession.expires_at < now)
                .delete(synchronize_session="fetch")
            )

            # Удаляем завершенные сессии старше определенного периода (например, 1 день)
            cutoff_time = now - timedelta(days=1)
            completed_sessions = (
                db.query(CorIdAuthSession)
                .filter(
                    CorIdAuthSession.status.in_(
                        [
                            AuthSessionStatus.APPROVED,
                            AuthSessionStatus.REJECTED,
                            AuthSessionStatus.TIMEOUT,
                        ]
                    ),
                    CorIdAuthSession.created_at < cutoff_time,
                )
                .delete(synchronize_session="fetch")
            )

            db.commit()
            print(
                f"Удалено {expired_sessions} истекших сессий и {completed_sessions} завершенных сессий."
            )
            db.close()
        except Exception as e:
            print(f"Ошибка при очистке сессий авторизации: {e}")
            if db:
                db.rollback()
                db.close()

        await asyncio.sleep(3600)  # Запускать каждый час (настрой по необходимости)
