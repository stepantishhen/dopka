from typing import List, Optional, Dict, Any
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
    join_code: Optional[str] = None
    # Пути для фронтенда (добавить origin): ссылка для студентов и прямой вход в экзамен
    join_path: Optional[str] = None
    exam_path: Optional[str] = None

    class Config:
        from_attributes = True


def exam_to_response(exam: Any) -> ExamResponse:
    """Собирает ExamResponse с маршрутами для копирования ссылок."""
    d = exam.model_dump() if hasattr(exam, "model_dump") else exam.dict()
    jc = (d.get("join_code") or "").strip()
    eid = d.get("exam_id") or ""
    d["join_path"] = f"/join/{jc}" if jc else None
    d["exam_path"] = f"/exam/{eid}" if eid else None
    return ExamResponse(**d)


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
    evaluations: List[Dict[str, Any]]
    knowledge_gaps: List[str]
    recommendations: List[str]
    strengths: List[str]


class CreateExamFromMaterialsRequest(BaseModel):
    name: str
    text: Optional[str] = None
    unit_ids: Optional[List[str]] = None
    num_questions: int = 10
    adaptive: bool = True
    questions_per_unit: int = 3
