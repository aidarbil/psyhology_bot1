from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import json
from datetime import datetime, timedelta
import logging

import config
from database import get_user, add_tokens, set_unlimited_status, get_bot_statistics

# Настройка логирования
logger = logging.getLogger(__name__)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /admin для админов бота"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Проверяем, является ли пользователь админом
    if user_id not in config.ADMIN_IDS:
        await context.bot.send_message(
            chat_id=chat_id,
            text="⛔ У вас нет доступа к админ-панели."
        )
        return
    
    # Меню админа
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("🎁 Выдать токены пользователю", callback_data="admin_give_tokens")],
        [InlineKeyboardButton("⭐ Выдать безлимит пользователю", callback_data="admin_give_unlimited")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text="🔐 Панель администратора",
        reply_markup=reply_markup
    )

async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик получения статистики бота"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Проверяем права администратора
    if user_id not in config.ADMIN_IDS:
        await query.edit_message_text(
            text="⛔ У вас нет доступа к админ-панели."
        )
        return
    
    # Получаем статистику из базы данных
    try:
        stats = await get_bot_statistics()
        
        stats_text = (
            "📊 Статистика бота:\n\n"
            f"👥 Всего пользователей: {stats['total_users']}\n"
            f"💬 Всего сообщений: {stats['total_messages']}\n"
            f"💰 Всего платежей: {stats['total_payments']}\n"
            f"💸 Общая сумма: {stats['total_amount']} ₽\n\n"
            f"За последние 24 часа:\n"
            f"👤 Новых пользователей: {stats['new_users_24h']}\n"
            f"💬 Сообщений: {stats['messages_24h']}\n"
            f"💰 Платежей: {stats['payments_24h']}\n"
        )
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {str(e)}")
        stats_text = "❌ Ошибка при получении статистики. Проверьте логи сервера."
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=stats_text,
        reply_markup=reply_markup
    )

async def admin_give_tokens_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик выдачи токенов пользователю"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Проверяем права администратора
    if user_id not in config.ADMIN_IDS:
        await query.edit_message_text(
            text="⛔ У вас нет доступа к админ-панели."
        )
        return
    
    # Сохраняем состояние для ожидания ID пользователя
    context.user_data['admin_state'] = 'waiting_user_id_for_tokens'
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=(
            "👤 Введите ID пользователя, которому хотите выдать токены.\n\n"
            "Формат: /user_id КОЛИЧЕСТВО_ТОКЕНОВ\n"
            "Например: /user_id 123456789 100"
        ),
        reply_markup=reply_markup
    )

async def admin_give_unlimited_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик выдачи безлимитного тарифа пользователю"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Проверяем права администратора
    if user_id not in config.ADMIN_IDS:
        await query.edit_message_text(
            text="⛔ У вас нет доступа к админ-панели."
        )
        return
    
    # Сохраняем состояние для ожидания ID пользователя
    context.user_data['admin_state'] = 'waiting_user_id_for_unlimited'
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=(
            "👤 Введите ID пользователя, которому хотите выдать безлимитный тариф.\n\n"
            "Формат: /unlimited ПОЛЬЗОВАТЕЛЬ_ID 1/0\n"
            "1 - включить безлимит, 0 - выключить\n"
            "Например: /unlimited 123456789 1"
        ),
        reply_markup=reply_markup
    )

async def admin_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик возврата в главное меню админа"""
    query = update.callback_query
    await query.answer()
    
    # Сбрасываем состояние админа
    if 'admin_state' in context.user_data:
        del context.user_data['admin_state']
    
    # Возвращаемся в главное меню админа
    await admin_command(update, context)

async def handle_admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик админских команд в тексте сообщений"""
    message = update.message
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = message.text
    
    # Проверяем, является ли пользователь админом
    if user_id not in config.ADMIN_IDS:
        return
    
    # Обрабатываем команду выдачи токенов
    if text.startswith('/user_id'):
        try:
            parts = text.split()
            target_user_id = int(parts[1])
            tokens_amount = int(parts[2])
            
            # Проверяем существование пользователя
            user = await get_user(target_user_id)
            if not user:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ Пользователь с ID {target_user_id} не найден."
                )
                return
            
            # Выдаем токены
            updated_user = await add_tokens(target_user_id, tokens_amount)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"✅ Пользователю {target_user_id} выдано {tokens_amount} Майндтокенов.\n"
                    f"Текущий баланс: {updated_user.tokens} Майндтокенов."
                )
            )
        except (ValueError, IndexError):
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Неверный формат команды. Используйте: /user_id ID_ПОЛЬЗОВАТЕЛЯ КОЛИЧЕСТВО_ТОКЕНОВ"
            )
    
    # Обрабатываем команду выдачи безлимита
    elif text.startswith('/unlimited'):
        try:
            parts = text.split()
            target_user_id = int(parts[1])
            is_unlimited = int(parts[2]) == 1
            
            # Проверяем существование пользователя
            user = await get_user(target_user_id)
            if not user:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ Пользователь с ID {target_user_id} не найден."
                )
                return
            
            # Устанавливаем статус безлимита
            await set_unlimited_status(target_user_id, is_unlimited)
            
            status_text = "включен" if is_unlimited else "выключен"
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ Для пользователя {target_user_id} безлимитный тариф {status_text}."
            )
        except (ValueError, IndexError):
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Неверный формат команды. Используйте: /unlimited ID_ПОЛЬЗОВАТЕЛЯ 1/0"
            )