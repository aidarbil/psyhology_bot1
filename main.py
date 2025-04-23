import logging
import os
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

import config
from handlers import (
    start_command,
    handle_message,
    start_chat_callback,
    buy_tokens_callback,
    select_tariff_callback,
    check_payment_callback,
    back_to_main_callback,
    check_subscription_callback,
    admin_command,
    admin_stats_callback,
    admin_give_tokens_callback,
    admin_give_unlimited_callback,
    admin_back_callback,
    handle_admin_commands
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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
    app.add_handler(CommandHandler("admin", admin_command))
    
    # Обработчики колбэков (кнопок)
    app.add_handler(CallbackQueryHandler(start_chat_callback, pattern="^start_chat$"))
    app.add_handler(CallbackQueryHandler(buy_tokens_callback, pattern="^buy_tokens$"))
    app.add_handler(CallbackQueryHandler(select_tariff_callback, pattern="^select_tariff:"))
    app.add_handler(CallbackQueryHandler(check_payment_callback, pattern="^check_payment:"))
    app.add_handler(CallbackQueryHandler(back_to_main_callback, pattern="^back_to_main$"))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))
    
    # Обработчики колбэков администратора
    app.add_handler(CallbackQueryHandler(admin_stats_callback, pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(admin_give_tokens_callback, pattern="^admin_give_tokens$"))
    app.add_handler(CallbackQueryHandler(admin_give_unlimited_callback, pattern="^admin_give_unlimited$"))
    app.add_handler(CallbackQueryHandler(admin_back_callback, pattern="^admin_back$"))
    
    # Обработчик всех текстовых сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик админских команд в тексте
    app.add_handler(MessageHandler(filters.TEXT & filters.COMMAND, handle_admin_commands))

async def process_yukassa_notification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик уведомлений от ЮKassa"""
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
    """Глобальный обработчик ошибок"""
    logger.error(f"Exception while handling an update: {context.error}")

def main() -> None:
    """Запуск бота"""
    # Проверяем наличие токена
    if not config.TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN not found. Please set it in .env file.")
        return
    
    # Создаем экземпляр приложения
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()
    
    # Регистрируем обработчики
    register_handlers(app)
    
    # Регистрируем обработчик ошибок
    app.add_error_handler(error_handler)
    
    # Настраиваем вебхук или запускаем в режиме поллинга
    is_production = os.getenv('ENVIRONMENT', 'development') == 'production'
    
    if is_production:
        # В продакшн режиме используем вебхуки
        webhook_path = os.getenv('WEBHOOK_PATH', f'/webhook/{config.TELEGRAM_TOKEN}')
        port = int(os.getenv('PORT', 8000))
        
        # Настраиваем вебхук при запуске
        app.post_init = setup_webhook
        
        # Регистрируем обработчик для уведомлений от ЮKassa
        app.add_handler(CommandHandler("yukassa_webhook", process_yukassa_notification))
        
        # Запускаем бота с вебхуком
        app.run_webhook(
            listen='0.0.0.0',
            port=port,
            webhook_url=None,  # Будет установлен в setup_webhook
            secret_token=os.getenv('WEBHOOK_SECRET', ''),
            drop_pending_updates=True
        )
    else:
        # В режиме разработки используем поллинг
        app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main() 