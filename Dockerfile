FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Убедитесь, что файл log_config.yaml находится в директории /app
# Если он уже в директории, то эта команда не нужна
# RUN cp path/to/log_config.yaml /app/log_config.yaml

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-config", "log_config.yaml"]