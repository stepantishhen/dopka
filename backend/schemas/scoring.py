"""Structured output для сравнения ответа студента с эталоном (отдельная scoring-модель)."""

from typing import List
from pydantic import BaseModel, ConfigDict, Field


class CriterionScoreItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Название критерия из списка")
    score: float = Field(ge=0, description="Набранные баллы по критерию")
    max_score: float = Field(ge=0, description="Максимум по критерию")
    comment: str = Field(default="", description="Краткий комментарий по критерию")


class AnswerScoringResult(BaseModel):
    """Результат сравнения эталона и ответа студента."""

    model_config = ConfigDict(extra="forbid")

    score: float = Field(description="Итоговый балл за вопрос, от 0 до max_score включительно")
    max_score: float = Field(description="Максимум баллов за этот вопрос (как передано в задании)")
    is_correct: bool = Field(
        description="True, если ответ по сути верный и соответствует эталону достаточно для зачёта"
    )
    overall_feedback: str = Field(description="Краткая обратная связь студенту по-русски")
    criteria_scores: List[CriterionScoreItem] = Field(
        default_factory=list,
        description="Разбивка по критериям; если критерии не заданы, можно оставить пустым",
    )
