from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class DidacticUnit(BaseModel):
    unit_id: str
    title: str
    content_type: str = "concept"
    definition: str = ""
    examples: List[str] = []
    common_errors: List[str] = []
    prerequisites: List[str] = []
    related_units: List[str] = []
    assessment_criteria: Dict = {}
    questions: Dict = Field(default_factory=lambda: {
        "understanding": [],
        "application": [],
        "analysis": []
    })
    difficulty_level: float = 0.5
    metadata: Dict = Field(default_factory=lambda: {
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "source_materials": [],
        "mastery_stats": {
            "total_attempts": 0,
            "correct_attempts": 0,
            "avg_response_time": 0,
            "common_misconceptions": []
        }
    })
    
    class Config:
        json_schema_extra = {
            "example": {
                "unit_id": "python_var_01",
                "title": "Переменные в Python",
                "content_type": "concept",
                "definition": "Переменная в Python - это именованная область памяти...",
                "examples": ["x = 10", "name = 'Анна'"],
                "common_errors": ["Использование необъявленной переменной"]
            }
        }

