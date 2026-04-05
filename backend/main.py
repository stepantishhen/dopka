import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.services.knowledge_service import KnowledgeService
from backend.services.exam_service import ExamService
from backend.services.chat_service import ChatService
from backend.services.orchestrator import CoreOrchestrator
from backend.services.llm_client import LLMClient
from backend.services.logging_service import logging_service
from backend.middleware import LoggingMiddleware
from backend.database import init_db
from backend.routers import knowledge_base, exams, students, chat, auth, teacher, dev as dev_router
from backend.routers import orchestrator as orchestrator_router

os.environ.setdefault("TZ", "Europe/Moscow")
logger = logging.getLogger("exam_system")

# Сервисы до app: lifespan и startup используют их в правильном порядке
knowledge_service = KnowledgeService()
exam_service = ExamService(knowledge_service)
chat_service = ChatService()
orchestrator = CoreOrchestrator(knowledge_service)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1) Сначала LLM — до init_db и долгих операций, чтобы проверка всегда была в логах
    # Результат кладём в app.state — GET /api/health отдаёт его без новых запросов к LLM
    if not settings.llm_skip_startup_check:
        logger.info("startup: проверка LLM (check_connection)...")
        llm = LLMClient()
        ok, msg = llm.check_connection()
        app.state.llm_at_startup = {"skipped": False, "ok": ok, "detail": msg}
        if ok:
            logger.info("startup: LLM OK — %s", msg)
        else:
            logger.warning(
                "startup: LLM не прошёл проверку (%s). Задайте OPENAI_API_KEY и OPENAI_BASE_URL "
                "(например ProxyAPI OpenRouter) или установите LLM_SKIP_STARTUP_CHECK=true.",
                msg,
            )
    else:
        logger.info("startup: проверка LLM отключена (llm_skip_startup_check)")
        app.state.llm_at_startup = {"skipped": True, "ok": None, "detail": "llm_skip_startup_check"}

    logger.info("startup: initializing database")
    init_db()
    if settings.seed_test_env:
        from backend.services.test_environment import seed_test_environment

        seed_test_environment(knowledge_service, exam_service, seed_users=True)
        logger.info("startup: test environment seeded (SEED_TEST_ENV)")
    else:
        exam_service.get_or_create_test_exam()
    logger.info("startup: ready timezone=%s test_exam_id=exam_test", os.environ.get("TZ", "not set"))

    yield


app = FastAPI(
    title="Система обучения с виртуальным экзаменатором",
    description="API для системы обучения студентов и преподавателей",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)

app.state.knowledge_service = knowledge_service
app.state.exam_service = exam_service
app.state.chat_service = chat_service
app.state.orchestrator = orchestrator

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(knowledge_base.router, prefix="/api/knowledge-base", tags=["knowledge-base"])
app.include_router(exams.router, prefix="/api/exams", tags=["exams"])
app.include_router(students.router, prefix="/api/students", tags=["students"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(orchestrator_router.router, prefix="/api/orchestrator", tags=["orchestrator"])
app.include_router(teacher.router, prefix="/api/teacher", tags=["teacher"])
app.include_router(dev_router.router, prefix="/api/dev", tags=["dev"])


@app.get("/")
async def root():
    return {"message": "Система обучения API", "version": "1.0.0"}


@app.get("/api/health")
async def health_check(request: Request):
    """
    Лёгкий ping для Docker/orchestrator (без вызова LLM).
    Частые GET сюда из docker-compose healthcheck — это не повторная проверка LLM,
    а только «процесс жив». Результат проверки LLM при старте — в поле llm.
    Живой запрос к API провайдера: GET /api/health/llm
    """
    logger.debug("health_check")
    out = {"status": "ok"}
    ls = getattr(request.app.state, "llm_at_startup", None)
    if ls is not None:
        out["llm"] = ls
    return out


@app.get("/api/health/llm")
async def health_llm():
    """Повторная проверка доступности LLM (тот же запрос, что при старте)."""
    llm = LLMClient()
    ok, msg = llm.check_connection()
    if ok:
        return {"status": "ok", "detail": msg}
    return JSONResponse(
        status_code=503,
        content={"status": "error", "detail": msg},
    )


@app.get("/api/metrics")
async def get_metrics():
    return logging_service.get_metrics_summary()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
