from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from telegram.ext import ContextTypes
import logging

import config
from database import get_user
from services import payment_service

# Проверяем, доступны ли Telegram платежи
TELEGRAM_PAYMENTS_AVAILABLE = hasattr(config, 'TELEGRAM_PROVIDER_TOKEN') and bool(config.TELEGRAM_PROVIDER_TOKEN)

async def buy_tokens_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопки 'Пополнить Майндтокены'"""
    query = update.callback_query
    await query.answer()
    
    # Формируем список тарифов для покупки токенов
    keyboard = []
    for tariff_key, tariff_data in config.TARIFFS.items():
        button_text = f"{tariff_data['description']} - {tariff_data['price']} ₽"
        if tariff_key == 'unlimited':
            button_text = f"💫 {button_text} (безлимит)"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"select_tariff:{tariff_key}")])
    
    # Добавляем кнопку возврата
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="🔹 Выберите тариф для пополнения Майндтокенов:",
        reply_markup=reply_markup
    )

async def select_tariff_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик выбора тарифа для покупки токенов"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Получаем выбранный тариф из callback_data
    callback_data = query.data
    tariff = callback_data.split(':')[1]
    
    # Проверяем существование тарифа
    if tariff not in config.TARIFFS:
        await query.edit_message_text(
            text="⚠️ Выбран неверный тариф. Пожалуйста, попробуйте еще раз."
        )
        return
    
    # Получаем данные тарифа
    tariff_data = config.TARIFFS[tariff]
    amount = tariff_data['price']
    
    # Создаем платежную ссылку или данные для Telegram платежа
    payment_result, payment = await payment_service.create_payment_link(user_id, tariff)
    
    if not payment_result:
        await query.edit_message_text(
            text="⚠️ Произошла ошибка при создании платежа. Пожалуйста, попробуйте позже."
        )
        return
    
    # Формируем описание тарифа
    if tariff == 'unlimited':
        description = "безлимитное количество вопросов"
    else:
        tokens = tariff_data['tokens']
        questions = tokens // config.TOKENS_PER_MESSAGE
        description = f"{tokens} Майндтокенов ({questions} вопросов)"
    
    # Проверяем, используются ли Telegram Payments
    if TELEGRAM_PAYMENTS_AVAILABLE and payment_result.startswith("tariff:"):
        # Разбираем данные для Telegram платежа
        parts = payment_result.split(":")
        selected_tariff = parts[1]
        payment_id = parts[3]
        
        # Сохраняем платежную информацию в контексте для последующей обработки
        if not context.user_data.get('payment_info'):
            context.user_data['payment_info'] = {}
        
        context.user_data['payment_info'][payment_id] = {
            'tariff': selected_tariff,
            'payment_id': payment_id,
            'amount': amount
        }
        
        # Создаем инвойс через API Telegram
        await show_payment_invoice(update, context, selected_tariff, payment_id)
    else:
        # Для совместимости - обработка платежа через ЮKassa или другие системы
        # Создаем клавиатуру с кнопкой оплаты
        keyboard = [
            [InlineKeyboardButton("💳 Перейти к оплате", url=payment_result)],
            [InlineKeyboardButton("✅ Проверить оплату", callback_data=f"check_payment:{payment.payment_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="buy_tokens")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=(
                f"🔹 Вы выбрали тариф: {description}\n"
                f"Стоимость: {tariff_data['price']} ₽\n\n"
                "Для оплаты нажмите кнопку «Перейти к оплате» и следуйте инструкциям на сайте.\n"
                "После успешной оплаты нажмите «Проверить оплату»."
            ),
            reply_markup=reply_markup
        )

async def show_payment_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE, tariff: str, payment_id: str) -> None:
    """Показать платежную форму Telegram"""
    query = update.callback_query
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Проверяем существование тарифа
    if tariff not in config.TARIFFS:
        await query.edit_message_text("⚠️ Выбран неверный тариф. Пожалуйста, попробуйте еще раз.")
        return
    
    # Получаем данные тарифа
    tariff_data = config.TARIFFS[tariff]
    amount = tariff_data['price'] * 100  # В копейках
    
    # Формируем название платежа
    if tariff == 'unlimited':
        title = "Безлимитный тариф"
        description = "Безлимитное количество вопросов к психологу"
    else:
        tokens = tariff_data['tokens']
        questions = tokens // config.TOKENS_PER_MESSAGE
        title = f"Тариф: {tariff_data['description']}"
        description = f"{tokens} Майндтокенов ({questions} вопросов к психологу)"
    
    # Формируем цену с описанием
    prices = [LabeledPrice("Майндтокены", amount)]
    
    # Получаем токен из конфигурации, убеждаемся, что он в правильном формате без пробелов
    provider_token = config.TELEGRAM_PROVIDER_TOKEN.strip()
    
    try:
        # Логируем информацию о платеже для отладки
        logger = logging.getLogger(__name__)
        logger.info(f"Отправка инвойса с токеном провайдера: {provider_token[:4]}...{provider_token[-4:]}")
        logger.info(f"Chat ID: {chat_id}, Title: {title}, Amount: {amount}")
        
        # Отправляем инвойс
        await context.bot.send_invoice(
            chat_id=chat_id,
            title=title,
            description=description,
            payload=f"payment:{payment_id}:{tariff}",
            provider_token=provider_token,
            currency="RUB",
            prices=prices,
            start_parameter=f"payment_{payment_id}",
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            is_flexible=False
        )
        
        # Отправляем сообщение после инвойса
        keyboard = [
            [InlineKeyboardButton("🔙 Назад к тарифам", callback_data="buy_tokens")],
            [InlineKeyboardButton("⬅️ Главное меню", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="📲 Платежная форма отправлена. Пожалуйста, заполните данные для оплаты.",
            reply_markup=reply_markup
        )
    except Exception as e:
        # Логируем ошибку
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при отправке инвойса: {str(e)}")
        
        # Сообщаем пользователю об ошибке
        keyboard = [
            [InlineKeyboardButton("🔙 Назад к тарифам", callback_data="buy_tokens")],
            [InlineKeyboardButton("⬅️ Главное меню", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="⚠️ Произошла ошибка при создании платежа. Пожалуйста, попробуйте позже или обратитесь к администратору.",
            reply_markup=reply_markup
        )

async def check_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик проверки статуса платежа (для совместимости с ЮKassa)"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Получаем ID платежа из callback_data
    callback_data = query.data
    payment_id = callback_data.split(':')[1]
    
    # Проверяем статус платежа
    status = await payment_service.check_payment_status(payment_id)
    
    if status == 'succeeded':
        # Платеж успешно выполнен
        user = await get_user(user_id)
        
        # Формируем сообщение об успешной оплате
        if user.is_unlimited:
            message = (
                "✅ Оплата успешно выполнена!\n\n"
                "💫 У вас активирован безлимитный тариф. "
                "Теперь вы можете задавать неограниченное количество вопросов!"
            )
        else:
            message = (
                f"✅ Оплата успешно выполнена!\n\n"
                f"💎 Ваш текущий баланс: {user.tokens} Майндтокенов."
            )
        
        # Создаем клавиатуру для возврата в диалог
        keyboard = [
            [InlineKeyboardButton("💬 Вернуться к диалогу", callback_data="start_chat")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=message,
            reply_markup=reply_markup
        )
    elif status == 'pending':
        # Платеж в обработке
        await query.edit_message_text(
            text=(
                "⏳ Ваш платеж находится в обработке.\n\n"
                "Пожалуйста, подождите некоторое время и нажмите «Проверить оплату» снова."
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Проверить оплату", callback_data=f"check_payment:{payment_id}")],
                [InlineKeyboardButton("🔙 Назад", callback_data="buy_tokens")]
            ])
        )
    else:
        # Платеж не выполнен или возникла ошибка
        await query.edit_message_text(
            text=(
                "❌ Платеж не был выполнен или возникла ошибка.\n\n"
                "Пожалуйста, попробуйте снова или выберите другой способ оплаты."
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data="buy_tokens")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
            ])
        )

async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик Telegram pre-checkout запроса"""
    query = update.pre_checkout_query
    
    # Извлекаем информацию о платеже из payload
    payload = query.invoice_payload
    parts = payload.split(':')
    
    if len(parts) >= 3 and parts[0] == 'payment':
        payment_id = parts[1]
        tariff = parts[2]
        
        # Подтверждаем pre-checkout
        await query.answer(ok=True)
    else:
        # Отклоняем платеж при некорректных данных
        await query.answer(ok=False, error_message="Ошибка обработки платежа. Пожалуйста, попробуйте позже.")

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик успешного платежа через Telegram Payments"""
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    
    # Извлекаем информацию о платеже из payload
    payload = payment.invoice_payload
    parts = payload.split(':')
    
    if len(parts) >= 3 and parts[0] == 'payment':
        payment_id = parts[1]
        tariff = parts[2]
        
        # Обрабатываем успешный платеж
        success = await payment_service.process_successful_payment(
            user_id=user_id, 
            telegram_payment_id=payment.telegram_payment_charge_id,
            tariff=tariff
        )
        
        # Получаем обновленные данные пользователя
        user = await get_user(user_id)
        
        # Формируем сообщение об успешной оплате
        if user.is_unlimited:
            message = (
                "✅ Оплата успешно выполнена!\n\n"
                "💫 У вас активирован безлимитный тариф. "
                "Теперь вы можете задавать неограниченное количество вопросов!"
            )
        else:
            message = (
                f"✅ Оплата успешно выполнена!\n\n"
                f"💎 Ваш текущий баланс: {user.tokens} Майндтокенов."
            )
        
        # Создаем клавиатуру для возврата в диалог
        keyboard = [
            [InlineKeyboardButton("💬 Вернуться к диалогу", callback_data="start_chat")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text=message,
            reply_markup=reply_markup
        )
    else:
        # Обработка ошибки платежа
        await update.message.reply_text(
            text=(
                "⚠️ Произошла ошибка при обработке платежа. "
                "Пожалуйста, свяжитесь с администратором."
            )
        )

async def back_to_main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопки 'Назад'"""
    query = update.callback_query
    await query.answer()
    
    # Возвращаемся к основному меню
    from handlers.start import show_main_menu
    await show_main_menu(update, context, show_description=False) 