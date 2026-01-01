from typing import List, Optional
from pydantic import BaseModel


class ChatMessage(BaseModel):
    id: str
    text: str
    sender: str  # 'user' or 'ai'
    timestamp: str


class ChatCreate(BaseModel):
    title: Optional[str] = None


class ChatResponse(BaseModel):
    id: str
    title: str
    messages: List[ChatMessage]
    createdAt: str
    updatedAt: str


class MessageSend(BaseModel):
    message: str
    chat_id: str

