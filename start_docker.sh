#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Запуск Docker Desktop на Mac${NC}"

# Проверяем установку Docker Desktop
if [ ! -d "/Applications/Docker.app" ]; then
    echo -e "${RED}Ошибка: Docker Desktop не установлен в /Applications/Docker.app${NC}"
    echo -e "${YELLOW}Установите Docker Desktop с сайта:${NC} https://www.docker.com/products/docker-desktop/"
    exit 1
fi

# Запускаем Docker Desktop
echo -e "${YELLOW}Запуск Docker Desktop...${NC}"
open -a Docker

# Ждем запуска демона Docker
echo -e "${YELLOW}Ожидание запуска Docker демона...${NC}"
max_attempts=60
attempt=0

while ! docker info >/dev/null 2>&1; do
    attempt=$((attempt+1))
    if [ $attempt -gt $max_attempts ]; then
        echo -e "${RED}Ошибка: Превышено время ожидания запуска Docker демона${NC}"
        echo -e "${YELLOW}Проверьте, запущен ли Docker Desktop и повторите попытку${NC}"
        exit 1
    fi
    echo -e "${YELLOW}Ожидание запуска Docker демона... ($attempt/$max_attempts)${NC}"
    sleep 2
done

echo -e "${GREEN}Docker демон успешно запущен!${NC}"
echo -e "${YELLOW}Теперь вы можете запустить бота с помощью:${NC} ./run.sh" 