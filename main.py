import logging
import os
import sys
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
    ContextTypes
)
import httpx
import asyncio

import config
from utils.logging_config import setup_logging, get_logger
from services import subscription_service
from handlers import (
    start_command,
    menu_command,
    handle_message,
    start_chat_callback,
    buy_tokens_callback,
    select_tariff_callback,
    check_payment_callback,
    pre_checkout_handler,
    successful_payment_handler,
    back_to_main_callback,
    check_subscription_callback,
    skip_subscription_callback,
    admin_command,
    admin_stats_callback,
    admin_give_tokens_callback,
    admin_give_unlimited_callback,
    admin_back_callback,
    handle_admin_commands
)
from handlers.menu import (
    show_description,
    show_review_form,
    handle_review_text,
    show_referral_menu
)

# Загружаем переменные окружения
load_dotenv()

# Настраиваем логирование с уровнем DEBUG
setup_logging(log_level='DEBUG')
logger = get_logger(__name__)

# Проверяем наличие токена
if not config.TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN не найден!")
    sys.exit(1)
else:
    logger.info(f"TELEGRAM_TOKEN найден, длина: {len(config.TELEGRAM_TOKEN)}")

# Проверяем наличие платежного токена
if not hasattr(config, 'TELEGRAM_PROVIDER_TOKEN') or not config.TELEGRAM_PROVIDER_TOKEN:
    logger.warning("TELEGRAM_PROVIDER_TOKEN не найден. Платежи через Telegram будут недоступны.")
else:
    logger.info(f"TELEGRAM_PROVIDER_TOKEN найден, платежи через Telegram активны")

async def setup_webhook(app: Application) -> None:
    """Настройка вебхука для продакшн окружения"""
    webhook_url = os.getenv('WEBHOOK_URL')
    webhook_secret = os.getenv('WEBHOOK_SECRET', '')
    webhook_path = os.getenv('WEBHOOK_PATH', f'/webhook/{config.TELEGRAM_TOKEN}')
    
    if webhook_url:
        await app.bot.set_webhook(
            url=f"{webhook_url}{webhook_path}",
            secret_token=webhook_secret
        )
        logger.info(f"Webhook set to {webhook_url}{webhook_path}")
    else:
        logger.info("Running in polling mode")

def register_handlers(app: Application) -> None:
    """Регистрация обработчиков команд и колбэков"""
    # Обработчики команд
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("admin", admin_command))
    
    # Обработчики колбэков (кнопок)
    app.add_handler(CallbackQueryHandler(start_chat_callback, pattern="^start_chat$"))
    app.add_handler(CallbackQueryHandler(buy_tokens_callback, pattern="^buy_tokens$"))
    app.add_handler(CallbackQueryHandler(select_tariff_callback, pattern="^select_tariff:"))
    app.add_handler(CallbackQueryHandler(check_payment_callback, pattern="^check_payment:"))
    app.add_handler(CallbackQueryHandler(back_to_main_callback, pattern="^back_to_main$"))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))
    app.add_handler(CallbackQueryHandler(skip_subscription_callback, pattern="^skip_subscription$"))
    
    # Обработчики новых кнопок меню
    app.add_handler(CallbackQueryHandler(show_description, pattern="^show_description$"))
    app.add_handler(CallbackQueryHandler(show_review_form, pattern="^show_review_form$"))
    app.add_handler(CallbackQueryHandler(show_referral_menu, pattern="^show_referral$"))
    app.add_handler(CallbackQueryHandler(back_to_main_callback, pattern="^main_menu$"))
    
    # Обработчики колбэков администратора
    app.add_handler(CallbackQueryHandler(admin_stats_callback, pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(admin_give_tokens_callback, pattern="^admin_give_tokens$"))
    app.add_handler(CallbackQueryHandler(admin_give_unlimited_callback, pattern="^admin_give_unlimited$"))
    app.add_handler(CallbackQueryHandler(admin_back_callback, pattern="^admin_back$"))
    
    # Обработчики для Telegram Payments
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    
    # Обработчик всех текстовых сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик админских команд в тексте
    app.add_handler(MessageHandler(filters.TEXT & filters.COMMAND, handle_admin_commands))

async def process_yukassa_notification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик уведомлений от ЮKassa (оставлен для совместимости)"""
    from services import payment_service
    
    try:
        # Получаем данные уведомления
        data = await update.request.json()
        
        # Обрабатываем уведомление
        result = await payment_service.process_payment_notification(data)
        
        if result:
            return {"success": True}
        else:
            return {"success": False, "error": "Failed to process notification"}
    except Exception as e:
        logger.error(f"Error processing YooKassa notification: {str(e)}")
        return {"success": False, "error": str(e)}

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Глобальный обработчик ошибок с расширенным логированием"""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    # Получаем информацию об обновлении
    if update:
        if isinstance(update, Update):
            user_id = update.effective_user.id if update.effective_user else "Unknown"
            chat_id = update.effective_chat.id if update.effective_chat else "Unknown"
            message_text = update.effective_message.text if update.effective_message else "No message"
            
            logger.error(
                "Update info: user_id=%s, chat_id=%s, message='%s'",
                user_id, chat_id, message_text
            )
        else:
            logger.error("Update object is not of type Update: %s", str(update))
    
    # Логируем дополнительный контекст ошибки
    if context and context.chat_data:
        logger.error("Chat data: %s", str(context.chat_data))
    if context and context.user_data:
        logger.error("User data: %s", str(context.user_data))
        
    # Если это критическая ошибка - отправляем уведомление администратору
    if isinstance(context.error, (SystemError, KeyError, AttributeError)):
        logger.critical(
            "Critical error occurred: %s\nTraceback: %s",
            str(context.error),
            context.error.__traceback__
        )

def main() -> None:
    """Запуск бота."""
    logger.info("Initializing bot...")
    
    # Создаем приложение и добавляем обработчик ошибок
    application = (
        Application.builder()
        .token(config.TELEGRAM_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .build()
    )
    logger.info("Application built successfully")
    
    # Инициализируем бота в сервисе подписки
    subscription_service.set_bot(application.bot)
    logger.info("Subscription service initialized with bot instance")
    
    # Настраиваем вебхук если URL предоставлен
    if os.getenv('WEBHOOK_URL'):
        logger.info("Setting up webhook at %s", os.getenv('WEBHOOK_URL'))
        setup_webhook(application)
        logger.info("Webhook setup completed")
    
    # Регистрируем обработчики
    logger.info("Registering handlers...")
    register_handlers(application)
    logger.info("Handlers registered successfully")
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)
    logger.info("Error handler added")
    
    # Запускаем бота
    if os.getenv('WEBHOOK_URL'):
        logger.info("Starting bot in webhook mode")
        application.run_webhook(
            listen="0.0.0.0",
            port=os.getenv('PORT', 8443),
            webhook_url=os.getenv('WEBHOOK_URL'),
            secret_token=os.getenv('WEBHOOK_SECRET', '')
        )
    else:
        logger.info("Starting bot in polling mode")
        application.run_polling()

if __name__ == '__main__':
    main() 