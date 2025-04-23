import logging
import json
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class VectorMemoryService:
    """
    Сервис для работы с векторной памятью агента.
    Обеспечивает сохранение и извлечение контекста диалога для каждого пользователя.
    """
    
    def __init__(self):
        self.user_memories = {}  # Словарь для хранения контекста диалогов по user_id
        logger.info("Инициализирован сервис векторной памяти")
    
    async def get_memory(self, user_id: int) -> List[Dict[str, str]]:
        """
        Получает текущий контекст диалога для пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            List[Dict[str, str]]: Список сообщений диалога в формате [{role: "user"/"assistant", content: "текст"}]
        """
        if user_id not in self.user_memories:
            self.user_memories[user_id] = []
        
        return self.user_memories[user_id]
    
    async def add_message(self, user_id: int, role: str, content: str) -> None:
        """
        Добавляет сообщение в контекст диалога пользователя
        
        Args:
            user_id: ID пользователя
            role: Роль отправителя (user/assistant)
            content: Текст сообщения
        """
        if user_id not in self.user_memories:
            self.user_memories[user_id] = []
        
        # Добавляем сообщение в историю
        self.user_memories[user_id].append({
            "role": role,
            "content": content
        })
        
        # Ограничиваем длину истории, чтобы избежать переполнения контекста
        if len(self.user_memories[user_id]) > 20:
            self.user_memories[user_id] = self.user_memories[user_id][-20:]
        
        logger.debug(f"Добавлено сообщение в память пользователя {user_id}: {role}: {content[:30]}...")
    
    async def clear_memory(self, user_id: int) -> None:
        """
        Очищает историю диалога для пользователя
        
        Args:
            user_id: ID пользователя
        """
        self.user_memories[user_id] = []
        logger.info(f"Очищена память пользователя {user_id}")
    
    async def prepare_context_for_agent(self, user_id: int) -> str:
        """
        Подготавливает контекст в формате, подходящем для отправки AI агенту
        
        Args:
            user_id: ID пользователя
            
        Returns:
            str: JSON-строка с контекстом диалога
        """
        memory = await self.get_memory(user_id)
        return json.dumps({"messages": memory})
    
    async def extract_agent_response(self, agent_response: Dict[str, Any]) -> str:
        """
        Извлекает ответ из ответа агента
        
        Args:
            agent_response: Ответ от AI агента
            
        Returns:
            str: Текст ответа
        """
        # Обработка разных форматов ответа агента
        if isinstance(agent_response, dict):
            if "response" in agent_response:
                return agent_response["response"]
            elif "content" in agent_response:
                return agent_response["content"]
            elif "text" in agent_response:
                return agent_response["text"]
            elif "message" in agent_response:
                return agent_response["message"]
        
        # Если не удалось извлечь ответ, возвращаем исходный ответ строкой
        return str(agent_response)

# Создаем экземпляр сервиса
vector_memory_service = VectorMemoryService() 