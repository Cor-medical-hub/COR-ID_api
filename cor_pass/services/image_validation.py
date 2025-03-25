from fastapi import UploadFile, HTTPException
import imghdr  # Встроенный модуль для проверки типа изображения

ALLOWED_IMAGE_TYPES = {"jpeg", "png", "gif", "jpg"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

async def validate_image_file(file: UploadFile):
    # Проверка размера файла
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE//(1024*1024)}MB"
        )
    
    # Проверка, что файл вообще является изображением
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=415,
            detail="Файл должен быть изображением"
        )
    


    # Читаем первые 32 байта для определения типа файла
    file_header = await file.read(32)
    await file.seek(0)  # Возвращаем указатель в начало файла
    # Определяем тип изображения
    image_type = imghdr.what(None, h=file_header)
    if image_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Неподдерживаемый тип изображения. Разрешены: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )
    
    # Проверка по расширению файла (дополнительная проверка)
    file_ext = file.filename.split('.')[-1].lower()
    print(file_ext)
    if file_ext not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Неподдерживаемый формат файла - {file_ext}. Разрешены: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )
    
    return file