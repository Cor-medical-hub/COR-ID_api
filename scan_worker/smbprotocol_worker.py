import asyncio
import enum
import socket
import os
import re
import sys
from datetime import datetime, timedelta
from smb.SMBConnection import SMBConnection
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.future import select
from loguru import logger
from openslide import OpenSlide
from io import BytesIO
import tempfile
import time
from cor_pass.database.models import Cassette, Glass, Sample 
from cor_pass.config.config import settings
import enum

SMB_USER = settings.smb_user
SMB_PASS = settings.smb_pass
SMB_SERVER_IP = settings.smb_server_ip
SMB_SHARE = settings.smb_share
REMOTE_NAME = settings.remote_name
DATABASE_URL = settings.sqlalchemy_database_url
SCAN_INTERVAL_SECONDS = settings.scan_interval_seconds
BASE_PATH = settings.base_path


engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class StainingType(enum.Enum):
    HE = "H&E"
    ALCIAN_PAS = "Alcian PAS"
    CONGO_RED = "Congo red"
    MASSON_TRICHROME = "Masson Trichrome"
    VAN_GIESON = "van Gieson"
    ZIEHL_NEELSEN = "Ziehl Neelsen"
    WARTHIN_STARRY_SILVER = "Warthin-Starry Silver"
    GROCOTT_METHENAMINE_SILVER = "Grocott's Methenamine Silver"
    TOLUIDINE_BLUE = "Toluidine Blue"
    PERLS_PRUSSIAN_BLUE = "Perls Prussian Blue"
    PAMS = "PAMS"
    PICROSIRIUS = "Picrosirius"
    SIRIUS_RED = "Sirius red"
    THIOFLAVIN_T = "Thioflavin T"
    TRICHROME_AFOG = "Trichrome AFOG"
    VON_KOSSA = "von Kossa"
    GIEMSA = "Giemsa"
    OTHAR = "Othar"

    def abbr(self) -> str:
        overrides = {
            "H&E": "H&E",
            "PAMS": "PAM",
            "Othar": "O",
        }
        if self.value in overrides:
            return overrides[self.value]
        parts = self.value.replace("-", " ").replace("'", "").split()
        abbr = "".join(word[0].upper() for word in parts)
        return abbr[:3]
STAINING_ABBREVIATIONS = [st.abbr() for st in StainingType]


filename_pattern = re.compile(
    r"^(?P<case_code>S\d{2}[RBECXSAY]\d{5})"
    r"(?P<cassette>[A-Z]\d)"
    r"(?P<hospital>[A-Z]{2})"
    r"(?P<sample>[A-Z])"
    r"L(?P<glass_number>\d+)"
    r"(?P<staining>" + "|".join(STAINING_ABBREVIATIONS) + ")"
    r"(?P<cor_id>[A-Z0-9]+(?:-[A-Z0-9]+)?)"
    r"\d{4}-\d{2}-\d{2}_\d{2}_\d{2}_\d{2}"
    r"\.svs$"
)

def parse_filename(filename):
    base = os.path.basename(filename)

    # Если расширение не .svs, просто пропускаем
    if not base.lower().endswith(".svs"):
        return None

    m = filename_pattern.match(base)
    if not m:
        logger.debug(f"Файл {base} не соответствует регулярному выражению: {filename_pattern.pattern}")
        return None

    return {
        "case_code": m.group("case_code"),
        "cassette": m.group("cassette"),
        "hospital": m.group("hospital"),
        "sample": m.group("sample"),
        "glass_number": int(m.group("glass_number")),
        "staining": m.group("staining"),
        "cor_id": m.group("cor_id")
    }

async def fetch_file_from_smb(path: str) -> str:
    loop = asyncio.get_running_loop()

    def _read_file():
        conn = SMBConnection(
            SMB_USER,
            SMB_PASS,
            my_name=socket.gethostname(),
            remote_name=REMOTE_NAME,
            use_ntlm_v2=True,
            is_direct_tcp=True,
        )
        if not conn.connect(SMB_SERVER_IP, 445):
            raise RuntimeError("Failed to connect to SMB server")

        prefix = f"\\\\{SMB_SERVER_IP}\\{SMB_SHARE}\\"
        if path.startswith(prefix):
            relative_path = path[len(prefix):].strip("/\\")
        else:
            relative_path = path.strip("/\\")

        logger.debug(f"relative_path: {relative_path}")

        try:
            file_info = conn.getAttributes(SMB_SHARE, relative_path)
            logger.debug(f"file_info: {file_info}, type: {type(file_info)}")
            filesize = getattr(file_info, "file_size", None)
            if filesize is None:
                raise ValueError("Cannot get filesize from SMB file_info")
            logger.debug(f"filesize: {filesize}, type: {type(filesize)}")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".svs") as temp_file:
                start_time = time.time()
                conn.retrieveFile(SMB_SHARE, relative_path, temp_file)
                temp_file.flush()
                logger.debug(f"Time to retrieve file to disk: {time.time() - start_time} seconds")

                temp_file.seek(0, os.SEEK_END)
                file_size = temp_file.tell()
                logger.debug(f"Total bytes written to temp file: {file_size}")
                if file_size != filesize:
                    raise RuntimeError(f"Expected {filesize} bytes, but wrote {file_size} bytes")
                
                return temp_file.name
        finally:
            conn.close()

    return await loop.run_in_executor(None, _read_file)

async def save_file_to_smb(data: BytesIO, path: str) -> None:
    loop = asyncio.get_running_loop()

    def _write_file():
        conn = SMBConnection(
            SMB_USER,
            SMB_PASS,
            my_name=socket.gethostname(),
            remote_name=REMOTE_NAME,
            use_ntlm_v2=True,
            is_direct_tcp=True,
        )
        if not conn.connect(SMB_SERVER_IP, 445):
            raise RuntimeError("Failed to connect to SMB server")

        prefix = f"\\\\{SMB_SERVER_IP}\\{SMB_SHARE}\\"
        if path.startswith(prefix):
            relative_path = path[len(prefix):].strip("/\\")
        else:
            relative_path = path.strip("/\\")

        logger.debug(f"Saving file to SMB: {relative_path}")
        try:
            data.seek(0)
            conn.storeFile(SMB_SHARE, relative_path, data)
            logger.debug(f"Successfully saved file to {relative_path}")
        finally:
            conn.close()

    await loop.run_in_executor(None, _write_file)

async def save_file_to_smb_manual(data: BytesIO, path: str) -> None:
    loop = asyncio.get_running_loop()

    def _write_file():
        conn = SMBConnection(
            SMB_USER,
            SMB_PASS,
            my_name=socket.gethostname(),
            remote_name=REMOTE_NAME,
            use_ntlm_v2=True,
            is_direct_tcp=True,
        )
        if not conn.connect(SMB_SERVER_IP, 445):
            raise RuntimeError("Failed to connect to SMB server")

        prefix = f"\\\\{SMB_SERVER_IP}\\{SMB_SHARE}\\"
        if path.startswith(prefix):
            relative_path = path[len(prefix):].strip("/\\")
        else:
            relative_path = path.strip("/\\")

        dir_path, filename = os.path.split(relative_path)

        # создаём директории если их нет
        if dir_path:
            parts = dir_path.replace("\\", "/").split("/")
            current = ""
            for part in parts:
                current = f"{current}/{part}" if current else part
                try:
                    conn.createDirectory(SMB_SHARE, current)
                except Exception:
                    # игнорируем, если уже есть
                    pass

        try:
            data.seek(0)
            conn.storeFile(SMB_SHARE, relative_path, data)
        finally:
            conn.close()

    await loop.run_in_executor(None, _write_file)


def list_files_in_folder(conn, share, folder_path):
    files = []
    logger.debug(f"Сканируем папку: {share}/{folder_path}")
    try:
        entries = conn.listPath(share, folder_path)
        folder_contents = [entry.filename for entry in entries if entry.filename not in ['.', '..']]
        logger.info(f"Содержимое папки {share}/{folder_path}: {folder_contents}")
        for entry in entries:
            if entry.filename in [".", ".."]:
                continue
            if not entry.isDirectory:
                files.append(f"{folder_path}/{entry.filename}")
    except Exception as e:
        logger.error(f"Ошибка при сканировании папки {share}/{folder_path}: {str(e)}")
    return files

def list_files_for_current_date(conn, share, base_path, include_yesterday=True):
    files = []
    try:
        base_path_clean = base_path.lstrip("/")
        entries = conn.listPath(share, base_path_clean)
        date_folders = [entry.filename for entry in entries if entry.isDirectory and entry.filename not in ['.', '..']]
        # logger.info(f"Доступные папки с датами в {share}/{base_path_clean}: {date_folders}")
    except Exception as e:
        logger.error(f"Ошибка при получении списка папок в {share}/{base_path_clean}: {str(e)}")
        return files

    current_date = datetime.now().strftime("%Y-%m-%d")
    if current_date in date_folders:
        files.extend(list_files_in_folder(conn, share, f"{base_path}/{current_date}".lstrip("/")))

    if include_yesterday:
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if yesterday in date_folders:
            files.extend(list_files_in_folder(conn, share, f"{base_path}/{yesterday}".lstrip("/")))

    for folder in date_folders:
        if folder not in [current_date, yesterday, 'LenaThyroidChile', 'test']:
            files.extend(list_files_in_folder(conn, share, f"{base_path}/{folder}".lstrip("/")))

    return files

async def update_scan_urls():
    def sync_scan():
        conn = SMBConnection(
            SMB_USER,
            SMB_PASS,
            my_name=socket.gethostname(),
            remote_name=REMOTE_NAME,
            use_ntlm_v2=True,
            is_direct_tcp=True
        )
        logger.debug(f"Попытка подключения к SMB-серверу: {SMB_SERVER_IP}, share: {SMB_SHARE}, remote_name: {REMOTE_NAME}")
        connected = conn.connect(SMB_SERVER_IP, 445)
        if not connected:
            raise RuntimeError("Не удалось подключиться к SMB-серверу")
        logger.info("Успешно подключились к SMB-серверу")

        try:
            shares = conn.listShares()
        except Exception as e:
            logger.error(f"Ошибка при получении списка шар: {str(e)}")

        try:
            root_entries = conn.listPath(SMB_SHARE, "")
        except Exception as e:
            logger.error(f"Ошибка при сканировании корня шары {SMB_SHARE}: {str(e)}")

        path_parts = BASE_PATH.lstrip("/").split("/")
        current_path = ""
        for part in path_parts:
            current_path = f"{current_path}/{part}".lstrip("/")
            logger.debug(f"Проверка папки: {SMB_SHARE}/{current_path}")
            try:
                entries = conn.listPath(SMB_SHARE, current_path)
                logger.info(f"Содержимое папки {SMB_SHARE}/{current_path}: {[entry.filename for entry in entries if entry.filename not in ['.', '..']]}")
                for entry in entries:
                    if entry.filename in [".", ".."]:
                        continue
                    logger.debug(f"Права для {entry.filename}: isDirectory={entry.isDirectory}, read={entry.isReadOnly is False}")
            except Exception as e:
                logger.error(f"Ошибка при сканировании папки {SMB_SHARE}/{current_path}: {str(e)}")
                if "Unable to open directory" in str(e):
                    logger.warning(f"Папка {SMB_SHARE}/{current_path} не существует или недоступна")

        try:
            scanner_entries = conn.listPath("scanner", "")
        except Exception as e:
            logger.error(f"Ошибка при сканировании корня шары scanner: {str(e)}")

        files = list_files_for_current_date(conn, SMB_SHARE, BASE_PATH, include_yesterday=True)
        conn.close()
        return files

    smb_files = await asyncio.to_thread(sync_scan)
    for file in smb_files:
        logger.debug(f"Обнаружен файл: {file}")

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(Glass)
                .options(
                    joinedload(Glass.cassette)
                    .joinedload(Cassette.sample)
                    .joinedload(Sample.case)
                )
            )
            glasses = result.scalars().all()
        except Exception as e:
            logger.error(f"Ошибка при выполнении SQL-запроса: {str(e)}")
            raise

        updated = 0
        skipped = 0
        for glass in glasses:
            if glass.scan_url and glass.preview_url:
                skipped += 1
                logger.debug(f"[SKIP] Стекло {glass.id} уже имеет scan_url: {glass.scan_url} и preview_url: {glass.preview_url}")
                continue

            case_code = glass.cassette.sample.case.case_code
            sample_number = glass.cassette.sample.sample_number
            cassette_number = glass.cassette.cassette_number
            glass_number = glass.glass_number
            staining = glass.staining.abbr() if glass.staining else None
            cor_id = glass.cassette.sample.case.patient_id

            logger.debug(f"Проверяем стекло {glass.id}: case_code={case_code}, sample={sample_number}, cassette={cassette_number}, glass_number={glass_number}, staining={staining}, cor_id={cor_id}")

            for file in smb_files:
                info = parse_filename(file)
                if not info:
                    continue

                # Учитываем, что cassette_number в базе данных может быть длиннее, но нам нужна только последняя буква + цифра
                cassette_last = cassette_number[-2:] if cassette_number and len(cassette_number) >= 2 else None

                logger.debug(f"Сравниваем с файлом {file}: {info}")

                if (
                    info["case_code"] == case_code and
                    info["sample"] == sample_number and
                    info["cassette"] == cassette_last and
                    info["glass_number"] == glass_number and
                    info["staining"] == staining and
                    info["cor_id"] == cor_id
                ):
                    if file.lower().endswith('.svs'):
                        scan_url = f"\\\\{SMB_SERVER_IP}\\{SMB_SHARE}\\{file}"
                        glass.scan_url = scan_url
                        logger.debug(f"[OK] Стекло {glass.id} → scan_url: {scan_url}")

                        if not glass.preview_url:
                            try:
                                temp_file_path = await fetch_file_from_smb(scan_url)
                                try:
                                    start_time = time.time()
                                    slide = OpenSlide(temp_file_path)
                                    logger.debug(f"Time to open slide: {time.time() - start_time} seconds")
                                    preview = slide.get_thumbnail((512, 512))
                                    buf = BytesIO()
                                    preview.save(buf, format="PNG")
                                    buf.seek(0)
                                    preview_path = scan_url.replace('.svs', '.png').replace('.SVS', '.png')
                                    await save_file_to_smb(buf, preview_path)
                                    glass.preview_url = preview_path
                                    logger.debug(f"[OK] Стекло {glass.id} → preview_url: {preview_path}")
                                finally:
                                    if os.path.exists(temp_file_path):
                                        os.unlink(temp_file_path)
                                        logger.debug(f"Temporary file {temp_file_path} deleted")
                            except Exception as e:
                                logger.error(f"Ошибка при генерации или сохранении превью для {file}: {str(e)}")
                                continue

                        updated += 1
                        break

        await session.commit()
        # logger.info(f"Обновлено {updated} записей, пропущено {skipped} записей")

async def main():
    while True:
        try:
            await update_scan_urls()
        except Exception as e:
            logger.exception(f"Ошибка в update_scan_urls: {e}")
        await asyncio.sleep(SCAN_INTERVAL_SECONDS)
        logger.debug("Мониторим файлы")

if __name__ == "__main__":
    if settings.app_env in ["development", "lab-neuro"]:
        if settings.smb_enabled:
            asyncio.run(main())