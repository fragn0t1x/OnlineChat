# backend/Dockerfile
FROM python:3.12-slim

# Установка системных зависимостей (включая pg_isready)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Устанавливаем Python-зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

EXPOSE 8000

CMD ["python", "app/main.py"]