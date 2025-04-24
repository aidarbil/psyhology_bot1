from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import logging
import uuid

import config
from database import (
    get_user, create_review, generate_referral_code,
    process_referral, get_user_by_referral_code
)

logger = logging.getLogger(__name__)

# Текст описания бота
BOT_DESCRIPTION = """
🤖 *Добро пожаловать в Психолог-БОТ!*

Я - ваш персональный ИИ-психолог, готовый помочь вам в любое время дня и ночи. 

*Как я работаю:*
• Каждое сообщение стоит {tokens} Майндтокенов
• За подписку на канал вы получаете {free_tokens} бесплатных токенов
• Вы можете пригласить друзей и получить {referral_tokens} токенов за каждого

*Как купить токены:*
1. Перейдите в раздел "Купить токены"
2. Выберите подходящий тариф
3. Оплатите удобным способом

*Важно знать:*
• Все ваши диалоги конфиденциальны
• Используется продвинутый ИИ для анализа
• Майндтокены в будущем могут стать криптовалютой! 🚀

*Команды:*
/start - Начать сначала
/help - Помощь
/balance - Баланс токенов
""".format(
    tokens=config.TOKENS_PER_MESSAGE,
    free_tokens=config.FREE_TOKENS,
    referral_tokens=config.REFERRAL_BONUS_TOKENS
)

async def show_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать описание бота"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=BOT_DESCRIPTION,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_review_form(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать форму для отзыва"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Сохраняем состояние - ожидаем отзыв
    context.user_data['state'] = 'waiting_for_review'
    
    await query.edit_message_text(
        text=(
            "📝 *Оставьте свой отзыв*\n\n"
            "Пожалуйста, напишите ваше мнение о работе бота.\n"
            "Ваш отзыв поможет нам стать лучше!"
        ),
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_review_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработать текст отзыва"""
    if context.user_data.get('state') != 'waiting_for_review':
        return
    
    user_id = update.effective_user.id
    review_text = update.message.text
    
    # Создаем отзыв в базе данных
    await create_review(user_id, review_text)
    
    # Очищаем состояние
    context.user_data.pop('state', None)
    
    # Показываем благодарность
    keyboard = [[InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🙏 *Спасибо за ваш отзыв!*\n\n"
        "Мы ценим ваше мнение и постоянно работаем над улучшением бота.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_referral_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать реферальное меню"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user = await get_user(user_id)
    
    # Генерируем реферальный код, если его нет
    referral_code = await generate_referral_code(user_id)
    
    referral_link = f"https://t.me/{config.BOT_USERNAME}?start=ref_{referral_code}"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=(
            "👥 *Пригласите друзей и получите бонусы!*\n\n"
            f"За каждого приглашенного друга вы получите {config.REFERRAL_BONUS_TOKENS} Майндтокенов.\n\n"
            f"Ваша реферальная ссылка (нажмите, чтобы скопировать):\n"
            f"```{referral_link}```\n\n"
            f"Количество приглашенных: {user.referral_count}\n"
            f"Заработано токенов: {user.referral_count * config.REFERRAL_BONUS_TOKENS}"
        ),
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def process_referral_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработать реферальный код из команды /start"""
    args = context.args
    if not args or not args[0].startswith('ref_'):
        return
    
    user_id = update.effective_user.id
    referral_code = args[0][4:]  # Убираем префикс 'ref_'
    
    # Проверяем и обрабатываем реферальный код
    success = await process_referral(user_id, referral_code)
    
    if success:
        await update.message.reply_text(
            f"🎉 Поздравляем! Вы присоединились по реферальной ссылке и получили {config.REFERRAL_BONUS_TOKENS} Майндтокенов!"
        ) 