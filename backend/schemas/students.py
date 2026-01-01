from typing import List, Optional, Dict
from pydantic import BaseModel


class StudentCreate(BaseModel):
    name: str
    group: Optional[str] = None


class StudentResponse(BaseModel):
    student_id: str
    name: Optional[str]
    group: Optional[str]
    created_at: str
    emotional_state: Optional[Dict] = None


class StudentProfileResponse(BaseModel):
    student_id: str
    name: Optional[str]
    group: Optional[str]
    created_at: str
    knowledge_map: Dict
    emotional_state: Optional[Dict]
    learning_history: List[Dict]
    last_evaluation: Optional[Dict]


class EmotionalStateRequest(BaseModel):
    student_id: str
    responses: List[str]


class DiagnosticRequest(BaseModel):
    student_id: str
    quick_mode: bool = True


class DiagnosticResponse(BaseModel):
    diagnostic_id: str
    questions: List[Dict]
    estimated_time: int

