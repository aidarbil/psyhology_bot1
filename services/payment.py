import uuid
from typing import Dict, Optional, Tuple
from datetime import datetime

from yookassa import Configuration, Payment as YooKassaPayment

import config
from database.models import Payment
from database import create_payment, update_payment_status, add_tokens, set_unlimited_status

# Инициализация библиотеки ЮKassa
Configuration.account_id = config.YUKASSA_SHOP_ID
Configuration.secret_key = config.YUKASSA_SECRET_KEY

class PaymentService:
    """Сервис для работы с платежной системой ЮKassa"""
    
    @staticmethod
    async def create_payment_link(user_id: int, tariff: str) -> Tuple[Optional[str], Optional[Payment]]:
        """Создать платежную ссылку для оплаты тарифа"""
        if tariff not in config.TARIFFS:
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
                "return_url": config.YUKASSA_RETURN_URL
            },
            "capture": True,
            "description": f"Оплата тарифа '{tariff}' ({tariff_data['description']})"
        }
        
        try:
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
            
            return response.confirmation.confirmation_url, payment
        except Exception as e:
            print(f"Ошибка при создании платежа: {str(e)}")
            return None, None
    
    @staticmethod
    async def process_payment_notification(payment_data: Dict) -> bool:
        """Обработать уведомление о статусе платежа от ЮKassa"""
        payment_id = payment_data.get('object', {}).get('id')
        status = payment_data.get('object', {}).get('status')
        
        if not payment_id or not status:
            return False
        
        # Обновляем статус платежа в базе
        payment = await update_payment_status(payment_id, status)
        
        if payment and status == 'succeeded':
            # Если платеж успешный, начисляем токены пользователю
            if payment.tokens == -1:  # Безлимитный тариф
                await set_unlimited_status(payment.user_id, True)
            else:
                await add_tokens(payment.user_id, payment.tokens)
            return True
        
        return False
    
    @staticmethod
    async def check_payment_status(payment_id: str) -> Optional[str]:
        """Проверить статус платежа"""
        try:
            response = YooKassaPayment.find_one(payment_id)
            return response.status
        except Exception as e:
            print(f"Ошибка при проверке статуса платежа: {str(e)}")
            return None

# Создаем экземпляр для использования в других модулях
payment_service = PaymentService() 