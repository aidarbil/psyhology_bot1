from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import logging
import traceback

import config
from database import get_user, deduct_tokens, add_message_to_history
from services import ai_service  # Используем умный выбор агента
from handlers.menu import handle_review_text  # Импортируем обработчик отзывов
from services.subscription import subscription_service

# Настраиваем логирование
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик входящих сообщений от пользователя"""
    message = update.message
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = message.text
    
    logger.info(f"[DEBUG] Начало обработки сообщения от пользователя {user_id}")
    logger.info(f"Получено сообщение от пользователя {user_id}: {text}")
    
    # Проверяем состояние пользователя
    if context.user_data.get('state') == 'waiting_for_review':
        logger.info(f"[DEBUG] Пользователь {user_id} отправил отзыв: {text}")
        await handle_review_text(update, context)
        return
    
    # Получаем пользователя из базы данных
    user = await get_user(user_id)
    logger.info(f"[DEBUG] Получен пользователь из БД: {user}")
    
    if not user:
        logger.warning(f"Пользователь {user_id} не найден в базе данных")
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=chat_id,
            text="Пожалуйста, используйте команду /start для начала работы с ботом.",
            reply_markup=reply_markup
        )
        return
    
    # Проверяем подписку пользователя на канал
    is_subscribed = await subscription_service.check_subscription(user_id)
    if not is_subscribed and not config.TEST_MODE and config.CHANNEL_ID:
        logger.info(f"Пользователь {user_id} не подписан на канал")
        channel_link = subscription_service.get_channel_link()
        
        keyboard = [
            [InlineKeyboardButton("📢 Подписаться на канал", url=channel_link)],
            [InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscription")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "⚠️ Для использования бота необходимо подписаться на наш канал.\n\n"
                f"Подпишитесь на канал и получите {config.FREE_TOKENS} Майндтокенов бесплатно!\n"
                f"Этого хватит на {config.FREE_TOKENS // config.TOKENS_PER_MESSAGE} вопросов."
            ),
            reply_markup=reply_markup
        )
        return
    
    # Проверяем, достаточно ли токенов у пользователя
    if not user.is_unlimited and user.tokens < config.TOKENS_PER_MESSAGE:
        logger.info(f"У пользователя {user_id} недостаточно токенов: {user.tokens}")
        keyboard = [
            [InlineKeyboardButton("💰 Пополнить Майндтокены", callback_data="buy_tokens")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
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
    logger.info(f"[DEBUG] Отправлен статус 'печатает' для пользователя {user_id}")
    
    try:
        # Сохраняем сообщение пользователя в историю
        logger.info(f"[DEBUG] Сохраняем сообщение в историю для пользователя {user_id}")
        await add_message_to_history(user_id, text, is_user=True)
        
        logger.info(f"[DEBUG] Отправляем запрос к AI агенту для пользователя {user_id}")
        # Отправляем запрос к ИИ-агенту с поддержкой векторной памяти
        response = await ai_service.send_message(text, user_id=user_id)
        logger.info(f"[DEBUG] Получен ответ от агента: {response[:100] if response else 'None'}")
        
        if response:
            logger.info(f"[DEBUG] Списываем токены для пользователя {user_id}")
            # Если получили ответ от агента, списываем токены и отправляем ответ
            updated_user = await deduct_tokens(user_id, config.TOKENS_PER_MESSAGE)
            logger.info(f"[DEBUG] Токены списаны, обновленный баланс: {updated_user.tokens}")
            
            # Сохраняем ответ агента в историю
            logger.info(f"[DEBUG] Сохраняем ответ в историю для пользователя {user_id}")
            await add_message_to_history(user_id, response, is_user=False)
            
            # Если пользователь не на безлимитном тарифе, добавляем информацию о балансе
            if not user.is_unlimited:
                response += f"\n\n💎 Остаток: {updated_user.tokens} Майндтокенов"
            
            # Добавляем кнопку главного меню к каждому ответу
            keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            logger.info(f"[DEBUG] Отправляем ответ пользователю {user_id}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=response,
                reply_markup=reply_markup
            )
            logger.info(f"[DEBUG] Ответ успешно отправлен пользователю {user_id}")
        else:
            # В случае ошибки с получением ответа от AI
            logger.error(f"[DEBUG] Не получен ответ от AI агента для пользователя {user_id}")
            keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=chat_id,
                text="😔 Извините, возникла техническая проблема при обработке вашего запроса. Пожалуйста, попробуйте позже.",
                reply_markup=reply_markup
            )
    except Exception as e:
        # Логируем детали исключения для отладки
        error_details = traceback.format_exc()
        logger.error(f"[DEBUG] Ошибка при обработке сообщения от пользователя {user_id}: {str(e)}\n{error_details}")
        
        # Отправляем пользователю сообщение об ошибке
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=chat_id,
            text="😔 Произошла ошибка при обработке вашего сообщения. Наши специалисты уже работают над решением проблемы.",
            reply_markup=reply_markup
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