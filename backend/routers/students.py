import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List

from backend.schemas.students import (
    StudentCreate, StudentResponse, StudentProfileResponse,
    EmotionalStateRequest, DiagnosticRequest, DiagnosticResponse
)
from backend.services.exam_service import ExamService

logger = logging.getLogger("exam_system.students")
router = APIRouter()


def get_exam_service(request: Request) -> ExamService:
    return request.app.state.exam_service


@router.post("/", response_model=StudentResponse)
async def create_student(
    student_data: StudentCreate,
    request: Request = None,
    service: ExamService = Depends(get_exam_service)
):
    from datetime import datetime
    logger.info("create_student name=%s group=%s", student_data.name, student_data.group)
    student_id = f"{student_data.name}_{student_data.group or 'default'}_{datetime.now().timestamp()}"
    profile = service.get_or_create_student(student_id, student_data.name, student_data.group or "")
    logger.info("create_student success student_id=%s", profile.student_id)
    return StudentResponse(
        student_id=profile.student_id,
        name=profile.name,
        group=profile.group,
        created_at=profile.created_at,
        emotional_state=profile.emotional_state.dict() if profile.emotional_state else None
    )


@router.get("/{student_id}", response_model=StudentProfileResponse)
async def get_student_profile(
    student_id: str,
    request: Request = None,
    service: ExamService = Depends(get_exam_service)
):
    logger.debug("get_student_profile student_id=%s", student_id)
    if student_id not in service.student_profiles:
        logger.warning("get_student_profile not found student_id=%s", student_id)
        raise HTTPException(status_code=404, detail="Студент не найден")
    
    profile = service.student_profiles[student_id]
    return StudentProfileResponse(
        student_id=profile.student_id,
        name=profile.name,
        group=profile.group,
        created_at=profile.created_at,
        knowledge_map=profile.knowledge_map,
        emotional_state=profile.emotional_state.dict() if profile.emotional_state else None,
        learning_history=profile.learning_history,
        last_evaluation=profile.last_evaluation
    )


@router.post("/{student_id}/emotional-state")
async def assess_emotional_state(
    student_id: str,
    request_data: EmotionalStateRequest,
    request: Request = None,
    service: ExamService = Depends(get_exam_service)
):
    emotional_state = service.assess_emotional_state(student_id, request_data.responses)
    return emotional_state.dict()


@router.post("/{student_id}/diagnostic", response_model=DiagnosticResponse)
async def diagnose_knowledge_gaps(
    student_id: str,
    diagnostic_data: DiagnosticRequest,
    request: Request = None,
    service: ExamService = Depends(get_exam_service)
):
    from datetime import datetime
    logger.info("diagnose_knowledge_gaps student_id=%s", student_id)
    service.get_or_create_student(student_id)
    
    questions = []
    knowledge_service = request.app.state.knowledge_service
    units = knowledge_service.get_all_units()
    
    for unit in units[:10]:
        if unit.get("questions", {}).get("understanding"):
            q = unit["questions"]["understanding"][0]
            q["unit_id"] = unit["unit_id"]
            questions.append(q)
            if len(questions) >= 10:
                break
    
    diagnostic_id = f"diag_{student_id}_{datetime.now().strftime('%Y%m%d')}"
    logger.info("diagnose_knowledge_gaps success diagnostic_id=%s questions=%s", diagnostic_id, len(questions[:10]))
    return DiagnosticResponse(
        diagnostic_id=diagnostic_id,
        questions=questions[:10],
        estimated_time=len(questions) * 2
    )


@router.get("/")
async def list_students(
    request: Request = None,
    service: ExamService = Depends(get_exam_service)
):
    logger.debug("list_students count=%s", len(service.student_profiles))
    students = [
        StudentResponse(
            student_id=profile.student_id,
            name=profile.name,
            group=profile.group,
            created_at=profile.created_at,
            emotional_state=profile.emotional_state.dict() if profile.emotional_state else None
        )
        for profile in service.student_profiles.values()
    ]
    return {"students": students, "count": len(students)}

