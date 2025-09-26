import os
import shutil
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_rmtree(path: str):
    """
    Надёжно удаляет директорию и её содержимое.
    Работает на CIFS/SMB шарах, игнорируя ошибки удаления отдельных файлов.
    """
    if not os.path.exists(path):
        logger.info(f"Папка {path} не существует, пропускаем")
        return

    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            file_path = os.path.join(root, name)
            try:
                os.unlink(file_path)
                logger.debug(f"Файл удалён: {file_path}")
            except Exception as e:
                logger.warning(f"Не удалось удалить файл {file_path}: {e}")
        for name in dirs:
            dir_path = os.path.join(root, name)
            try:
                os.rmdir(dir_path)
                logger.debug(f"Директория удалена: {dir_path}")
            except Exception as e:
                logger.warning(f"Не удалось удалить директорию {dir_path}: {e}")

    try:
        os.rmdir(path)
        logger.info(f"Корневая папка {path} удалена")
    except Exception as e:
        logger.warning(f"Не удалось удалить корневую папку {path}: {e}")


if __name__ == "__main__":
    dicom_dir = "/app/dicom_users_data"
    safe_rmtree(dicom_dir)