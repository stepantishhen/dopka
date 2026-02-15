from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class SessionStatus(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AgentType(str, Enum):
    KNOWLEDGE = "knowledge"
    DIALOGUE = "dialogue"
    CRITIC = "critic"
    PLANNING = "planning"
    ANALYTICS = "analytics"
    ADAPTIVE_EXAM = "adaptive_exam"


class DialogueTactic(str, Enum):
    CLARIFICATION = "clarification"
    HINT = "hint"
    ANALOGY = "analogy"
    COUNTEREXAMPLE = "counterexample"
    ENCOURAGEMENT = "encouragement"


class SessionState(BaseModel):
    session_id: str
    student_id: str
    exam_id: Optional[str] = None
    current_question_id: Optional[str] = None
    status: SessionStatus = SessionStatus.CREATED
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    dialogue_history: List[Dict[str, Any]] = Field(default_factory=list)
    answered_questions: List[str] = Field(default_factory=list)
    question_order: Optional[List[str]] = None
    knowledge_gaps: List[str] = Field(default_factory=list)
    current_tactic: Optional[DialogueTactic] = None
    current_simplification_level: int = 0


class AgentRequest(BaseModel):
    agent_type: AgentType
    action: str
    context: Dict[str, Any] = Field(default_factory=dict)
    session_state: Optional[SessionState] = None


class AgentResponse(BaseModel):
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowStep(BaseModel):
    step_id: str
    agent_type: AgentType
    action: str
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    status: str = "pending"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class Workflow(BaseModel):
    workflow_id: str
    session_id: str
    steps: List[WorkflowStep] = Field(default_factory=list)
    status: str = "active"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
