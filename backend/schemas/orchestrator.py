from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class SessionCreate(BaseModel):
    student_id: str
    exam_id: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str
    student_id: str
    exam_id: Optional[str] = None
    current_question_id: Optional[str] = None
    status: str
    created_at: str
    updated_at: str


class AnswerSubmission(BaseModel):
    session_id: str
    question_id: str
    answer: str
    question_data: Dict[str, Any]


class AnswerResponse(BaseModel):
    evaluation: Dict[str, Any]
    is_correct: bool
    score: float
    max_score: float
    clarification: Optional[str] = None
    error_analysis: Optional[Dict[str, Any]] = None
    reasoning_analysis: Optional[Dict[str, Any]] = None
    tactic: Optional[str] = None
    feedback: Optional[str] = None


class NextQuestionRequest(BaseModel):
    session_id: str
    exam_config: Dict[str, Any]


class InsightsRequest(BaseModel):
    session_id: str
    student_id: str


class InsightsResponse(BaseModel):
    insights: Dict[str, Any]
    metrics_summary: Optional[Dict[str, Any]] = None

