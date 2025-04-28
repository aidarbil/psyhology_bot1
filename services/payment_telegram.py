import uuid
import logging
import traceback
import json
import sys
from typing import Dict, Optional, Tuple
from datetime import datetime

import config
from database.models import Payment
from database import create_payment, update_payment_status, add_tokens, set_unlimited_status

# Инициализация логирования
logger = logging.getLogger(__name__)
# Добавляем обработчик для вывода логов в консоль
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# Статус доступности Telegram Payments - сделаем его глобальным
global TELEGRAM_PAYMENTS_AVAILABLE
global TELEGRAM_PAYMENTS_INITIALIZED
TELEGRAM_PAYMENTS_AVAILABLE = True
TELEGRAM_PAYMENTS_INITIALIZED = False

# Получаем ключ провайдера из конфигурации
PROVIDER_TOKEN = config.TELEGRAM_PROVIDER_TOKEN

# Проверка наличия токена
if not PROVIDER_TOKEN:
    logger.error("❌ Отсутствует настройка TELEGRAM_PROVIDER_TOKEN")
    TELEGRAM_PAYMENTS_INITIALIZED = False
else:
    logger.info(f"✅ Telegram Payments инициализирован с токеном провайдера: {PROVIDER_TOKEN[:4]}...{PROVIDER_TOKEN[-4:] if len(PROVIDER_TOKEN) > 8 else ''}")
    TELEGRAM_PAYMENTS_INITIALIZED = True
    logger.debug(f"TELEGRAM_PAYMENTS_INITIALIZED установлен в {TELEGRAM_PAYMENTS_INITIALIZED}")

logger.info(f"Статус инициализации Telegram Payments: {TELEGRAM_PAYMENTS_INITIALIZED}")

class PaymentService:
    """Сервис для работы с платежной системой Telegram Payments"""
    
    # Добавляем атрибут класса для проверки в services/__init__.py
    TELEGRAM_PAYMENTS_INITIALIZED = TELEGRAM_PAYMENTS_INITIALIZED
    
    @staticmethod
    async def create_payment_link(user_id: int, tariff: str) -> Tuple[Optional[str], Optional[Payment]]:
        """Создать платеж через Telegram Payments"""
        global TELEGRAM_PAYMENTS_INITIALIZED
        
        logger.info(f"Проверка инициализации в create_payment_link: {TELEGRAM_PAYMENTS_INITIALIZED}")
        
        if not TELEGRAM_PAYMENTS_INITIALIZED:
            logger.error("❌ Невозможно создать платеж: Telegram Payments не инициализирован")
            return None, None
            
        if tariff not in config.TARIFFS:
            logger.error(f"❌ Тариф {tariff} не найден в конфигурации")
            logger.info(f"Доступные тарифы: {list(config.TARIFFS.keys())}")
            return None, None
        
        tariff_data = config.TARIFFS[tariff]
        amount = tariff_data['price']
        tokens = tariff_data['tokens']
        
        # Проверка корректности данных тарифа
        if not isinstance(amount, (int, float)) or amount <= 0:
            logger.error(f"❌ Некорректная сумма платежа: {amount}")
            return None, None
        
        payment_id = str(uuid.uuid4())
        
        # Для Telegram Payments не нужно создавать ссылку, а возвращать идентификатор тарифа и данные
        # Вместо URL, возвращаем tariff:payment_id, которое будет использоваться в функции show_payment_invoice
        
        logger.info(f"📊 Создание платежа для пользователя {user_id}, тариф: {tariff}")
        
        try:
            # Сохраняем данные о платеже в базу
            payment = Payment(
                payment_id=payment_id,
                user_id=user_id,
                tariff=tariff,
                amount=amount,
                tokens=tokens,
                status='pending',
                created_at=datetime.now().isoformat()
            )
            await create_payment(payment)
            
            logger.info(f"✅ Создан платеж {payment_id} для пользователя {user_id}")
            
            # Вместо URL, возвращаем строку формата "tariff:payment_id"
            return f"tariff:{tariff}:payment_id:{payment_id}", payment
        except Exception as e:
            # Подробное логирование ошибки
            logger.error(f"❌ Общая ошибка при создании платежа: {str(e)}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            logger.error(traceback.format_exc())
            return None, None
    
    @staticmethod
    async def process_successful_payment(user_id: int, telegram_payment_id: str, tariff: str) -> bool:
        """Обработать успешный платеж от Telegram"""
        logger.info(f"📩 Обработка успешного платежа от Telegram, пользователь: {user_id}, платеж: {telegram_payment_id}")
        
        try:
            if tariff not in config.TARIFFS:
                logger.error(f"❌ Тариф {tariff} не найден в конфигурации")
                return False
                
            tariff_data = config.TARIFFS[tariff]
            tokens = tariff_data['tokens']
            amount = tariff_data['price']
            
            # Создаем запись о платеже
            payment = Payment(
                payment_id=telegram_payment_id,
                user_id=user_id,
                tariff=tariff,
                amount=amount,
                tokens=tokens,
                status='succeeded',
                created_at=datetime.now().isoformat()
            )
            await create_payment(payment)
            
            # Начисляем токены пользователю
            if tokens == -1:  # Безлимитный тариф
                logger.info(f"🎉 Активация безлимитного тарифа для пользователя {user_id}")
                await set_unlimited_status(user_id, True)
            else:
                logger.info(f"🎉 Начисление {tokens} токенов пользователю {user_id}")
                await add_tokens(user_id, tokens)
            
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при обработке успешного платежа: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    @staticmethod
    async def check_payment_status(payment_id: str) -> Optional[str]:
        """Проверить статус платежа (заглушка, так как в Telegram Payments статус обрабатывается через pre_checkout_query и successful_payment)"""
        logger.info(f"🔍 Проверка статуса платежа {payment_id}")
        logger.info("В Telegram Payments статус обрабатывается автоматически через колбэки")
        
        return "unknown"  # В Telegram Payments мы не проверяем статус таким образом

# Создаем экземпляр для использования в других модулях
payment_service = PaymentService() 