from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.services.knowledge_service import KnowledgeService
from backend.services.exam_service import ExamService
from backend.services.chat_service import ChatService
from backend.services.orchestrator import CoreOrchestrator
from backend.services.logging_service import logging_service
from backend.middleware import LoggingMiddleware
from backend.routers import knowledge_base, exams, students, chat
from backend.routers import orchestrator as orchestrator_router

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
app.add_middleware(LoggingMiddleware)

knowledge_service = KnowledgeService()
exam_service = ExamService(knowledge_service)
chat_service = ChatService()
orchestrator = CoreOrchestrator(knowledge_service)

app.state.knowledge_service = knowledge_service
app.state.exam_service = exam_service
app.state.chat_service = chat_service
app.state.orchestrator = orchestrator

app.include_router(knowledge_base.router, prefix="/api/knowledge-base", tags=["knowledge-base"])
app.include_router(exams.router, prefix="/api/exams", tags=["exams"])
app.include_router(students.router, prefix="/api/students", tags=["students"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(orchestrator_router.router, prefix="/api/orchestrator", tags=["orchestrator"])


@app.get("/")
async def root():
    return {"message": "Система обучения API", "version": "1.0.0"}


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/metrics")
async def get_metrics():
    return logging_service.get_metrics_summary()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

