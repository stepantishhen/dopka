"""
Эндпоинты только для разработки / тестовой среды (описание предзаполненных данных).
"""
from fastapi import APIRouter, HTTPException, Request

from backend.config import settings
from backend.services.test_environment import test_environment_payload

router = APIRouter()


def _check_dev_enabled():
    if not (settings.debug or settings.seed_test_env):
        raise HTTPException(status_code=404, detail="Not available")


@router.get("/test-environment")
async def get_test_environment(request: Request):
    """Сводка: код экзамена TEST01, тестовые логины, ссылки для фронтенда."""
    _check_dev_enabled()
    ks = request.app.state.knowledge_service
    es = request.app.state.exam_service
    return test_environment_payload(ks, es)
