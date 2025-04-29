import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Telegram Bot
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME', 'tarodevruslanbot')  # Имя пользователя бота
CHANNEL_ID = os.getenv('CHANNEL_ID')
CHANNEL_URL = os.getenv('CHANNEL_URL')
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(',')))

# Telegram Payments
# Токен провайдера для тестовых платежей Telegram
# Формат: 123456789:TEST:XXXXXXXXXX
TELEGRAM_PROVIDER_TOKEN = os.getenv('TELEGRAM_PROVIDER_TOKEN', '381764678:TEST:121476').strip()

# MongoDB
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
DB_NAME = os.getenv('DB_NAME', 'psycholog_bot')

# AI Agent
AI_AGENT_URL = os.getenv('AI_AGENT_URL', 'https://api.bilalov.ai/api/message')
AI_AGENT_ID = os.getenv('AI_AGENT_ID', 'ed3ca89f25ba41b1a5c6')

# Токены
FREE_TOKENS = 50  # Количество бесплатных токенов за подписку
TOKENS_PER_MESSAGE = 10  # Стоимость одного сообщения в токенах
REFERRAL_BONUS_TOKENS = 10  # Бонусные токены за приглашенного пользователя

# Тарифы
TARIFFS = {
    'small': {'tokens': 50, 'price': 99, 'description': '5 вопросов'},
    'medium': {'tokens': 100, 'price': 150, 'description': '10 вопросов'},
    'large': {'tokens': 500, 'price': 490, 'description': '50 вопросов'},
    'unlimited': {'tokens': -1, 'price': 990, 'description': 'Безлимитное количество вопросов'}
}

# ЮKassa
YUKASSA_SHOP_ID = os.getenv('YUKASSA_SHOP_ID')
YUKASSA_SECRET_KEY = os.getenv('YUKASSA_SECRET_KEY')
YUKASSA_RETURN_URL = os.getenv('YUKASSA_RETURN_URL', 'https://t.me/your_bot_name') 

# Режим тестирования
TEST_MODE = os.getenv('TEST_MODE', 'false').lower() == 'true' 