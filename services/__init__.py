from services.ai_agent import ai_agent
from services.mock_ai_agent import mock_ai_agent
from services.subscription import subscription_service
from services.vector_memory import vector_memory_service

import logging
import sys
import importlib.util
from config import TEST_MODE
from utils.logging_config import setup_logging, get_logger

# Инициализируем логирование
setup_logging(
    log_level='INFO',
    log_file='logs/services.log',
    max_bytes=10 * 1024 * 1024,  # 10 MB
    backup_count=5
)
logger = get_logger(__name__)

# Проверяем наличие модуля YooKassa более надежным способом
try:
    import yookassa
    has_yookassa = True
    logger.info(f"✅ YooKassa найдена, версия: {yookassa.__version__}")
except ImportError as e:
    has_yookassa = False
    logger.error(f"❌ Ошибка импорта YooKassa: {str(e)}")

# Всегда используем настоящий AI агент вместо мока
ai_service = ai_agent
logger.info("🧠 Используется настоящий AI агент")

# Определяем, какой платежный сервис использовать
if TEST_MODE:
    logger.info("🧪 Запуск в тестовом режиме. Используется фиктивный платежный сервис.")
    from .payment_mock import payment_service
elif not has_yookassa:
    logger.info("💰 YooKassa не найдена. Используется бесплатный режим.")
    from .payment_free import payment_service
else:
    try:
        logger.info("💰 Используется платежный сервис YooKassa.")
        from .payment_yookassa import payment_service
        # Проверка инициализации
        if not getattr(payment_service, 'YOOKASSA_INITIALIZED', False):
            logger.warning("⚠️ YooKassa не инициализирована, переключаемся на бесплатный платежный сервис")
            from .payment_free import payment_service
    except ImportError as e:
        logger.warning(f"❌ Ошибка импорта payment_yookassa: {str(e)}")
        logger.warning("⚠️ Переключаемся на бесплатный платежный сервис")
        from .payment_free import payment_service
    except Exception as e:
        logger.error(f"❌ Непредвиденная ошибка при импорте YooKassa: {str(e)}")
        logger.warning("⚠️ Переключаемся на бесплатный платежный сервис")
        from .payment_free import payment_service

__all__ = [
    'ai_agent',
    'mock_ai_agent',
    'ai_service',  # Теперь всегда настоящий AI агент
    'payment_service',  # Умный выбор между реальным, бесплатным и мок сервисом платежей
    'subscription_service',
    'vector_memory_service'  # Сервис векторной памяти
] 