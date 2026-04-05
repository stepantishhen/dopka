from typing import List, Literal, Optional, Type, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T", bound=BaseModel)


class AnswerDecision(BaseModel):
    reasoning: str = Field(description="Логическое рассуждение агента")
    answer: str = Field(description="Ответ пользователю или промежуточный комментарий")
    use_tool: Optional[str] = Field(None, description="Название инструмента для вызова (если нужен)")


class CriterionItem(BaseModel):
    """Критерий оценки ответа на вопрос (structured output для генерации вопросов)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Название критерия оценки")
    max_score: float = Field(default=2, ge=0, description="Максимальный балл по критерию")


class QuestionGenerated(BaseModel):
    """Один сгенерированный вопрос — схема для LLM structured output."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(description="Текст вопроса")
    type: Literal["understanding", "application", "analysis"] = Field(
        default="understanding",
        description="Тип вопроса: understanding | application | analysis",
    )
    difficulty: float = Field(default=0.5, ge=0, le=1, description="Сложность от 0 до 1")
    criteria: List[CriterionItem] = Field(default_factory=list, description="Критерии оценивания")
    reference_answer: str = Field(default="", description="Эталонный ответ")


class GenerateQuestionsStructured(BaseModel):
    """Ответ LLM при генерации вопросов по дидактической единице."""

    model_config = ConfigDict(extra="forbid")

    questions: List[QuestionGenerated] = Field(description="Список вопросов")


class DidacticUnitLLM(BaseModel):
    """Одна извлечённая дидактическая единица — схема для LLM structured output."""

    model_config = ConfigDict(extra="forbid")

    unit_id: str = Field(description="Уникальный идентификатор единицы, например unit_1")
    title: str = Field(description="Название концепции")
    content_type: str = Field(default="concept", description="Тип содержимого, например concept")
    definition: str = Field(default="", description="Определение")
    examples: List[str] = Field(default_factory=list, description="Примеры")
    common_errors: List[str] = Field(default_factory=list, description="Типичные ошибки")


class ExtractKnowledgeStructured(BaseModel):
    """Ответ LLM при извлечении дидактических единиц из текста."""

    model_config = ConfigDict(extra="forbid")

    units: List[DidacticUnitLLM] = Field(description="Извлечённые дидактические единицы")
