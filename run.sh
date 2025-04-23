#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Запуск Психолог-БОТ в Docker${NC}"

# Проверяем наличие файла .env
if [ ! -f .env ]; then
    echo -e "${RED}Ошибка: Файл .env не найден${NC}"
    echo -e "${YELLOW}Создаю .env из примера...${NC}"
    cp .env.example .env
    echo -e "${GREEN}Файл .env создан. Пожалуйста, отредактируйте его перед запуском.${NC}"
    exit 1
fi

# Проверяем Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Ошибка: Docker не установлен${NC}"
    echo -e "${YELLOW}Установите Docker перед запуском:${NC}"
    echo -e "https://docs.docker.com/get-docker/"
    exit 1
fi

# Запускаем контейнеры
echo -e "${YELLOW}Запуск контейнеров...${NC}"
docker compose up --build -d

# Проверяем статус
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Бот успешно запущен в Docker!${NC}"
    echo -e "${YELLOW}Логи бота:${NC} docker compose logs -f telegram_bot"
    echo -e "${YELLOW}Остановка:${NC} docker compose down"
else
    echo -e "${RED}Ошибка при запуске бота${NC}"
    exit 1
fi 