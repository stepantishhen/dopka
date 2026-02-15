import logging
from fastapi import APIRouter, Depends, HTTPException

from backend.routers.auth import require_teacher
from backend.models.user_db import User
from backend.repositories import student_analytics as student_analytics_repo

logger = logging.getLogger("exam_system.teacher")
router = APIRouter()


@router.get("/students")
async def list_students_with_analytics(
    _: User = Depends(require_teacher),
):
    try:
        students = student_analytics_repo.list_students_with_analytics()
        return {"students": students}
    except Exception as e:
        logger.exception("list_students_with_analytics error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/students/{student_id}/analytics")
async def get_student_analytics(
    student_id: str,
    _: User = Depends(require_teacher),
):
    try:
        sessions = student_analytics_repo.get_by_student_id(student_id)
        return {"student_id": student_id, "sessions": sessions}
    except Exception as e:
        logger.exception("get_student_analytics error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
