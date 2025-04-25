import uuid
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime

from yookassa import Configuration, Payment as YooKassaPayment

import config
from database.models import Payment
from database import create_payment, update_payment_status, add_tokens, set_unlimited_status

# Инициализация логирования
logger = logging.getLogger(__name__)

# Инициализация библиотеки ЮKassa с тестовыми данными
# Тестовый shopId и секретный ключ для проведения тестовых платежей
Configuration.account_id = "381764678"
Configuration.secret_key = "TEST:121476"

# URL для возврата после платежа
RETURN_URL = "https://t.me/psychologybilalov_bot"

class PaymentService:
    """Сервис для работы с платежной системой ЮKassa (тестовый режим)"""
    
    @staticmethod
    async def create_payment_link(user_id: int, tariff: str) -> Tuple[Optional[str], Optional[Payment]]:
        """Создать платежную ссылку для оплаты тарифа"""
        if tariff not in config.TARIFFS:
            logger.error(f"Тариф {tariff} не найден")
            return None, None
        
        tariff_data = config.TARIFFS[tariff]
        amount = tariff_data['price']
        tokens = tariff_data['tokens']
        
        idempotence_key = str(uuid.uuid4())
        payment_data = {
            "amount": {
                "value": amount,
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": RETURN_URL
            },
            "capture": True,
            "description": f"Оплата тарифа '{tariff}' ({tariff_data['description']})"
        }
        
        try:
            logger.info(f"Создание тестового платежа для пользователя {user_id}, тариф: {tariff}")
            response = YooKassaPayment.create(payment_data, idempotence_key)
            
            # Сохраняем данные о платеже в базу
            payment = Payment(
                payment_id=response.id,
                user_id=user_id,
                tariff=tariff,
                amount=amount,
                tokens=tokens,
                status='pending'
            )
            await create_payment(payment)
            
            logger.info(f"Создан тестовый платеж {response.id} для пользователя {user_id}")
            return response.confirmation.confirmation_url, payment
        except Exception as e:
            logger.error(f"Ошибка при создании платежа: {str(e)}")
            return None, None
    
    @staticmethod
    async def process_payment_notification(payment_data: Dict) -> bool:
        """Обработать уведомление о статусе платежа от ЮKassa"""
        payment_id = payment_data.get('object', {}).get('id')
        status = payment_data.get('object', {}).get('status')
        
        if not payment_id or not status:
            logger.warning("Получено некорректное уведомление о платеже")
            return False
        
        logger.info(f"Обработка уведомления о платеже {payment_id}, статус: {status}")
        
        # Обновляем статус платежа в базе
        payment = await update_payment_status(payment_id, status)
        
        if payment and status == 'succeeded':
            # Если платеж успешный, начисляем токены пользователю
            if payment.tokens == -1:  # Безлимитный тариф
                logger.info(f"Активация безлимитного тарифа для пользователя {payment.user_id}")
                await set_unlimited_status(payment.user_id, True)
            else:
                logger.info(f"Начисление {payment.tokens} токенов пользователю {payment.user_id}")
                await add_tokens(payment.user_id, payment.tokens)
            return True
        
        return False
    
    @staticmethod
    async def check_payment_status(payment_id: str) -> Optional[str]:
        """Проверить статус платежа"""
        try:
            logger.info(f"Проверка статуса платежа {payment_id}")
            response = YooKassaPayment.find_one(payment_id)
            logger.info(f"Получен статус платежа {payment_id}: {response.status}")
            return response.status
        except Exception as e:
            logger.error(f"Ошибка при проверке статуса платежа {payment_id}: {str(e)}")
            return None

# Создаем экземпляр для использования в других модулях
payment_service = PaymentService() 