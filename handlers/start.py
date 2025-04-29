from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import logging

import config
from database import get_user, get_or_create_user, add_tokens, set_subscription_status
from services import subscription_service
from handlers.menu import process_referral_code

logger = logging.getLogger(__name__)

# Описание бота
BOT_DESCRIPTION = """
🤖 *Добро пожаловать в Психолог-БОТ!*

Я - ваш дружелюбный помощник-психолог, который всегда готов выслушать и поддержать вас. Со мной легко общаться - просто нажмите кнопку "Начать диалог" и расскажите, что вас беспокоит.

🎯 *Как со мной общаться:*
1. Нажмите "Начать диалог" 
2. Опишите свою ситуацию простыми словами
3. Я внимательно выслушаю и дам полезные советы

✨ *Чем я могу помочь:*
• Разобраться в сложных жизненных ситуациях
• Найти выход из стрессовых состояний
• Улучшить отношения с близкими
• Повысить самооценку и уверенность
• Справиться с тревогой и страхами

💎 За каждое обращение списывается {tokens_per_message} Майндтокенов.
Пополнить баланс можно через кнопку "Купить токены".

🤝 Я здесь, чтобы помочь вам! Не стесняйтесь обращаться с любыми вопросами.
"""

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user=None, show_description=True) -> None:
    """Показать главное меню"""
    if not user:
        user_id = update.effective_user.id
        user = await get_user(user_id)
    
    # Создаем клавиатуру с кнопками
    keyboard = [
        [InlineKeyboardButton("💬 Начать диалог", callback_data="start_chat")],
        [InlineKeyboardButton("💰 Купить токены", callback_data="buy_tokens")],
        [InlineKeyboardButton("ℹ️ О боте", callback_data="show_description")],
        [
            InlineKeyboardButton("📝 Оставить отзыв", callback_data="show_review_form"),
            InlineKeyboardButton("👥 Пригласить друзей", callback_data="show_referral")
        ]
    ]
    
    # Добавляем информацию о балансе
    balance_text = "∞ Безлимитный тариф" if user.is_unlimited else f"💎 Баланс: {user.tokens} Майндтокенов"
    
    # Формируем текст сообщения
    message_text = f"""🤖 *Главное меню*
Я - ваш дружелюбный помощник-психолог, который всегда готов выслушать и поддержать вас. Со мной легко общаться - просто нажмите кнопку "Начать диалог" и расскажите, что вас беспокоит.

🎯 *Как со мной общаться:*
1. Нажмите "Начать диалог" 
2. Опишите свою ситуацию простыми словами
3. Я внимательно выслушаю и дам полезные советы

✨ *Чем я могу помочь:*
• Разобраться в сложных жизненных ситуациях
• Найти выход из стрессовых состояний
• Улучшить отношения с близкими
• Повысить самооценку и уверенность
• Справиться с тревогой и страхами

💎 За каждое обращение списывается {config.TOKENS_PER_MESSAGE} Майндтокенов.
Пополнить баланс можно через кнопку "Купить токены".

🤝 Я здесь, чтобы помочь вам! Не стесняйтесь обращаться с любыми вопросами.

{balance_text}"""
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Определяем, нужно ли редактировать существующее сообщение или отправить новое
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    last_name = update.effective_user.last_name
    
    # Создаем пользователя, если его нет в базе
    user = await get_or_create_user(user_id, username, first_name, last_name)
    
    # Проверяем, подписан ли пользователь на канал
    is_subscribed = await subscription_service.check_subscription(user_id)
    if not is_subscribed and not config.TEST_MODE and config.CHANNEL_ID:
        # Если не подписан, предлагаем подписаться или пропустить
        channel_link = subscription_service.get_channel_link()
        
        keyboard = [
            [InlineKeyboardButton("📢 Подписаться на канал", url=channel_link)],
            [InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscription")],
            [InlineKeyboardButton("⏩ Пропустить подписку", callback_data="skip_subscription")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text=(
                "🔹 Для получения бесплатных токенов необходимо подписаться на канал Создателя.\n\n"
                f"За подписку вы получите {config.FREE_TOKENS} Майндтокенов бесплатно!\n"
                f"Этого хватит на {config.FREE_TOKENS // config.TOKENS_PER_MESSAGE} вопросов.\n\n"
                "Вы можете подписаться сейчас или пропустить этот шаг."
            ),
            reply_markup=reply_markup
        )
        return
    
    # Проверка аргументов команды start
    if context.args:
        arg = context.args[0]
        
        # Обработка реферальной ссылки
        if arg.startswith('ref_'):
            await process_referral_code(update, context)
        
        # Обработка платежных ссылок
        elif arg.startswith('payment_'):
            payment_id = arg.replace('payment_', '')
            logger.info(f"Получена платежная ссылка с ID платежа: {payment_id}")
            
            # Перенаправляем пользователя на проверку оплаты
            await update.message.reply_text(
                "💳 Вы перешли по платежной ссылке. Нажмите кнопку ниже, чтобы проверить статус платежа:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Проверить оплату", callback_data=f"check_payment:{payment_id}")]
                ])
            )
            return
    
    # Показываем главное меню с описанием
    await show_main_menu(update, context, user, show_description=True)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /menu"""
    # Показываем главное меню без описания
    await show_main_menu(update, context, show_description=False) 