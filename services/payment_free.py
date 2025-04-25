import uuid
import logging
import time
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timedelta

from config import TARIFFS, BOT_USERNAME
from database.models import Payment
from database import create_payment, update_payment_status, add_tokens, set_unlimited_status, get_payment

logger = logging.getLogger(__name__)

class FreePaymentService:
    """
    Бесплатный платежный сервис.
    Используется, когда YooKassa недоступна или в режиме разработки.
    Все платежи автоматически считаются успешными.
    """
    
    def __init__(self):
        self.payments = {}  # Словарь для хранения информации о платежах
        logger.info("Инициализирован бесплатный платежный сервис")
    
    async def create_payment_link(self, user_id: int, tariff: str) -> Tuple[Optional[str], Optional[Payment]]:
        """
        Создает платежную ссылку для оплаты тарифа.
        В бесплатной версии просто создает тестовый платеж и сразу начисляет токены.
        
        Args:
            user_id: ID пользователя
            tariff: ID тарифа
            
        Returns:
            Tuple[str, Payment]: URL для подтверждения и объект платежа
        """
        logger.info(f"📝 Создание бесплатного платежа для пользователя {user_id}, тариф: {tariff}")
        
        if tariff not in TARIFFS:
            logger.error(f"❌ Тариф {tariff} не найден в конфигурации")
            logger.info(f"Доступные тарифы: {list(TARIFFS.keys())}")
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
        
        # Используем гарантированно рабочий URL с поддержкой в Telegram
        # Используем формат, который точно работает в Telegram
        payment_url = f"https://t.me/{BOT_USERNAME}?start=payment_{payment_id}"
        
        logger.info(f"✅ Создан бесплатный платеж {payment_id} для пользователя {user_id}")
        logger.info(f"🔗 URL для подтверждения: {payment_url}")
        
        return payment_url, payment
    
    async def create_payment(self, amount: float, description: str) -> Tuple[str, str]:
        """
        Создает бесплатный платеж и возвращает его идентификатор и URL оплаты.
        В этой реализации платеж всегда считается успешным.
        
        Args:
            amount: Сумма платежа
            description: Описание платежа
            
        Returns:
            Tuple[str, str]: ID платежа и URL для оплаты
        """
        payment_id = f"free_payment_{len(self.payments) + 1}"
        confirmation_url = f"https://free-payment.example.com/{payment_id}"
        
        # Сохраняем информацию о платеже
        self.payments[payment_id] = {
            "amount": amount,
            "description": description,
            "status": "succeeded"  # Сразу помечаем как успешный
        }
        
        logger.info(f"Создан бесплатный платеж: {payment_id}, сумма: {amount}, описание: {description}")
        return payment_id, confirmation_url
    
    async def check_payment_status(self, payment_id: str) -> Optional[str]:
        """
        Проверяет статус платежа и начисляет токены пользователю.
        В бесплатной версии все платежи всегда успешны.
        
        Args:
            payment_id: ID платежа
            
        Returns:
            str: Статус платежа
        """
        # Получаем платеж из базы данных
        payment = await get_payment(payment_id)
        
        if not payment:
            logger.warning(f"⚠️ Платеж {payment_id} не найден в базе данных")
            return None
            
        # Если платеж уже обработан, просто возвращаем его статус
        if payment.status == 'succeeded':
            logger.info(f"✅ Платеж {payment_id} уже имеет статус succeeded")
            return 'succeeded'
            
        # Имитируем небольшую задержку, как будто проверяем статус на сервере YooKassa
        time.sleep(0.5)
        
        # В бесплатной версии всегда считаем платеж успешным
        # Обновляем статус платежа в базе
        payment = await update_payment_status(payment_id, 'succeeded')
        
        if payment:
            # Начисляем токены пользователю в зависимости от тарифа
            if payment.tokens == -1:  # Безлимитный тариф
                await set_unlimited_status(payment.user_id, True)
                logger.info(f"🎉 Пользователю {payment.user_id} активирован безлимитный тариф")
            else:
                await add_tokens(payment.user_id, payment.tokens)
                logger.info(f"🎉 Пользователю {payment.user_id} начислено {payment.tokens} токенов")
        
        return 'succeeded'
    
    async def check_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Проверяет статус бесплатного платежа.
        Все платежи всегда считаются успешными.
        
        Args:
            payment_id: ID платежа для проверки
            
        Returns:
            Dict[str, Any]: Информация о платеже
        """
        # Проверяем существование платежа
        if payment_id not in self.payments:
            logger.warning(f"Платеж с ID {payment_id} не найден")
            return {"status": "not_found"}
        
        logger.info(f"Проверка бесплатного платежа: {payment_id}, статус: succeeded")
        return {
            "id": payment_id,
            "status": "succeeded",
            "amount": self.payments[payment_id]["amount"],
            "description": self.payments[payment_id]["description"]
        }
    
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
    
    async def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Имитирует отмену платежа, но так как платежи бесплатные,
        фактически просто меняет статус.
        
        Args:
            payment_id: ID платежа для отмены
            
        Returns:
            Dict[str, Any]: Информация об отмененном платеже
        """
        if payment_id not in self.payments:
            logger.warning(f"Платеж с ID {payment_id} не найден")
            return {"status": "not_found"}
        
        self.payments[payment_id]["status"] = "canceled"
        
        logger.info(f"Отмена бесплатного платежа: {payment_id}")
        return {
            "id": payment_id,
            "status": "canceled",
            "amount": self.payments[payment_id]["amount"],
            "description": self.payments[payment_id]["description"]
        }

# Создаем экземпляр сервиса
payment_service = FreePaymentService() 