from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.services.knowledge_service import KnowledgeService
from backend.services.exam_service import ExamService
from backend.services.chat_service import ChatService
from backend.routers import knowledge_base, exams, students, chat

app = FastAPI(
    title="Система обучения с виртуальным экзаменатором",
    description="API для системы обучения студентов и преподавателей",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

knowledge_service = KnowledgeService()
exam_service = ExamService(knowledge_service)
chat_service = ChatService()

app.state.knowledge_service = knowledge_service
app.state.exam_service = exam_service
app.state.chat_service = chat_service

app.include_router(knowledge_base.router, prefix="/api/knowledge-base", tags=["knowledge-base"])
app.include_router(exams.router, prefix="/api/exams", tags=["exams"])
app.include_router(students.router, prefix="/api/students", tags=["students"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


@app.get("/")
async def root():
    return {"message": "Система обучения API", "version": "1.0.0"}


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

