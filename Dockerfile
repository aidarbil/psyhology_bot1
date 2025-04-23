FROM python:3.11-slim

WORKDIR /app

# Установка необходимых зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Копирование файлов проекта
COPY requirements.txt .

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Переменные окружения
ENV TEST_MODE=false
ENV ENVIRONMENT=production

# Запуск бота
CMD ["python", "main.py"] 