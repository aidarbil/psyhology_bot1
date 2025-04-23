import motor.motor_asyncio
from typing import Dict, List, Optional, Union
from datetime import datetime

import config
from database.models import User, Payment

# Подключение к MongoDB
client = motor.motor_asyncio.AsyncIOMotorClient(config.MONGO_URI)
db = client[config.DB_NAME]

# Коллекции
users_collection = db['users']
payments_collection = db['payments']

# Операции с пользователями
async def get_user(user_id: int) -> Optional[User]:
    """Получить пользователя по ID"""
    user_data = await users_collection.find_one({'user_id': user_id})
    if user_data:
        return User.from_dict(user_data)
    return None

async def create_user(user: User) -> User:
    """Создать нового пользователя"""
    user_dict = user.to_dict()
    await users_collection.insert_one(user_dict)
    return user

async def update_user(user: User) -> User:
    """Обновить данные пользователя"""
    user_dict = user.to_dict()
    await users_collection.update_one(
        {'user_id': user.user_id},
        {'$set': user_dict}
    )
    return user

async def get_or_create_user(
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None
) -> User:
    """Получить пользователя или создать нового"""
    user = await get_user(user_id)
    if not user:
        user = User(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        await create_user(user)
    return user

async def add_tokens(user_id: int, tokens: int) -> User:
    """Добавить токены пользователю"""
    user = await get_user(user_id)
    if user:
        user.tokens += tokens
        await update_user(user)
    return user

async def deduct_tokens(user_id: int, tokens: int) -> Optional[User]:
    """Списать токены у пользователя"""
    user = await get_user(user_id)
    if user and (user.is_unlimited or user.tokens >= tokens):
        if not user.is_unlimited:
            user.tokens -= tokens
        user.last_activity = datetime.now()
        await update_user(user)
        return user
    return None

async def set_subscription_status(user_id: int, is_subscribed: bool) -> User:
    """Установить статус подписки пользователя"""
    user = await get_user(user_id)
    if user:
        user.is_subscribed = is_subscribed
        if is_subscribed and user.tokens == 0:  # Если подписался впервые
            user.tokens = config.FREE_TOKENS
        await update_user(user)
    return user

async def set_unlimited_status(user_id: int, is_unlimited: bool) -> User:
    """Установить статус безлимитного тарифа"""
    user = await get_user(user_id)
    if user:
        user.is_unlimited = is_unlimited
        await update_user(user)
    return user

async def add_message_to_history(user_id: int, message: str, is_user: bool) -> User:
    """Добавить сообщение в историю чата пользователя"""
    user = await get_user(user_id)
    if user:
        message_data = {
            'text': message,
            'is_user': is_user,
            'timestamp': datetime.now()
        }
        user.chat_history.append(message_data)
        await update_user(user)
    return user

# Операции с платежами
async def create_payment(payment: Payment) -> Payment:
    """Создать новый платеж"""
    payment_dict = payment.to_dict()
    await payments_collection.insert_one(payment_dict)
    return payment

async def get_payment(payment_id: str) -> Optional[Payment]:
    """Получить платеж по ID"""
    payment_data = await payments_collection.find_one({'payment_id': payment_id})
    if payment_data:
        return Payment.from_dict(payment_data)
    return None

async def update_payment_status(payment_id: str, status: str) -> Optional[Payment]:
    """Обновить статус платежа"""
    payment = await get_payment(payment_id)
    if payment:
        payment.status = status
        if status == 'succeeded':
            payment.completed_at = datetime.now()
        
        payment_dict = payment.to_dict()
        await payments_collection.update_one(
            {'payment_id': payment.payment_id},
            {'$set': payment_dict}
        )
        return payment
    return None

async def get_user_payments(user_id: int) -> List[Payment]:
    """Получить все платежи пользователя"""
    cursor = payments_collection.find({'user_id': user_id})
    payments = []
    async for payment_data in cursor:
        payments.append(Payment.from_dict(payment_data))
    return payments 