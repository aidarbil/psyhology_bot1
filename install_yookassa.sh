#!/bin/bash

# Скрипт для установки библиотеки yookassa

# Путь к директории бота (измените на вашем сервере)
BOT_DIR="/root/bots/psycholog_bot"

# Вывод отладочной информации
echo "======================"
echo "Установка ЮKassa"
echo "======================"
echo "Текущая директория: $(pwd)"
echo "Целевая директория: $BOT_DIR"

# Перейти в директорию бота
cd "$BOT_DIR"
echo "Текущая директория после перехода: $(pwd)"

# Проверка наличия Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
    echo "✅ Python3 найден: $(python3 --version)"
else
    echo "❌ Python3 не установлен!"
    exit 1
fi

# Проверка наличия pip
if $PYTHON_CMD -m pip --version &> /dev/null; then
    echo "✅ Pip найден: $($PYTHON_CMD -m pip --version)"
else
    echo "❌ Pip не установлен. Устанавливаем..."
    apt-get update && apt-get install -y python3-pip
fi

# Проверка наличия виртуального окружения
if [ -d "venv" ]; then
    echo "✅ Виртуальное окружение найдено, активируем..."
    source venv/bin/activate
    echo "Версия Python в виртуальном окружении: $(python --version)"
else
    echo "⚠️ Виртуальное окружение не найдено, создаем новое..."
    $PYTHON_CMD -m venv venv
    source venv/bin/activate
    echo "Версия Python в новом виртуальном окружении: $(python --version)"
fi

# Обновляем pip в виртуальном окружении
echo "Обновляем pip..."
pip install --upgrade pip
echo "Версия pip после обновления: $(pip --version)"

# Удаляем существующую библиотеку yookassa если она установлена
if pip freeze | grep -q yookassa; then
    echo "Удаляем предыдущую версию yookassa..."
    pip uninstall -y yookassa
fi

# Установка библиотеки yookassa
echo "Устанавливаем yookassa версии 3.0.0..."
pip install yookassa==3.0.0

# Проверка успешности установки
if python -c "import yookassa; print(f'Версия yookassa: {yookassa.__version__}')" 2>/dev/null; then
    echo "✅ Библиотека yookassa успешно установлена!"
    # Тестовая проверка импорта всех необходимых модулей
    python -c "from yookassa import Configuration, Payment; print('✅ Все необходимые компоненты yookassa доступны')" 2>/dev/null
else
    echo "❌ Ошибка: не удалось установить библиотеку yookassa"
    echo "Пробуем установить с дополнительными зависимостями..."
    pip install requests
    pip install yookassa==3.0.0
    
    if python -c "import yookassa; print(f'Версия yookassa: {yookassa.__version__}')" 2>/dev/null; then
        echo "✅ Библиотека yookassa успешно установлена со второй попытки!"
    else
        echo "❌ Ошибка: не удалось установить библиотеку yookassa"
        exit 1
    fi
fi

# Обновление TEST_MODE в конфигурации
ENV_FILE="$BOT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    echo "Файл .env найден, обновляем настройки..."
    if grep -q "TEST_MODE" "$ENV_FILE"; then
        # Обновляем TEST_MODE
        sed -i 's/^TEST_MODE=.*/TEST_MODE=false/' "$ENV_FILE"
        echo "✅ Настройка TEST_MODE обновлена на false"
    else
        # Добавляем TEST_MODE
        echo "TEST_MODE=false" >> "$ENV_FILE"
        echo "✅ Настройка TEST_MODE добавлена"
    fi
    
    # Проверяем и добавляем настройки ЮKassa если их нет
    if ! grep -q "YUKASSA_SHOP_ID" "$ENV_FILE"; then
        echo "YUKASSA_SHOP_ID=381764678" >> "$ENV_FILE"
        echo "✅ YUKASSA_SHOP_ID добавлен"
    fi
    
    if ! grep -q "YUKASSA_SECRET_KEY" "$ENV_FILE"; then
        echo "YUKASSA_SECRET_KEY=TEST:121476" >> "$ENV_FILE"
        echo "✅ YUKASSA_SECRET_KEY добавлен"
    fi
    
    if ! grep -q "YUKASSA_RETURN_URL" "$ENV_FILE"; then
        echo "YUKASSA_RETURN_URL=https://t.me/psychologybilalov_bot" >> "$ENV_FILE"
        echo "✅ YUKASSA_RETURN_URL добавлен"
    fi
else
    echo "⚠️ Файл .env не найден, создаем..."
    cat > "$ENV_FILE" << EOF
# Тестовые платежи ЮKassa
YUKASSA_SHOP_ID=381764678
YUKASSA_SECRET_KEY=TEST:121476
YUKASSA_RETURN_URL=https://t.me/psychologybilalov_bot
TEST_MODE=false
EOF
    echo "✅ Файл .env создан с настройками ЮKassa"
fi

# Вывод списка установленных пакетов
echo "Список установленных пакетов:"
pip freeze

# Перезапуск бота
echo "Перезапускаем бота..."
systemctl restart psycholog-bot

# Проверяем статус бота
echo "Проверяем статус бота..."
systemctl status psycholog-bot --no-pager

echo ""
echo "✅ Готово! Проверьте работу бота через Telegram."
echo "Для проверки логов используйте команду:"
echo "journalctl -u psycholog-bot -n 50 --no-pager" 