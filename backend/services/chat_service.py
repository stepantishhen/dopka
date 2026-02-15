from typing import Dict, List, Optional
from datetime import datetime
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

from backend.config import settings


class ChatService:
    def __init__(self):
        self.giga = GigaChat(credentials=settings.gigachat_credentials, verify_ssl_certs=False)
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
                Messages(role=MessagesRole.SYSTEM, content=system_prompt),
                Messages(role=MessagesRole.USER, content=user_prompt)
            ]
            payload = Chat(messages=messages, temperature=0.7, max_tokens=500)
            response = self.giga.chat(payload)
            return response.choices[0].message.content
        except Exception as e:
            print(f"Ошибка при генерации ответа: {e}")
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

