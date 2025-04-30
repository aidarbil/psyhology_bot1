#!/usr/bin/env python3
import asyncio
import logging
import sys

from database.operations import users_collection

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('migration')

async def add_subscription_bonus_field():
    """
    Добавляет поле has_received_subscription_bonus всем пользователям в базе данных.
    Для уже подписанных пользователей устанавливает значение True, для остальных - False.
    """
    logger.info("Начинаем миграцию: добавление поля has_received_subscription_bonus")
    
    # Количество обработанных пользователей
    updated_count = 0
    
    # Получаем всех пользователей
    cursor = users_collection.find({})
    
    async for user in cursor:
        user_id = user.get('user_id')
        is_subscribed = user.get('is_subscribed', False)
        
        # Устанавливаем значение поля на основе статуса подписки
        await users_collection.update_one(
            {'user_id': user_id},
            {'$set': {'has_received_subscription_bonus': is_subscribed}}
        )
        
        updated_count += 1
        if updated_count % 100 == 0:
            logger.info(f"Обработано {updated_count} пользователей")
    
    logger.info(f"Миграция завершена. Всего обновлено {updated_count} пользователей.")

async def main():
    logger.info("Запуск миграции базы данных")
    await add_subscription_bonus_field()
    logger.info("Миграция завершена успешно")

if __name__ == "__main__":
    asyncio.run(main()) 