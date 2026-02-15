import logging
from typing import Dict, List, Optional
from datetime import datetime

from backend.services.llm_client import LLMClient

logger = logging.getLogger("exam_system.chat_service")


class ChatService:
    def __init__(self):
        self.llm = LLMClient()
        self.chats: Dict[str, Dict] = {}
    
    def generate_ai_response(self, user_message: str, context: Optional[List[Dict]] = None) -> str:
        context_text = ""
        if context:
            context_text = "\n".join([f"{msg.get('sender', 'user')}: {msg.get('text', '')}" 
                                    for msg in context[-5:]])
        
        system_prompt = "Ты опытный преподаватель, помогающий студентам в обучении. Отвечай дружелюбно и конструктивно."
        user_prompt = f"""Контекст диалога:
{context_text}

Сообщение студента: {user_message}

Ответь на вопрос студента или помоги ему разобраться в теме."""
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            logger.debug("generate_ai_response message_len=%s context_messages=%s", len(user_message), len(context or []))
            out = self.llm.chat(messages, temperature=0.7, max_tokens=500)
            logger.debug("generate_ai_response response_len=%s", len(out))
            return out
        except Exception as e:
            logger.exception("generate_ai_response error: %s", e)
            return "Извините, произошла ошибка. Попробуйте еще раз."
    
    def create_chat(self, title: str = "Новый экзамен") -> str:
        chat_id = f"chat_{datetime.now().timestamp()}"
        self.chats[chat_id] = {
            "id": chat_id,
            "title": title,
            "messages": [],
            "createdAt": datetime.now().isoformat(),
            "updatedAt": datetime.now().isoformat()
        }
        return chat_id
    
    def get_chat(self, chat_id: str) -> Optional[Dict]:
        return self.chats.get(chat_id)
    
    def add_message(self, chat_id: str, message: Dict):
        if chat_id in self.chats:
            self.chats[chat_id]["messages"].append(message)
            self.chats[chat_id]["updatedAt"] = datetime.now().isoformat()
            
            if len(self.chats[chat_id]["messages"]) == 1:
                text = message.get("text", "")
                if len(text) > 30:
                    text = text[:30] + "..."
                self.chats[chat_id]["title"] = text

