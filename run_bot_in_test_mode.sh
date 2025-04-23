#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Запуск Психолог-БОТ в тестовом режиме${NC}"

# Включаем тестовый режим
export TEST_MODE=true

# Создаем виртуальное окружение, если его нет
if [ ! -d "venv_test" ]; then
    echo -e "${YELLOW}Создаем виртуальное окружение для тестов...${NC}"
    python3 -m venv venv_test
fi

# Активируем виртуальное окружение
echo -e "${YELLOW}Активируем виртуальное окружение...${NC}"
source venv_test/bin/activate

# Устанавливаем зависимости
echo -e "${YELLOW}Устанавливаем зависимости...${NC}"
pip install -r requirements_test.txt

# Проверяем, запущена ли MongoDB
if ! pgrep -x mongod > /dev/null; then
    echo -e "${YELLOW}Запускаем MongoDB...${NC}"
    brew services start mongodb-community || echo -e "${RED}Не удалось запустить MongoDB${NC}"
else
    echo -e "${GREEN}MongoDB уже запущена${NC}"
fi

# Запускаем бота
echo -e "${GREEN}Запускаем бота в тестовом режиме...${NC}"
python3 main.py

# Деактивируем виртуальное окружение после завершения
deactivate
echo -e "${YELLOW}Виртуальное окружение деактивировано${NC}" 