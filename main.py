import time

import uvicorn
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import FastAPI, Request, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Histogram
from prometheus_client import generate_latest
from starlette.responses import Response

from cor_pass.routes import auth, person
from cor_pass.database.db import get_db
from cor_pass.database.redis_db import redis_client

from cor_pass.routes import (
    auth,
    records,
    tags,
    password_generator,
    cor_id,
    otp_auth,
    admin,
    lawyer,
    doctor,
    dicom
)
from cor_pass.config.config import settings
from cor_pass.services.logger import logger
from cor_pass.services.auth import auth_service
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from collections import defaultdict
from jose import JWTError, jwt

import logging


# Создание обработчика для логирования с временными метками
class CustomFormatter(logging.Formatter):
    def format(self, record):
        record.asctime = self.formatTime(record, self.datefmt)
        return super().format(record)


# Настройка логирования
log_formatter = CustomFormatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

logging.basicConfig(handlers=[console_handler], level=logging.INFO)


app = FastAPI()
app.mount("/static", StaticFiles(directory="cor_pass/static"), name="static")


origins = settings.allowed_redirect_urls


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")


# Пример метрик
REQUEST_COUNT = Counter("app_requests_total", "Total number of requests")
REQUEST_LATENCY = Histogram("app_request_latency_seconds", "Request latency")

# Middleware для CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Обработчики исключений
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    logger.error("An unhandled exception occurred", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal Server Error"},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error("Request validation error", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation Error"},
    )


# Маршруты
@app.get("/config")
def read_config():
    return {"ENV": settings.app_env}


@app.get("/", name="Корень")
def read_root(request: Request):
    REQUEST_COUNT.inc()
    with REQUEST_LATENCY.time():
        return FileResponse("cor_pass/static/login.html")


@app.get("/api/healthchecker")
def healthchecker(db: Session = Depends(get_db)):
    REQUEST_COUNT.inc()
    try:
        result = db.execute(text("SELECT 1")).fetchone()
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database is not configured correctly",
            )
        return {"message": "Welcome to FastApi, database work correctly"}
    except Exception as e:
        logger.error("Database connection error", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error connecting to the database",
        )


# Middleware для добавления заголовка времени обработки
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["My-Process-Time"] = str(process_time)
    return response


# Middleware для фиксирования активных пользователей
@app.middleware("http")
async def track_active_users(request: Request, call_next):
    user_token = request.headers.get("Authorization")
    if user_token:
        token_parts = user_token.split(" ")
        if len(token_parts) >= 2:
            try:
                decoded_token = jwt.decode(
                    token_parts[1],
                    options={"verify_signature": False},
                    key=auth_service.SECRET_KEY,
                    algorithms=[auth_service.ALGORITHM],
                )
                oid = decoded_token.get("oid")
                redis_client.set(oid, time.time())
            except JWTError:
                pass
    response = await call_next(request)
    return response


# Событие при старте приложения
@app.on_event("startup")
async def startup():
    print("------------- STARTUP --------------")


auth_attempts = defaultdict(list)
blocked_ips = {}

app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(records.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(password_generator.router, prefix="/api")
app.include_router(person.router, prefix="/api")
app.include_router(cor_id.router, prefix="/api")
app.include_router(otp_auth.router, prefix="/api")
app.include_router(lawyer.router, prefix="/api")
app.include_router(doctor.router, prefix="/api")
app.include_router(dicom.router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(
        app="main:app",
        host="192.168.153.203",
        port=8000,
        log_level="info",
        access_log=True,
        reload=settings.reload,
    )
# 192.168.153.203
