from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

import config
from database import get_user
from services import payment_service

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
    
    # Создаем платежную ссылку
    payment_url, payment = await payment_service.create_payment_link(user_id, tariff)
    
    if not payment_url:
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
    
    # Создаем клавиатуру с кнопкой оплаты
    keyboard = [
        [InlineKeyboardButton("💳 Перейти к оплате", url=payment_url)],
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

async def check_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик проверки статуса платежа"""
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

async def back_to_main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопки 'Назад'"""
    query = update.callback_query
    await query.answer()
    
    # Возвращаемся к основному меню
    from handlers.start import start_command
    await start_command(update, context) 