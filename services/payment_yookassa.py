import uuid
import logging
import traceback
import json
import sys
from typing import Dict, Optional, Tuple
from datetime import datetime

try:
    import yookassa
    from yookassa import Configuration, Payment as YooKassaPayment
    from yookassa.domain.exceptions import ApiError, BadRequestError, AuthorizationError
    YOOKASSA_AVAILABLE = True
except ImportError as e:
    YOOKASSA_AVAILABLE = False
    print(f"❌ Ошибка импорта YooKassa: {str(e)}")

import config
from database.models import Payment
from database import create_payment, update_payment_status, add_tokens, set_unlimited_status

# Инициализация логирования
logger = logging.getLogger(__name__)
# Добавляем обработчик для вывода логов в консоль
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# Статус доступности YooKassa
YOOKASSA_INITIALIZED = False

# Вывод информации о версии Python и модулях
logger.info(f"Python версия: {sys.version}")
logger.info(f"YooKassa доступна: {YOOKASSA_AVAILABLE}")

# Инициализация библиотеки ЮKassa с данными из конфигурации
if YOOKASSA_AVAILABLE:
    try:
        # Получаем настройки из конфигурации
        shop_id = config.YUKASSA_SHOP_ID
        secret_key = config.YUKASSA_SECRET_KEY
        
        if not shop_id or not secret_key:
            logger.error("❌ Отсутствуют настройки YUKASSA_SHOP_ID или YUKASSA_SECRET_KEY")
            logger.error(f"YUKASSA_SHOP_ID: {shop_id}")
            logger.error(f"YUKASSA_SECRET_KEY: {'Задан' if secret_key else 'Не задан'}")
            YOOKASSA_INITIALIZED = False
        else:
            # Явно инициализируем через объект библиотеки
            yookassa.Configuration.account_id = shop_id
            yookassa.Configuration.secret_key = secret_key
            
            # Проверим, что библиотека успешно инициализирована
            logger.info(f"✅ ЮKassa инициализирована с ID магазина: {shop_id}")
            logger.info(f"✅ Ключ: {secret_key[:4]}...{secret_key[-4:] if len(secret_key) > 8 else ''}")
            logger.info(f"✅ Configuration.account_id: {yookassa.Configuration.account_id}")
            YOOKASSA_INITIALIZED = True
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации ЮKassa: {str(e)}")
        logger.error(traceback.format_exc())
        YOOKASSA_INITIALIZED = False
else:
    logger.error("❌ YooKassa не доступна. Проверьте установку библиотеки: pip install yookassa==3.0.0")
    YOOKASSA_INITIALIZED = False

# URL для возврата после платежа из конфигурации или по умолчанию
RETURN_URL = config.YUKASSA_RETURN_URL or "https://t.me/psychologybilalov_bot"

class PaymentService:
    """Сервис для работы с платежной системой ЮKassa (тестовый режим)"""
    
    @staticmethod
    async def create_payment_link(user_id: int, tariff: str) -> Tuple[Optional[str], Optional[Payment]]:
        """Создать платежную ссылку для оплаты тарифа"""
        if not YOOKASSA_AVAILABLE:
            logger.error("❌ Невозможно создать платеж: библиотека YooKassa не установлена")
            return None, None
            
        if not YOOKASSA_INITIALIZED:
            logger.error("❌ Невозможно создать платеж: YooKassa не инициализирована")
            return None, None
            
        if tariff not in config.TARIFFS:
            logger.error(f"❌ Тариф {tariff} не найден в конфигурации")
            logger.info(f"Доступные тарифы: {list(config.TARIFFS.keys())}")
            return None, None
        
        tariff_data = config.TARIFFS[tariff]
        amount = tariff_data['price']
        tokens = tariff_data['tokens']
        
        # Проверка корректности данных тарифа
        if not isinstance(amount, (int, float)) or amount <= 0:
            logger.error(f"❌ Некорректная сумма платежа: {amount}")
            return None, None
        
        idempotence_key = str(uuid.uuid4())
        payment_data = {
            "amount": {
                "value": float(amount),  # Убедимся, что значение передается как float
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": RETURN_URL
            },
            "capture": True,
            "description": f"Оплата тарифа '{tariff}' ({tariff_data['description']})"
        }
        
        logger.info(f"📝 Данные для создания платежа: {json.dumps(payment_data, ensure_ascii=False)}")
        
        try:
            logger.info(f"📊 Создание платежа для пользователя {user_id}, тариф: {tariff}")
            
            # Подробно логируем шаги для отладки
            logger.info(f"🔑 Идемпотентный ключ: {idempotence_key}")
            logger.info(f"🏪 ID аккаунта ЮKassa: {yookassa.Configuration.account_id}")
            logger.info(f"🔒 Секретный ключ (маскированный): {yookassa.Configuration.secret_key[:4]}...{yookassa.Configuration.secret_key[-4:] if len(yookassa.Configuration.secret_key) > 8 else ''}")
            
            # Создаем платеж через глобальную библиотеку yookassa
            response = yookassa.Payment.create(payment_data, idempotence_key)
            
            # Логируем ответ
            logger.info(f"✅ Получен ответ от ЮKassa: {response.json()}")
            logger.info(f"✅ ID платежа: {response.id}, Статус: {response.status}")
            
            # Сохраняем данные о платеже в базу
            payment = Payment(
                payment_id=response.id,
                user_id=user_id,
                tariff=tariff,
                amount=amount,
                tokens=tokens,
                status='pending',
                created_at=datetime.now().isoformat()
            )
            await create_payment(payment)
            
            logger.info(f"✅ Создан платеж {response.id} для пользователя {user_id}")
            logger.info(f"🔗 URL для подтверждения: {response.confirmation.confirmation_url}")
            
            return response.confirmation.confirmation_url, payment
        except BadRequestError as e:
            logger.error(f"❌ Ошибка запроса к YooKassa (неверные параметры): {str(e)}")
            logger.error(f"Код ошибки: {e.error_code}, описание: {e.description}")
            logger.error(traceback.format_exc())
            return None, None
        except AuthorizationError as e:
            logger.error(f"❌ Ошибка авторизации в YooKassa: {str(e)}")
            logger.error(f"Проверьте правильность shopId и секретного ключа.")
            logger.error(traceback.format_exc())
            return None, None
        except ApiError as e:
            logger.error(f"❌ Ошибка API YooKassa: {str(e)}")
            logger.error(traceback.format_exc())
            return None, None
        except Exception as e:
            # Подробное логирование ошибки
            logger.error(f"❌ Общая ошибка при создании платежа: {str(e)}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            logger.error(traceback.format_exc())
            return None, None
    
    @staticmethod
    async def process_payment_notification(payment_data: Dict) -> bool:
        """Обработать уведомление о статусе платежа от ЮKassa"""
        if not YOOKASSA_AVAILABLE:
            logger.error("❌ Невозможно обработать уведомление: библиотека YooKassa не установлена")
            return False
            
        logger.info(f"📩 Получено уведомление от ЮKassa: {json.dumps(payment_data, ensure_ascii=False)}")
        
        payment_id = payment_data.get('object', {}).get('id')
        status = payment_data.get('object', {}).get('status')
        
        if not payment_id or not status:
            logger.warning("⚠️ Получено некорректное уведомление о платеже")
            logger.warning(f"📋 Данные уведомления: {json.dumps(payment_data, ensure_ascii=False)}")
            return False
        
        logger.info(f"🔄 Обработка уведомления о платеже {payment_id}, статус: {status}")
        
        try:
            # Обновляем статус платежа в базе
            payment = await update_payment_status(payment_id, status)
            
            if not payment:
                logger.warning(f"⚠️ Платеж {payment_id} не найден в базе данных")
                return False
            
            logger.info(f"📊 Платеж {payment_id} найден в базе, пользователь: {payment.user_id}, статус обновлен на {status}")
            
            if status == 'succeeded':
                # Если платеж успешный, начисляем токены пользователю
                if payment.tokens == -1:  # Безлимитный тариф
                    logger.info(f"🎉 Активация безлимитного тарифа для пользователя {payment.user_id}")
                    await set_unlimited_status(payment.user_id, True)
                else:
                    logger.info(f"🎉 Начисление {payment.tokens} токенов пользователю {payment.user_id}")
                    await add_tokens(payment.user_id, payment.tokens)
                return True
            
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка при обработке уведомления о платеже: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    @staticmethod
    async def check_payment_status(payment_id: str) -> Optional[str]:
        """Проверить статус платежа"""
        if not YOOKASSA_AVAILABLE:
            logger.error("❌ Невозможно проверить статус платежа: библиотека YooKassa не установлена")
            return None
            
        if not YOOKASSA_INITIALIZED:
            logger.error("❌ Невозможно проверить статус платежа: YooKassa не инициализирована")
            return None
            
        try:
            logger.info(f"🔍 Проверка статуса платежа {payment_id}")
            response = yookassa.Payment.find_one(payment_id)
            logger.info(f"✅ Получен статус платежа {payment_id}: {response.status}")
            return response.status
        except BadRequestError as e:
            logger.error(f"❌ Ошибка запроса к YooKassa (неверный ID платежа): {str(e)}")
            logger.error(traceback.format_exc())
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке статуса платежа {payment_id}: {str(e)}")
            logger.error(traceback.format_exc())
            return None

# Создаем экземпляр для использования в других модулях
payment_service = PaymentService() 