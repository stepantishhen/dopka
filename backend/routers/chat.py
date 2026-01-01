from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Optional
from datetime import datetime

from backend.schemas.chat import ChatCreate, ChatResponse, MessageSend
from backend.services.chat_service import ChatService


router = APIRouter()


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service


@router.post("/", response_model=ChatResponse)
async def create_chat(
    chat_data: ChatCreate,
    request: Request = None,
    service: ChatService = Depends(get_chat_service)
):
    title = chat_data.title or "Новый экзамен"
    chat_id = service.create_chat(title)
    chat = service.get_chat(chat_id)
    
    return ChatResponse(
        id=chat["id"],
        title=chat["title"],
        messages=chat["messages"],
        createdAt=chat["createdAt"],
        updatedAt=chat["updatedAt"]
    )


@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: str,
    request: Request = None,
    service: ChatService = Depends(get_chat_service)
):
    chat = service.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    
    return ChatResponse(
        id=chat["id"],
        title=chat["title"],
        messages=chat["messages"],
        createdAt=chat["createdAt"],
        updatedAt=chat["updatedAt"]
    )


@router.post("/{chat_id}/message")
async def send_message(
    chat_id: str,
    message_data: MessageSend,
    request: Request = None,
    service: ChatService = Depends(get_chat_service)
):
    chat = service.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    
    user_message = {
        "id": f"msg_{datetime.now().timestamp()}",
        "text": message_data.message,
        "sender": "user",
        "timestamp": datetime.now().isoformat()
    }
    
    service.add_message(chat_id, user_message)
    
    context = chat["messages"]
    ai_response_text = service.generate_ai_response(message_data.message, context)
    
    ai_message = {
        "id": f"msg_{datetime.now().timestamp()}_ai",
        "text": ai_response_text,
        "sender": "ai",
        "timestamp": datetime.now().isoformat()
    }
    
    service.add_message(chat_id, ai_message)
    
    updated_chat = service.get_chat(chat_id)
    
    return ChatResponse(
        id=updated_chat["id"],
        title=updated_chat["title"],
        messages=updated_chat["messages"],
        createdAt=updated_chat["createdAt"],
        updatedAt=updated_chat["updatedAt"]
    )


@router.get("/")
async def list_chats(
    request: Request = None,
    service: ChatService = Depends(get_chat_service)
):
    chats = [
        ChatResponse(
            id=chat["id"],
            title=chat["title"],
            messages=chat["messages"],
            createdAt=chat["createdAt"],
            updatedAt=chat["updatedAt"]
        )
        for chat in service.chats.values()
    ]
    return {"chats": chats, "count": len(chats)}

