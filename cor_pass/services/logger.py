import logging
from loguru import logger
import sys
from cor_pass.config.config import settings

logger_level = "DEBUG" if settings.debug else "INFO"

logger.remove() 
# logger.add(
#     "logs/application.log",   # Путь к файлу логов
#     rotation="500 MB",    # Размер файла перед ротацией
#     retention="10 days",  # Хранение логов в течение 10 дней
#     compression="zip",    # Сжатие старых логов
#     level=logger_level,   # Уровень логирования
#     format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
# )

logger.add(
    sys.stdout, 
    level=logger_level,  
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
)


logger.remove()
logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}", level="INFO")

uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.handlers = [] 
uvicorn_access_logger.propagate = False 

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(client_addr)s - "%(request_line)s" %(status_code)s', datefmt='%Y-%m-%d %H:%M:%S %z')
handler.setFormatter(formatter)
uvicorn_access_logger.addHandler(handler)
uvicorn_access_logger.setLevel(logging.INFO)
