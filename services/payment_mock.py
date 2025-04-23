import uuid
import logging
from typing import Dict, Optional, Any, Tuple

from config import TARIFFS, BOT_USERNAME
from database.models import Payment
from database import create_payment, update_payment_status, add_tokens, set_unlimited_status

logger = logging.getLogger(__name__)

class MockPaymentService:
    """
    Заглушка платежного сервиса для тестирования.
    Имитирует создание платежей и проверку их статуса без реальных транзакций.
    Автоматически начисляет токены пользователю при создании платежа.
    """
    
    def __init__(self):
        self.payments = {}  # Словарь для хранения информации о платежах
        logger.info("Инициализирована заглушка платежного сервиса")
    
    async def create_payment_link(self, user_id: int, tariff: str) -> Tuple[Optional[str], Optional[Payment]]:
        """
        Создает ссылку на оплату и автоматически начисляет токены.
        В тестовом режиме все платежи считаются успешными сразу.
        
        Args:
            user_id: ID пользователя
            tariff: ID тарифа
            
        Returns:
            Tuple[str, Payment]: URL для подтверждения и объект платежа
        """
        if tariff not in TARIFFS:
            return None, None
        
        tariff_data = TARIFFS[tariff]
        amount = tariff_data['price']
        tokens = tariff_data['tokens']
        
        # Генерируем уникальный ID платежа
        payment_id = str(uuid.uuid4())
        
        # Создаем запись платежа
        payment = Payment(
            payment_id=payment_id,
            user_id=user_id,
            tariff=tariff,
            amount=amount,
            tokens=tokens,
            status='pending'
        )
        
        # Сохраняем в базу
        await create_payment(payment)
        
        # Симулируем успешный платеж и сразу начисляем токены
        await self.check_payment_status(payment_id)
        
        logger.info(f"Создан тестовый платеж {payment_id} для пользователя {user_id}, тариф: {tariff}")
        
        # Возвращаем специальный URL, который будет перенаправлять обратно к боту
        return f"https://t.me/{BOT_USERNAME}", payment
    
    async def check_payment_status(self, payment_id: str) -> Optional[str]:
        """
        Проверяет статус платежа и начисляет токены пользователю.
        В тестовом режиме все платежи всегда успешны.
        
        Args:
            payment_id: ID платежа
            
        Returns:
            str: Статус платежа
        """
        # Обновляем статус платежа в базе
        payment = await update_payment_status(payment_id, 'succeeded')
        
        if payment:
            # Начисляем токены пользователю в зависимости от тарифа
            if payment.tokens == -1:  # Безлимитный тариф
                await set_unlimited_status(payment.user_id, True)
                logger.info(f"Пользователю {payment.user_id} активирован безлимитный тариф")
            else:
                await add_tokens(payment.user_id, payment.tokens)
                logger.info(f"Пользователю {payment.user_id} начислено {payment.tokens} токенов")
        
        return 'succeeded'
    
    async def process_payment_notification(self, payment_data: Dict) -> bool:
        """
        Обрабатывает уведомление от платежной системы.
        В тестовой версии всегда считаем платежи успешными.
        
        Args:
            payment_data: Данные уведомления
            
        Returns:
            bool: True, если обработка прошла успешно
        """
        payment_id = payment_data.get('object', {}).get('id')
        if not payment_id:
            return False
        
        await self.check_payment_status(payment_id)
        return True

# Создаем экземпляр сервиса
payment_service = MockPaymentService() 