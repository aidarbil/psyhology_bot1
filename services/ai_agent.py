import aiohttp
import json
import logging
from typing import Dict, Optional, List, Any

import config
from services.vector_memory import vector_memory_service

# Настраиваем логирование
logger = logging.getLogger(__name__)

class AIAgent:
    """Класс для работы с API ИИ-агента с поддержкой векторной памяти"""
    
    def __init__(self, agent_id: str = config.AI_AGENT_ID, api_url: str = config.AI_AGENT_URL):
        self.agent_id = agent_id
        self.api_url = api_url
        logger.info(f"Инициализирован AI агент: agent_id={agent_id}, api_url={api_url}")
    
    async def send_message(self, message: str, user_id: int = None, stream: bool = False) -> Optional[str]:
        """
        Отправить сообщение ИИ-агенту и получить ответ.
        Поддерживает векторную память, если указан user_id.
        
        Args:
            message: Текст сообщения
            user_id: ID пользователя для сохранения контекста
            stream: Использовать ли потоковую передачу ответа
            
        Returns:
            str: Ответ от ИИ-агента
        """
        
        # Базовый payload с обязательными параметрами
        payload = {
            "agent_id": self.agent_id,
            "message": message,
            "stream": stream
        }
        
        # Если указан user_id, добавляем его в запрос для поддержки векторной памяти на стороне API
        if user_id is not None:
            # Преобразуем user_id в строку, т.к. некоторые API ожидают строковые идентификаторы
            payload["user_id"] = str(user_id)
            
            # Также добавляем сообщение в локальную память для резервного хранения
            await vector_memory_service.add_message(user_id, "user", message)
            
            logger.info(f"Отправка сообщения пользователя {user_id} AI агенту: {message[:50]}...")
        else:
            logger.info(f"Отправка сообщения AI агенту без user_id: {message[:50]}...")
        
        logger.debug(f"Полезная нагрузка запроса к API: {json.dumps(payload)}")
        
        try:
            async with aiohttp.ClientSession() as session:
                logger.debug(f"Отправка POST запроса на {self.api_url}")
                
                async with session.post(self.api_url, json=payload) as response:
                    status_code = response.status
                    logger.debug(f"Получен ответ от API с кодом: {status_code}")
                    
                    if status_code == 200:
                        result = await response.json()
                        logger.debug(f"Успешный ответ от API: {json.dumps(result)[:200]}...")
                        
                        if stream:
                            # Обработка потокового ответа если понадобится
                            pass
                        
                        response_text = result.get('response', '')
                        
                        # Если используется векторная память, сохраняем ответ ассистента в локальную память
                        if user_id is not None:
                            await vector_memory_service.add_message(user_id, "assistant", response_text)
                            logger.info(f"Сохранен ответ AI агента для пользователя {user_id}: {response_text[:50]}...")
                        
                        return response_text
                    else:
                        response_content = await response.text()
                        logger.error(f"Ошибка при запросе к ИИ-агенту: {status_code} - {response_content}")
                        return None
        except Exception as e:
            logger.exception(f"Исключение при запросе к ИИ-агенту: {str(e)}")
            return None
    
    async def clear_memory(self, user_id: int) -> None:
        """Очистить историю диалога для пользователя в локальной памяти"""
        logger.info(f"Очистка памяти для пользователя {user_id}")
        await vector_memory_service.clear_memory(user_id)

# Создаем экземпляр для использования в других модулях
ai_agent = AIAgent() 