from typing import Optional, Type, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class AnswerDecision(BaseModel):
    reasoning: str = Field(description="Логическое рассуждение агента")
    answer: str = Field(description="Ответ пользователю или промежуточный комментарий")
    use_tool: Optional[str] = Field(None, description="Название инструмента для вызова (если нужен)")
