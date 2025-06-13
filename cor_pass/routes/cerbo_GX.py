import asyncio
from datetime import datetime
import json
from fastapi import APIRouter, HTTPException, status
import logging
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian
from cor_pass.database.redis_db import redis_client
from cor_pass.services.logger import logger

router = APIRouter(prefix="/modbus", tags=["Modbus"])

MODBUS_IP = "91.203.25.12"
MODBUS_PORT = 502
UNIT_ID = 225  # Pylontech battery

REGISTERS = {
    "soc": 266,        # % SoC (0.1%)
    "voltage": 259,    # Battery Voltage (V x100)
    "current": 261,    # Battery Current (A x10)
    "power": 258,      # Power (Watts, signed)
    "soh": 304         # State of Health (0.1%)
}


CACHE_KEY = "battery_status"
MODBUS_READ_INTERVAL_SECONDS = 5
CACHE_TTL_SECONDS = 10


def decode_signed_16(value: int) -> int:
    if value >= 0x8000:
        return value - 0x10000
    return value

@router.get("/battery_status")
async def get_battery_status():
    try:
        async with AsyncModbusTcpClient(host=MODBUS_IP, port=MODBUS_PORT) as client:
            await client.connect()

            start_address = min(REGISTERS.values())
            end_address = max(REGISTERS.values())
            count = end_address - start_address + 1

            result = await client.read_input_registers(start_address, count=count, slave=UNIT_ID)
            if result.isError():
                logging.error(f"❌ Ошибка чтения Modbus: {result}")
                raise HTTPException(status_code=500, detail="Ошибка чтения регистров батареи")

            raw = result.registers

            raw_current = raw[REGISTERS["current"] - start_address]
            current = decode_signed_16(raw_current) / 10

            raw_power = raw[REGISTERS["power"] - start_address]
            power = decode_signed_16(raw_power)

            raw_soh = raw[REGISTERS["soh"] - start_address]
            soh = raw_soh / 10

            status = {
                "soc": raw[REGISTERS["soc"] - start_address] / 10,
                "voltage": raw[REGISTERS["voltage"] - start_address] / 100,
                "current": current,
                "power": power,
                "soh": soh
            }

            return status

    except Exception as e:
        logging.error("❗ Ошибка получения данных с батареи", exc_info=e)
        raise HTTPException(status_code=500, detail="Modbus ошибка")



# Фоновая задача для чтения батарейки по модбасу и кеширования в Redis
async def read_modbus_and_cache():
    global redis_client
    if redis_client is None:
        logger.error("Redis client is not initialized in background task.")
        await asyncio.sleep(MODBUS_READ_INTERVAL_SECONDS)
        return

    logger.info("Starting background Modbus read task.")
    while True:
        try:
            async with AsyncModbusTcpClient(host=MODBUS_IP, port=MODBUS_PORT) as client:
                await client.connect()
                if not client:
                    logger.warning("Modbus client failed to connect. Retrying...")
                    await asyncio.sleep(MODBUS_READ_INTERVAL_SECONDS)
                    continue

                start_address = min(REGISTERS.values())
                end_address = max(REGISTERS.values())
                count = end_address - start_address + 1

                result = await client.read_input_registers(start_address, count=count, slave=UNIT_ID)
                if result.isError():
                    logging.error(f"❌ Ошибка чтения Modbus: {result}")
                    raise HTTPException(status_code=500, detail="Ошибка чтения регистров батареи")

                else:
                    raw = result.registers

                    raw_current = raw[REGISTERS["current"] - start_address]
                    current = decode_signed_16(raw_current) / 10
                    
                    raw_power = raw[REGISTERS["power"] - start_address]
                    power = decode_signed_16(raw_power)

                    raw_soh = raw[REGISTERS["soh"] - start_address]
                    soh = raw_soh / 10

                    status = {
                        "soc": raw[REGISTERS["soc"] - start_address] / 10,
                        "voltage": raw[REGISTERS["voltage"] - start_address] / 100,
                        "current": current,
                        "power": power,
                        "soh": soh,
                        "timestamp": datetime.now().isoformat()
                    }
                    

                    await redis_client.setex(CACHE_KEY, CACHE_TTL_SECONDS, json.dumps(status))
                    logger.info("✅ Данные с батареи успешно прочитаны и сохранены в Redis.")

        except Exception as e:
            logger.error(f"❗ Ошибка в фоновой задаче Modbus: {e}", exc_info=True)
        
        await asyncio.sleep(MODBUS_READ_INTERVAL_SECONDS)



# API-маршрут для чтения 
@router.get("/battery_status_new")
async def get_battery_status_from_cache():
    if redis_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis client not initialized."
        )

    cached_data = await redis_client.get(CACHE_KEY)
    if cached_data:
        try:
            status_data = json.loads(cached_data)
            logger.info("☑️ Данные о батарее получены из Redis.")
            return status_data
        except json.JSONDecodeError:
            logger.error("❌ Ошибка декодирования JSON из Redis.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Неверный формат данных в кеше."
            )
    else:
        logger.warning("⚠️ Данные о батарее отсутствуют в кеше или устарели. Попробуйте позже.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Данные о батарее временно недоступны или устарели. Повторите запрос через несколько секунд."
        )


"""

Я пока закомментировал вызов фоновой задачи на опрос в main.py, что бы не спамить ошибки

"""
