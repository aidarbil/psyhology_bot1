from services.ai_agent import ai_agent
from services.mock_ai_agent import mock_ai_agent
from services.subscription import subscription_service
from services.vector_memory import vector_memory_service

import logging
import importlib.util
from config import TEST_MODE

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Проверяем наличие модуля YooKassa
has_yookassa = importlib.util.find_spec('yookassa') is not None

# Всегда используем настоящий AI агент вместо мока
ai_service = ai_agent
logger.info("🧠 Используется настоящий AI агент")

# Определяем, какой платежный сервис использовать
if TEST_MODE:
    logger.info("🧪 Запуск в тестовом режиме. Используется фиктивный платежный сервис.")
    from .payment_mock import payment_service
elif not has_yookassa:
    logger.info("💰 Модуль YooKassa не найден. Используется бесплатный режим.")
    from .payment_free import payment_service
else:
    try:
        logger.info("💰 Используется платежный сервис YooKassa.")
        from .payment_yookassa import payment_service
    except ImportError:
        logger.warning("Ошибка импорта YooKassa, переключаемся на бесплатный платежный сервис")
        from .payment_free import payment_service

__all__ = [
    'ai_agent',
    'mock_ai_agent',
    'ai_service',  # Теперь всегда настоящий AI агент
    'payment_service',  # Умный выбор между реальным, бесплатным и мок сервисом платежей
    'subscription_service',
    'vector_memory_service'  # Сервис векторной памяти
] 