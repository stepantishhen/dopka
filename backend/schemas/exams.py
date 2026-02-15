from typing import List, Optional, Dict
from pydantic import BaseModel
from backend.models.exam_system import ExamConfig, StudentAnswer


class ExamCreate(BaseModel):
    name: str
    adaptive: bool = False
    num_questions: int = 10
    target_difficulty: float = 0.5
    unit_ids: Optional[List[str]] = None


class ExamResponse(BaseModel):
    exam_id: str
    config: ExamConfig
    created_at: str
    status: str
    questions: List[Dict]
    link: str
    
    class Config:
        from_attributes = True


class QuestionResponse(BaseModel):
    question_id: str
    question: str
    type: str
    difficulty: float
    criteria: List[Dict]
    reference_answer: Optional[str] = None


class ExamSubmission(BaseModel):
    student_id: str
    answers: List[StudentAnswer]


class EvaluationResponse(BaseModel):
    student_id: str
    evaluation_date: str
    total_score: float
    max_score: float
    percentage: float
    evaluations: List[Dict]
    knowledge_gaps: List[Dict]
    recommendations: List[Dict]
    strengths: List[str]


class CreateExamFromMaterialsRequest(BaseModel):
    name: str
    text: Optional[str] = None
    unit_ids: Optional[List[str]] = None
    num_questions: int = 10
    adaptive: bool = True
    questions_per_unit: int = 3
