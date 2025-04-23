import uuid
import logging
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timedelta

from config import TARIFFS, BOT_USERNAME
from database.models import Payment
from database import create_payment, update_payment_status, add_tokens, set_unlimited_status

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