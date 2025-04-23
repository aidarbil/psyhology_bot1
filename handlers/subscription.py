from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

import config
from database import get_user, set_subscription_status
from services.subscription import subscription_service

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик проверки подписки на канал"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Проверяем, подписан ли пользователь на канал
    is_subscribed = await subscription_service.check_subscription(context.bot, user_id)
    
    if is_subscribed:
        # Пользователь подписан, выдаем бонусные токены
        user = await get_user(user_id)
        
        # Создаем клавиатуру для начала диалога
        keyboard = [
            [InlineKeyboardButton("💬 Начать диалог", callback_data="start_chat")]
        ]
        
        # Если у пользователя мало токенов, добавляем кнопку пополнения
        if user.tokens < config.TOKENS_PER_MESSAGE and not user.is_unlimited:
            keyboard.append([InlineKeyboardButton("💰 Пополнить Майндтокены", callback_data="buy_tokens")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=(
                f"✅ Спасибо за подписку на наш канал!\n\n"
                f"🎁 Вам начислено {config.FREE_TOKENS} Майндтокенов.\n"
                f"💎 Ваш текущий баланс: {user.tokens} Майндтокенов.\n\n"
                f"Этого хватит на {user.tokens // config.TOKENS_PER_MESSAGE} вопросов."
            ),
            reply_markup=reply_markup
        )
    else:
        # Пользователь не подписан, предлагаем подписаться
        channel_link = subscription_service.get_channel_link()
        
        keyboard = [
            [InlineKeyboardButton("📢 Подписаться на канал", url=channel_link)],
            [InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscription")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=(
                "⚠️ Вы еще не подписаны на наш канал.\n\n"
                f"Подпишитесь на канал и получите {config.FREE_TOKENS} Майндтокенов бесплатно!\n"
                f"Этого хватит на {config.FREE_TOKENS // config.TOKENS_PER_MESSAGE} вопросов."
            ),
            reply_markup=reply_markup
        ) 