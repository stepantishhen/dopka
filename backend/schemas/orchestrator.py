from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator


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
    total_score: Optional[float] = None
    max_total_score: Optional[float] = None
    questions_answered: Optional[int] = None
    passed: Optional[bool] = None
    exam_flow_phase: Optional[str] = None
    pretest_completed: Optional[bool] = None


class PretestSubmission(BaseModel):
    choices: Dict[str, int] = Field(default_factory=dict)


class PretestCompleteResponse(BaseModel):
    pretest_completed: bool
    per_question: Dict[str, bool] = Field(default_factory=dict)
    strong_topics: List[Dict[str, Any]] = Field(default_factory=list)
    weak_topics: List[Dict[str, Any]] = Field(default_factory=list)
    weak_question_ids: List[str] = Field(default_factory=list)


class SessionCompleteResponse(BaseModel):
    session_id: str
    status: str
    total_score: float
    max_total_score: float
    questions_answered: int
    passed: bool


class AnswerSubmission(BaseModel):
    session_id: str
    question_id: str
    answer: str = ""
    question_data: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("question_id", mode="before")
    @classmethod
    def question_id_str(cls, v):
        return str(v) if v is not None else ""

    @field_validator("question_data", mode="before")
    @classmethod
    def question_data_dict(cls, v):
        return v if isinstance(v, dict) else {}


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

