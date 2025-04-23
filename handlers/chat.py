from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import logging
import traceback

import config
from database import get_user, deduct_tokens, add_message_to_history
from services import ai_service  # Используем умный выбор агента

# Настраиваем логирование
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик входящих сообщений от пользователя"""
    message = update.message
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = message.text
    
    logger.info(f"Получено сообщение от пользователя {user_id}: {text[:30]}...")
    
    # Получаем пользователя из базы данных
    user = await get_user(user_id)
    
    if not user:
        # Если пользователя нет в базе, предлагаем начать с /start
        logger.warning(f"Пользователь {user_id} не найден в базе данных")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Пожалуйста, используйте команду /start для начала работы с ботом."
        )
        return
    
    # Проверяем, достаточно ли токенов у пользователя
    if not user.is_unlimited and user.tokens < config.TOKENS_PER_MESSAGE:
        # Если токенов недостаточно, предлагаем пополнить
        logger.info(f"У пользователя {user_id} недостаточно токенов: {user.tokens}")
        keyboard = [
            [InlineKeyboardButton("💰 Пополнить Майндтокены", callback_data="buy_tokens")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"⚠️ У вас недостаточно Майндтокенов для продолжения диалога. "
                f"Стоимость одного сообщения составляет {config.TOKENS_PER_MESSAGE} токенов.\n\n"
                f"Ваш текущий баланс: {user.tokens} Майндтокенов."
            ),
            reply_markup=reply_markup
        )
        return
    
    # Отправляем индикатор "печатает..."
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    try:
        # Сохраняем сообщение пользователя в историю
        await add_message_to_history(user_id, text, is_user=True)
        
        logger.info(f"Отправляем запрос к AI агенту для пользователя {user_id}")
        # Отправляем запрос к ИИ-агенту с поддержкой векторной памяти
        response = await ai_service.send_message(text, user_id=user_id)
        
        if response:
            logger.info(f"Получен ответ от AI агента для пользователя {user_id}: {response[:50]}...")
            # Если получили ответ от агента, списываем токены и отправляем ответ
            updated_user = await deduct_tokens(user_id, config.TOKENS_PER_MESSAGE)
            logger.info(f"Списано {config.TOKENS_PER_MESSAGE} токенов у пользователя {user_id}, остаток: {updated_user.tokens}")
            
            # Сохраняем ответ агента в историю
            await add_message_to_history(user_id, response, is_user=False)
            
            # Если пользователь не на безлимитном тарифе, добавляем информацию о балансе
            if not user.is_unlimited:
                response += f"\n\n💎 Остаток: {updated_user.tokens} Майндтокенов"
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=response
            )
        else:
            # В случае ошибки с получением ответа от AI
            logger.error(f"Не получен ответ от AI агента для пользователя {user_id}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="😔 Извините, возникла техническая проблема при обработке вашего запроса. Пожалуйста, попробуйте позже."
            )
    except Exception as e:
        # Логируем детали исключения для отладки
        error_details = traceback.format_exc()
        logger.error(f"Ошибка при обработке сообщения от пользователя {user_id}: {str(e)}\n{error_details}")
        
        # Отправляем пользователю сообщение об ошибке
        await context.bot.send_message(
            chat_id=chat_id,
            text="😔 Произошла ошибка при обработке вашего сообщения. Наши специалисты уже работают над решением проблемы."
        )

async def start_chat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатия на кнопку 'Начать диалог'"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    logger.info(f"Пользователь {user_id} запустил диалог")
    
    # Получаем пользователя из базы данных
    user = await get_user(user_id)
    
    # Очищаем векторную память при начале нового диалога
    try:
        await ai_service.clear_memory(user_id)
        logger.info(f"Очищена история диалога для пользователя {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при очистке истории диалога для пользователя {user_id}: {str(e)}")
    
    if user.is_unlimited or user.tokens >= config.TOKENS_PER_MESSAGE:
        # Если токенов достаточно, предлагаем начать диалог
        await query.edit_message_text(
            text=(
                "🔹 Вы можете начать диалог прямо сейчас. Просто напишите ваш вопрос или опишите ситуацию, "
                "и я постараюсь помочь вам разобраться.\n\n"
                "Чем я могу вам помочь сегодня?"
            )
        )
    else:
        # Если токенов недостаточно, предлагаем пополнить
        logger.info(f"У пользователя {user_id} недостаточно токенов для начала диалога: {user.tokens}")
        keyboard = [
            [InlineKeyboardButton("💰 Пополнить Майндтокены", callback_data="buy_tokens")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=(
                f"⚠️ У вас недостаточно Майндтокенов для начала диалога. "
                f"Стоимость одного сообщения составляет {config.TOKENS_PER_MESSAGE} токенов.\n\n"
                f"Ваш текущий баланс: {user.tokens} Майндтокенов."
            ),
            reply_markup=reply_markup
        ) 