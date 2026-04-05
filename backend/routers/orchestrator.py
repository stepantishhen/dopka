import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any

from backend.schemas.orchestrator import (
    SessionCreate, SessionResponse, SessionCompleteResponse,
    AnswerSubmission, AnswerResponse, NextQuestionRequest, InsightsRequest, InsightsResponse,
    PretestSubmission, PretestCompleteResponse,
)
from backend.services.orchestrator import CoreOrchestrator

logger = logging.getLogger("exam_system.orchestrator")
router = APIRouter()


def get_orchestrator(request: Request) -> CoreOrchestrator:
    return request.app.state.orchestrator


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    request: Request,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator)
):
    logger.info("create_session student_id=%s exam_id=%s", session_data.student_id, session_data.exam_id)
    exam_service = getattr(request.app.state, "exam_service", None)
    session = orchestrator.create_session(
        student_id=session_data.student_id,
        exam_id=session_data.exam_id,
        exam_service=exam_service,
    )
    # Первый вопрос выдаётся только через POST .../next-question (единый порядок и shuffle)
    logger.info("create_session success session_id=%s", session.session_id)
    return SessionResponse(
        session_id=session.session_id,
        student_id=session.student_id,
        exam_id=session.exam_id,
        current_question_id=session.current_question_id,
        status=session.status.value if hasattr(session.status, "value") else "active",
        created_at=session.created_at,
        updated_at=session.updated_at,
        exam_flow_phase=session.exam_flow_phase,
        pretest_completed=session.pretest_completed,
    )


@router.post("/sessions/{session_id}/answer", response_model=AnswerResponse)
async def submit_answer(
    session_id: str,
    submission: AnswerSubmission,
    request: Request = None,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator)
):
    logger.info("submit_answer session_id=%s question_id=%s answer_len=%s",
                session_id, submission.question_id, len(submission.answer or ""))
    if submission.session_id != session_id:
        logger.warning("submit_answer session_id mismatch")
        raise HTTPException(status_code=400, detail="Session ID mismatch")
    question_data = dict(submission.question_data or {})
    session = orchestrator.get_session(session_id)
    total_so_far, _ = orchestrator._session_scores(session) if session else (0, 0)
    remaining = max(0, 100 - (total_so_far or 0))
    if session and session.exam_id:
        exam_service = getattr(request.app.state, "exam_service", None)
        if exam_service:
            exam = exam_service.get_exam(session.exam_id)
            if exam and getattr(exam, "questions", None):
                M = len(exam.questions)
                question_data["total_questions"] = M
                question_data["question_number"] = len(session.answered_questions) + 1
                question_data["max_score_for_this_question"] = min(100.0 / M, remaining) if M else remaining
    if "max_score_for_this_question" not in question_data:
        question_data["max_score_for_this_question"] = remaining if remaining > 0 else 100.0
    try:
        result = await orchestrator.process_student_answer(
            session_id=session_id,
            question_id=submission.question_id,
            answer=submission.answer,
            question_data=question_data
        )
        logger.info("submit_answer success session_id=%s is_correct=%s", session_id, result.get("is_correct"))
        return AnswerResponse(**result)
    except ValueError as e:
        msg = str(e)
        if "завершён" in msg or "completed" in msg.lower():
            raise HTTPException(status_code=403, detail=msg)
        logger.warning("submit_answer ValueError session_id=%s: %s", session_id, e)
        raise HTTPException(status_code=404, detail=msg)
    except Exception as e:
        logger.exception("submit_answer error session_id=%s: %s", session_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/complete", response_model=SessionCompleteResponse)
async def complete_session(
    session_id: str,
    request: Request = None,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator)
):
    try:
        session = orchestrator.get_session(session_id)
        student_id = session.student_id if session else None
        result = orchestrator.complete_session(session_id)
        if student_id:
            try:
                await orchestrator.generate_insights(session_id, student_id)
            except Exception as ex:
                logger.warning("complete_session: generate_insights failed session_id=%s: %s", session_id, ex)
        return SessionCompleteResponse(**result)
    except ValueError as e:
        logger.warning("complete_session ValueError session_id=%s: %s", session_id, e)
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    request: Request = None,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator)
):
    logger.debug("get_session session_id=%s", session_id)
    session = orchestrator.get_session(session_id)
    if not session:
        logger.warning("get_session not found session_id=%s", session_id)
        raise HTTPException(status_code=404, detail="Session not found")
    status_str = session.status.value if hasattr(session.status, "value") else str(session.status)
    total_score, max_total = None, None
    if status_str == "completed":
        total_score, max_total = orchestrator._session_scores(session)
    return SessionResponse(
        session_id=session.session_id,
        student_id=session.student_id,
        exam_id=session.exam_id,
        current_question_id=session.current_question_id,
        status=status_str,
        created_at=session.created_at,
        updated_at=session.updated_at,
        total_score=total_score,
        max_total_score=max_total,
        questions_answered=len(session.answered_questions) if status_str == "completed" else None,
        passed=(min(100, total_score or 0) >= 56) if (total_score is not None) else None,
        exam_flow_phase=session.exam_flow_phase,
        pretest_completed=session.pretest_completed,
    )


@router.post("/sessions/{session_id}/pretest", response_model=PretestCompleteResponse)
async def complete_pretest(
    session_id: str,
    body: PretestSubmission,
    request: Request,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    exam_service = getattr(request.app.state, "exam_service", None)
    if not exam_service:
        raise HTTPException(status_code=500, detail="Exam service unavailable")
    try:
        result = orchestrator.complete_pretest(session_id, body.choices, exam_service)
        return PretestCompleteResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/next-question")
async def get_next_question(
    session_id: str,
    request_data: NextQuestionRequest,
    request: Request,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator)
):
    logger.info("get_next_question session_id=%s", session_id)
    exam_service = getattr(request.app.state, "exam_service", None)
    try:
        question = await orchestrator.get_next_question(
            session_id=session_id,
            exam_config=request_data.exam_config,
            exam_service=exam_service,
        )
        logger.info("get_next_question success session_id=%s has_question=%s", session_id, question is not None)
        return {"question": question}
    except ValueError as e:
        msg = str(e)
        if "завершён" in msg or "completed" in msg.lower():
            raise HTTPException(status_code=403, detail=msg)
        if "входной тест" in msg:
            raise HTTPException(status_code=400, detail=msg)
        logger.warning("get_next_question ValueError session_id=%s: %s", session_id, e)
        raise HTTPException(status_code=404, detail=msg)
    except Exception as e:
        logger.exception("get_next_question error session_id=%s: %s", session_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/dialogue")
async def get_dialogue(
    session_id: str,
    request: Request = None,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator)
):
    logger.debug("get_dialogue session_id=%s", session_id)
    session = orchestrator.get_session(session_id)
    if not session:
        logger.warning("get_dialogue not found session_id=%s", session_id)
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "dialogue_history": session.dialogue_history,
        "knowledge_gaps": session.knowledge_gaps
    }


@router.post("/sessions/{session_id}/insights", response_model=InsightsResponse)
async def get_insights(
    session_id: str,
    request_data: InsightsRequest,
    request: Request = None,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator)
):
    logger.info("get_insights session_id=%s student_id=%s", session_id, request_data.student_id)
    try:
        insights = await orchestrator.generate_insights(
            session_id=session_id,
            student_id=request_data.student_id
        )
        logger.info("get_insights success session_id=%s", session_id)
        return InsightsResponse(**insights)
    except ValueError as e:
        logger.warning("get_insights ValueError session_id=%s: %s", session_id, e)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("get_insights error session_id=%s: %s", session_id, e)
        raise HTTPException(status_code=500, detail=str(e))

