from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

import config
from database import get_or_create_user
from services import subscription_service

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Получаем или создаем пользователя в базе данных
    db_user = await get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Приветственное сообщение
    welcome_text = (
        f"👋 Здравствуйте, {user.first_name}!\n\n"
        "Я — бот-психолог на базе искусственного интеллекта. "
        "Я готов выслушать вас, помочь разобраться в сложных ситуациях "
        "и предложить поддержку в любое время суток.\n\n"
        "🔹 Что я могу:\n"
        "• Обсудить ваши эмоции и переживания\n"
        "• Помочь разобраться в сложных ситуациях\n"
        "• Предложить практические стратегии для решения проблем\n"
        "• Поддержать вас в трудный момент\n\n"
        f"💎 У вас сейчас {db_user.tokens} Майндтокенов."
    )
    
    # Проверяем подписку на канал
    is_subscribed = await subscription_service.check_subscription(context.bot, user.id)
    
    # Создаем клавиатуру в зависимости от статуса подписки
    if is_subscribed:
        keyboard = [
            [InlineKeyboardButton("💬 Начать диалог", callback_data="start_chat")]
        ]
        
        # Если у пользователя нет токенов, добавляем кнопку пополнения
        if db_user.tokens < config.TOKENS_PER_MESSAGE and not db_user.is_unlimited:
            keyboard.append([InlineKeyboardButton("💰 Пополнить Майндтокены", callback_data="buy_tokens")])
    else:
        # Если пользователь не подписан, предлагаем подписаться
        channel_link = subscription_service.get_channel_link()
        keyboard = [
            [InlineKeyboardButton("📢 Подписаться на канал", url=channel_link)],
            [InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscription")]
        ]
        
        # Добавляем информацию о бонусе за подписку
        welcome_text += f"\n\n🎁 Подпишитесь на наш канал и получите {config.FREE_TOKENS} Майндтокенов бесплатно!"
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=welcome_text,
        reply_markup=reply_markup
    ) 