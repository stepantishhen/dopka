from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ExamConfig(BaseModel):
    name: str
    adaptive: bool = False
    num_questions: int = 10
    target_difficulty: float = 0.5
    unit_ids: Optional[List[str]] = None


class Exam(BaseModel):
    exam_id: str
    config: ExamConfig
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    status: str = "draft"
    students: List[str] = []
    questions: List[Dict] = []
    results: Dict = Field(default_factory=dict)
    link: str = ""


class StudentAnswer(BaseModel):
    question_id: str
    answer: str
    timestamp: Optional[str] = None


class EvaluationRequest(BaseModel):
    student_id: str
    student_answers: List[StudentAnswer]


class EmotionalState(BaseModel):
    emotional_state: str
    confidence_score: float
    anxiety_score: float
    key_indicators: List[str] = []
    recommendations: List[str] = []
    communication_style: str = "neutral"


class StudentProfile(BaseModel):
    student_id: str
    name: Optional[str] = None
    group: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    knowledge_map: Dict = Field(default_factory=dict)
    emotional_state: Optional[EmotionalState] = None
    learning_history: List[Dict] = Field(default_factory=list)
    last_evaluation: Optional[Dict] = None

