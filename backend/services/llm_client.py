import logging
from typing import List, Dict, Optional, Tuple, Type, TypeVar
from openai import OpenAI
from pydantic import BaseModel

from backend.config import settings

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger("exam_system.llm")


class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.openai_api_key or settings.gigachat_credentials
        self.base_url = base_url or settings.openai_base_url
        self.model = model or settings.openai_model
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            kwargs = {"api_key": self.api_key or "placeholder"}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def has_credentials(self) -> bool:
        key = (self.api_key or "").strip()
        return bool(key) and key != "placeholder"

    def check_connection(self) -> Tuple[bool, str]:
        """
        Минимальный запрос к Chat Completions (OpenAI-совместимый API).
        Возвращает (успех, сообщение для логов).
        """
        if not self.has_credentials():
            return False, "не заданы OPENAI_API_KEY или GIGACHAT_CREDENTIALS"
        model_name = self.model
        base = self.base_url or "(OpenAI по умолчанию)"
        try:
            logger.info(
                "LLM: проверка соединения model=%s base_url=%s",
                model_name,
                base,
            )
            r = self.client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": "."}],
                max_tokens=1,
                temperature=0,
            )
            rid = getattr(r, "id", None) or ""
            return True, f"ответ получен (model={model_name}, id={rid[:20]}…)" if rid else f"ответ получен (model={model_name})"
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            logger.exception("LLM: проверка не удалась")
            return False, err

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        model: Optional[str] = None,
    ) -> str:
        model_name = model or self.model
        logger.debug("chat model=%s messages=%s max_tokens=%s", model_name, len(messages), max_tokens)
        response = self.client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content or ""
        logger.debug("chat response len=%s", len(content))
        return content

    def _build_response_format(self, schema_class: Type[BaseModel]) -> Dict:
        schema = schema_class.model_json_schema()
        if "additionalProperties" not in schema:
            schema = {**schema, "additionalProperties": False}
        return {
            "type": "json_schema",
            "json_schema": {
                "name": schema_class.__name__,
                "strict": True,
                "schema": schema,
            },
        }

    def chat_structured(
        self,
        messages: List[Dict[str, str]],
        response_format: Type[T],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        model: Optional[str] = None,
    ) -> T:
        logger.debug("chat_structured format=%s", response_format.__name__)
        fmt = self._build_response_format(response_format)
        response = self.client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=fmt,
        )
        content = response.choices[0].message.content or "{}"
        return response_format.model_validate_json(content)

    def decide_tool(
        self,
        messages: List[Dict[str, str]],
        tools_description: str,
        system_extra: str = "",
        **kwargs,
    ):
        from backend.schemas.structured_outputs import AnswerDecision

        system = f"""Ты помощник. У тебя есть инструменты.

Доступные инструменты:
{tools_description}

Решай:
1. Если можешь дать ответ сам — заполни "answer", оставь "use_tool" пустым.
2. Если нужен инструмент — укажи его название в "use_tool", в "answer" — краткий комментарий пользователю.
{system_extra}"""
        msgs = [{"role": "system", "content": system}] + list(messages)
        return self.chat_structured(msgs, AnswerDecision, **kwargs)

    def tool_params(
        self,
        messages: List[Dict[str, str]],
        tool_name: str,
        params_model: Type[T],
        **kwargs,
    ) -> T:
        return self.chat_structured(messages, params_model, **kwargs)
