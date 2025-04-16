import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from cor_pass.database.models import CorIdAuthSession, AuthSessionStatus
from datetime import datetime, timedelta

from cor_pass.database.db import async_session_maker
from sqlalchemy.ext.asyncio import AsyncSession

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
    """Асинхронна фонова задача для перевірки та обробки таймаутів сесій."""
    while True:
        async with async_session_maker() as db:  # Використовуємо async with для керування сесією
            try:
                now = datetime.utcnow()
                stmt = select(CorIdAuthSession).where(
                    CorIdAuthSession.status == AuthSessionStatus.PENDING,
                    CorIdAuthSession.expires_at < now,
                )
                result = await db.execute(stmt)
                expired_sessions = result.scalars().all()

                for session in expired_sessions:
                    session.status = AuthSessionStatus.TIMEOUT
                    await db.commit()  # Комітимо зміни для кожної сесії одразу

                    await send_websocket_message(
                        session.session_token, {"status": "timeout"}
                    )
                    await close_websocket_connection(
                        session.session_token
                    )  # Закрываем соединение

            except Exception as e:
                print(f"Ошибка в асинхронной фоновой задаче проверки таймаутов: {e}")
                await db.rollback()
            finally:
                await asyncio.sleep(60)  # Проверять каждую минуту


async def cleanup_auth_sessions():
    """Асинхронна фонова задача для видалення старих сесій авторизації."""
    while True:
        async with async_session_maker() as db:
            try:
                now = datetime.utcnow()

                # Видаляємо сесії, які вже минули
                expired_stmt = delete(CorIdAuthSession).where(
                    CorIdAuthSession.expires_at < now
                )
                expired_result = await db.execute(expired_stmt)
                expired_count = expired_result.rowcount

                # Видаляємо завершені сесії старше певного періоду (наприклад, 1 день)
                cutoff_time = now - timedelta(days=1)
                completed_stmt = delete(CorIdAuthSession).where(
                    CorIdAuthSession.status.in_(
                        [
                            AuthSessionStatus.APPROVED,
                            AuthSessionStatus.REJECTED,
                            AuthSessionStatus.TIMEOUT,
                        ]
                    ),
                    CorIdAuthSession.created_at < cutoff_time,
                )
                completed_result = await db.execute(completed_stmt)
                completed_count = completed_result.rowcount

                await db.commit()
                print(
                    f"Асинхронно видалено {expired_count} прострочених сесій та {completed_count} завершених сесій."
                )
            except Exception as e:
                print(f"Ошибка при асинхронной очистке сессий авторизации: {e}")
                await db.rollback()
            finally:
                await asyncio.sleep(
                    3600
                )  # Запускати кожен час (настрой по необходимости)
