from typing import List, Optional
from pydantic import BaseModel
from backend.models.didactic_unit import DidacticUnit


class KnowledgeItemCreate(BaseModel):
    title: str
    content: str
    category: Optional[str] = None
    tags: List[str] = []


class KnowledgeItemResponse(BaseModel):
    id: str
    title: str
    content: str
    category: Optional[str] = None
    tags: List[str] = []
    createdAt: str
    updatedAt: str
    
    class Config:
        from_attributes = True


class KnowledgeItemUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class DidacticUnitCreate(BaseModel):
    title: str
    content_type: str = "concept"
    definition: str = ""
    examples: List[str] = []
    common_errors: List[str] = []


class DidacticUnitResponse(BaseModel):
    unit_id: str
    title: str
    content_type: str
    definition: str
    examples: List[str]
    common_errors: List[str]
    prerequisites: List[str]
    related_units: List[str]
    difficulty_level: float
    metadata: dict
    
    class Config:
        from_attributes = True

