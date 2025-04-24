from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import logging

import config
from database import get_user, get_or_create_user
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
    
    # Создаем пользователя, если его нет в базе
    user = await get_or_create_user(user_id, username)
    
    # Проверяем реферальный код
    if context.args and context.args[0].startswith('ref_'):
        await process_referral_code(update, context)
    
    # Показываем главное меню с описанием
    await show_main_menu(update, context, user, show_description=True)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /menu"""
    # Показываем главное меню без описания
    await show_main_menu(update, context, show_description=False) 