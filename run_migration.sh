#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Запуск миграции базы данных${NC}"

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Ошибка: Python 3 не установлен${NC}"
    exit 1
fi

# Запускаем миграцию
echo -e "${YELLOW}Выполнение миграции...${NC}"
python3 database/migration.py

# Проверяем статус
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Миграция успешно завершена!${NC}"
else
    echo -e "${RED}Ошибка при выполнении миграции${NC}"
    exit 1
fi 