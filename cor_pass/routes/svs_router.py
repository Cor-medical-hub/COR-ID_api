from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
import os
import logging
from openslide import OpenSlide, OpenSlideUnsupportedFormatError
from io import BytesIO
import shutil
from cor_pass.services.auth import auth_service
from cor_pass.database.models import User

logger = logging.getLogger("svs_logger")
logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/svs", tags=["SVS"])

SVS_ROOT_DIR = "svs_users_data"
os.makedirs(SVS_ROOT_DIR, exist_ok=True)
DICOM_ROOT_DIR = "dicom_users_data"

@router.post("/upload")
async def upload_svs_files(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(auth_service.get_current_user)
):
    try:
        user_dir = os.path.join(SVS_ROOT_DIR, str(current_user.cor_id))
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)
        os.makedirs(user_dir, exist_ok=True)

        valid_svs = 0

        for file in files:
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext != '.svs':
                # Пропускаем не svs файлы
                continue

            temp_path = os.path.join(user_dir, file.filename)
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            try:
                OpenSlide(temp_path)  # проверяем что читается
                valid_svs += 1
            except OpenSlideUnsupportedFormatError:
                os.remove(temp_path)
                logger.error(f"Файл {file.filename} не является допустимым SVS-форматом.")

        if valid_svs == 0:
            shutil.rmtree(user_dir)
            raise HTTPException(status_code=400, detail="No valid SVS files found.")

        return {"message": f"Загружено {valid_svs} файлов SVS"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/svs_metadata")
def get_svs_metadata(current_user: User = Depends(auth_service.get_current_user)):
    user_slide_dir = os.path.join(DICOM_ROOT_DIR, str(current_user.cor_id), "slides")
    svs_files = [f for f in os.listdir(user_slide_dir) if f.lower().endswith('.svs')]

    if not svs_files:
        raise HTTPException(status_code=404, detail="No SVS files found.")

    svs_path = os.path.join(user_slide_dir, svs_files[0])

    try:
        slide = OpenSlide(svs_path)
        
        # Основные метаданные
        metadata = {
            "filename": svs_files[0],
            "dimensions": {
                "width": slide.dimensions[0],
                "height": slide.dimensions[1],
                "levels": slide.level_count
            },
            "basic_info": {
                "mpp": float(slide.properties.get('aperio.MPP', 0)),
                "magnification": slide.properties.get('aperio.AppMag', 'N/A'),
                "scan_date": slide.properties.get('aperio.Time', 'N/A'),
                "scanner": slide.properties.get('aperio.User', 'N/A'),
                "vendor": slide.properties.get('openslide.vendor', 'N/A')
            },
            "levels": [],
            "full_properties": {}
        }

        # Информация о уровнях
        for level in range(slide.level_count):
            metadata["levels"].append({
                "downsample": float(slide.properties.get(f'openslide.level[{level}].downsample', 0)),
                "width": int(slide.properties.get(f'openslide.level[{level}].width', 0)),
                "height": int(slide.properties.get(f'openslide.level[{level}].height', 0))
            })

        # Все свойства для детального просмотра
        metadata["full_properties"] = dict(slide.properties)

        return metadata

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview_svs")
def preview_svs(
    full: bool = Query(False),
    level: int = Query(0),  # Добавляем параметр уровня
    current_user: User = Depends(auth_service.get_current_user)
):
    user_slide_dir = os.path.join(DICOM_ROOT_DIR, str(current_user.cor_id), "slides")
    svs_files = [f for f in os.listdir(user_slide_dir) if f.lower().endswith('.svs')]

    if not svs_files:
        raise HTTPException(status_code=404, detail="No SVS found.")

    svs_path = os.path.join(user_slide_dir, svs_files[0])

    try:
        slide = OpenSlide(svs_path)
        
        if full:
            # Полное изображение в выбранном разрешении
            level = min(level, slide.level_count - 1)  # Проверяем, чтобы уровень был допустимым
            size = slide.level_dimensions[level]
            
            # Читаем регион целиком
            img = slide.read_region((0, 0), level, size)
            
            # Конвертируем в RGB, если нужно
            if img.mode == 'RGBA':
                img = img.convert('RGB')
        else:
            # Миниатюра
            size = (300, 300)
            img = slide.get_thumbnail(size)
        
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))






@router.get("/svs/{filename}")
def get_svs_slide(
    filename: str,
    current_user: User = Depends(auth_service.get_current_user)
):
    slide_path = os.path.join(DICOM_ROOT_DIR, str(current_user.cor_id), "slides", filename)
    
    if not os.path.isfile(slide_path):
        raise HTTPException(status_code=404, detail="Файл не найден")

    try:
        slide = OpenSlide(slide_path)

       
        img = slide.read_region((0, 0), 0, slide.dimensions)
        img = img.convert("RGB")

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return StreamingResponse(buffer, media_type="image/png")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при чтении SVS: {e}")

