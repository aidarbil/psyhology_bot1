from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import asyncio

import config
from database import get_user, set_subscription_status, add_tokens
from services.subscription import subscription_service
from handlers.start import show_main_menu

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик проверки подписки на канал"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Проверяем подписку
    is_subscribed = await subscription_service.check_subscription(user_id)
    
    if is_subscribed or config.TEST_MODE:  # В тестовом режиме или при наличии подписки
        user = await get_user(user_id)
        if not user.is_subscribed:  # Если бонус еще не был получен
            # Начисляем бонусные токены
            await add_tokens(user_id, config.FREE_TOKENS)
            # Отмечаем что подписка получена
            await set_subscription_status(user_id, True)
            
            # Получаем обновленные данные пользователя
            user = await get_user(user_id)
            
            # Показываем благодарственное сообщение
            await query.edit_message_text(
                text=(
                    "🎉 Спасибо за подписку!\n\n"
                    f"🎁 Вам начислено {config.FREE_TOKENS} Майндтокенов в подарок.\n"
                    f"💎 Ваш текущий баланс: {user.tokens} Майндтокенов.\n\n"
                    f"Этого хватит на {user.tokens // config.TOKENS_PER_MESSAGE} вопросов."
                )
            )
            
            # Через небольшую паузу показываем главное меню
            await asyncio.sleep(2)
            await show_main_menu(update, context, user, show_description=True)
        else:
            # Если бонус уже был получен, просто показываем главное меню
            await show_main_menu(update, context, user, show_description=True)
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