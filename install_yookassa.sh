#!/bin/bash

# Скрипт для установки библиотеки yookassa

# Путь к директории бота (измените на вашем сервере)
BOT_DIR="/root/bots/psycholog_bot"

# Перейти в директорию бота
cd "$BOT_DIR"

# Проверка наличия виртуального окружения
if [ -d "venv" ]; then
    echo "Виртуальное окружение найдено, активируем..."
    source venv/bin/activate
else
    echo "Виртуальное окружение не найдено, создаем новое..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Установка или обновление библиотеки yookassa
pip install yookassa==3.0.0

# Проверка успешности установки
if python -c "import yookassa" &> /dev/null; then
    echo "✅ Библиотека yookassa успешно установлена!"
else
    echo "❌ Ошибка: не удалось установить библиотеку yookassa"
    exit 1
fi

# Обновление TEST_MODE в конфигурации
ENV_FILE="$BOT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    if grep -q "TEST_MODE" "$ENV_FILE"; then
        # Обновляем TEST_MODE
        sed -i 's/^TEST_MODE=.*/TEST_MODE=false/' "$ENV_FILE"
    else
        # Добавляем TEST_MODE
        echo "TEST_MODE=false" >> "$ENV_FILE"
    fi
    echo "✅ Настройка TEST_MODE обновлена"
fi

# Перезапуск бота
echo "Перезапускаем бота..."
systemctl restart psycholog-bot

echo "✅ Готово! Проверьте работу бота через Telegram." 