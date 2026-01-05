from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any

from backend.schemas.orchestrator import (
    SessionCreate, SessionResponse, AnswerSubmission,
    AnswerResponse, NextQuestionRequest, InsightsRequest, InsightsResponse
)
from backend.services.orchestrator import CoreOrchestrator


router = APIRouter()


def get_orchestrator(request: Request) -> CoreOrchestrator:
    return request.app.state.orchestrator


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    request: Request = None,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator)
):
    session = orchestrator.create_session(
        student_id=session_data.student_id,
        exam_id=session_data.exam_id
    )
    
    return SessionResponse(
        session_id=session.session_id,
        student_id=session.student_id,
        exam_id=session.exam_id,
        current_question_id=session.current_question_id,
        status="active",
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.post("/sessions/{session_id}/answer", response_model=AnswerResponse)
async def submit_answer(
    session_id: str,
    submission: AnswerSubmission,
    request: Request = None,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator)
):
    if submission.session_id != session_id:
        raise HTTPException(status_code=400, detail="Session ID mismatch")
    
    try:
        result = await orchestrator.process_student_answer(
            session_id=session_id,
            question_id=submission.question_id,
            answer=submission.answer,
            question_data=submission.question_data
        )
        
        return AnswerResponse(**result)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    request: Request = None,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator)
):
    session = orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionResponse(
        session_id=session.session_id,
        student_id=session.student_id,
        exam_id=session.exam_id,
        current_question_id=session.current_question_id,
        status="active",
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.post("/sessions/{session_id}/next-question")
async def get_next_question(
    session_id: str,
    request_data: NextQuestionRequest,
    request: Request = None,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator)
):
    try:
        question = await orchestrator.get_next_question(
            session_id=session_id,
            exam_config=request_data.exam_config
        )
        
        return {"question": question}
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/dialogue")
async def get_dialogue(
    session_id: str,
    request: Request = None,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator)
):
    session = orchestrator.get_session(session_id)
    if not session:
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
    try:
        insights = await orchestrator.generate_insights(
            session_id=session_id,
            student_id=request_data.student_id
        )
        
        return InsightsResponse(**insights)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

