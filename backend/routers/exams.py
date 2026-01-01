from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Optional

from backend.schemas.exams import (
    ExamCreate, ExamResponse, ExamSubmission, EvaluationResponse
)
from backend.services.exam_service import ExamService
from backend.models.exam_system import ExamConfig, StudentAnswer


router = APIRouter()


def get_exam_service(request: Request) -> ExamService:
    return request.app.state.exam_service


@router.post("/", response_model=ExamResponse)
async def create_exam(
    exam_data: ExamCreate,
    request: Request = None,
    service: ExamService = Depends(get_exam_service)
):
    exam_config = ExamConfig(**exam_data.dict())
    exam = service.create_exam(exam_config)
    return ExamResponse(**exam.dict())


@router.get("/current", response_model=Optional[ExamResponse])
async def get_current_exam(
    request: Request = None,
    service: ExamService = Depends(get_exam_service)
):
    exam = service.get_current_exam()
    if not exam:
        return None
    return ExamResponse(**exam.dict())


@router.get("/{exam_id}", response_model=ExamResponse)
async def get_exam(
    exam_id: str,
    request: Request = None,
    service: ExamService = Depends(get_exam_service)
):
    exam = service.get_exam(exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Экзамен не найден")
    return ExamResponse(**exam.dict())


@router.post("/{exam_id}/submit", response_model=EvaluationResponse)
async def submit_exam(
    exam_id: str,
    submission: ExamSubmission,
    request: Request = None,
    service: ExamService = Depends(get_exam_service)
):
    exam = service.get_exam(exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Экзамен не найден")
    
    answers = [StudentAnswer(**ans.dict()) for ans in submission.answers]
    evaluation = service.evaluate_student_answers(submission.student_id, answers)
    
    return EvaluationResponse(**evaluation)


@router.get("/")
async def list_exams(
    request: Request = None,
    service: ExamService = Depends(get_exam_service)
):
    exams = [ExamResponse(**exam.dict()) for exam in service.exams.values()]
    return {"exams": exams, "count": len(exams)}

