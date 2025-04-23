from typing import Optional, Dict, List
import logging
from telegram import Bot
from telegram.error import TelegramError

import config
from database import get_user, set_subscription_status

# Настраиваем логирование
logger = logging.getLogger(__name__)

class SubscriptionService:
    """Сервис для проверки подписки на канал"""
    
    @staticmethod
    async def check_subscription(bot: Bot, user_id: int) -> bool:
        """Проверить, подписан ли пользователь на канал"""
        try:
            logger.info(f"Проверка подписки пользователя {user_id} на канал {config.CHANNEL_ID}")
            
            # Пробуем получить статус пользователя в канале
            chat_member = await bot.get_chat_member(chat_id=config.CHANNEL_ID, user_id=user_id)
            
            # Проверяем статус участника
            status = chat_member.status
            is_subscribed = status in ['member', 'administrator', 'creator']
            
            logger.info(f"Статус подписки пользователя {user_id}: {status}, подписан: {is_subscribed}")
            
            # Обновляем статус в базе данных
            user = await get_user(user_id)
            if user and user.is_subscribed != is_subscribed:
                await set_subscription_status(user_id, is_subscribed)
                logger.info(f"Обновлен статус подписки для пользователя {user_id}: {is_subscribed}")
            
            return is_subscribed
        except TelegramError as e:
            logger.error(f"Ошибка при проверке подписки пользователя {user_id}: {str(e)}")
            return False

    @staticmethod
    def get_channel_link() -> str:
        """Получить ссылку на канал для подписки"""
        # Проверяем наличие ссылки в конфигурации
        if config.CHANNEL_URL:
            logger.info(f"Используется канал из конфигурации: {config.CHANNEL_URL}")
            return config.CHANNEL_URL
            
        # Запасная ссылка на канал
        logger.warning("Ссылка на канал не найдена в конфигурации, используется запасная ссылка")
        return "https://t.me/bilalovai"

# Создаем экземпляр для использования в других модулях
subscription_service = SubscriptionService() 