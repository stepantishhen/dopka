import json
import re
import logging
from typing import Dict, Any, List, Optional

from backend.services.agents.base_agent import BaseAgent
from backend.models.session import AgentRequest, AgentResponse, AgentType
from backend.services.llm_client import LLMClient

logger = logging.getLogger("exam_system.adaptive_exam_agent")

MAX_SIMPLIFICATION_LEVEL = 3


class AdaptiveExamAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.ADAPTIVE_EXAM)
        self.llm = LLMClient()

    def _safe_parse_json(self, text: str) -> Dict[str, Any]:
        if not text:
            return {}
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if not json_match:
            return {}
        raw = json_match.group()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        for pattern in (r'```json\s*(\{.*?\})\s*```', r'```\s*(\{.*?\})\s*```'):
            m = re.search(pattern, text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1))
                except json.JSONDecodeError:
                    pass
        return {}

    async def process(self, request: AgentRequest) -> AgentResponse:
        action = request.action
        context = request.context
        session_state = request.session_state

        if action == "recommend_response_strategy":
            return await self._recommend_response_strategy(context, session_state)
        if action == "recommend_next_difficulty":
            return await self._recommend_next_difficulty(context, session_state)

        return self._create_response(False, error=f"Unknown action: {action}")

    async def _recommend_response_strategy(
        self,
        context: Dict[str, Any],
        session_state: Optional[Any],
    ) -> AgentResponse:
        current_level = context.get("current_simplification_level", 0)
        question = context.get("question", "")
        answer = context.get("answer", "")
        dialogue_context = context.get("dialogue_context", "")

        if current_level >= MAX_SIMPLIFICATION_LEVEL:
            next_level = MAX_SIMPLIFICATION_LEVEL
            tactic = "ask_experience"
        else:
            next_level = current_level
            tactic = {0: "rephrase", 1: "example", 2: "simplify", 3: "ask_experience"}.get(
                current_level, "rephrase"
            )

        system_prompt = """Ты контроллер адаптивного экзамена (CAT). Управляешь подходами к студенту при слабом ответе.
Лестница упрощений: 0 — переформулировать вопрос; 1 — упростить или пример из жизни; 2 — упростить до предела или спросить про опыт; 3 — спросить про занятость/опыт студента.
Ответь ТОЛЬКО JSON без markdown:
{"simplification_level": 0-3, "rephrase_tactic": "rephrase|simplify|example|ask_experience", "reasoning": "одна фраза"}"""

        user_prompt = f"""Текущий уровень упрощения: {current_level}. Вопрос: {question}. Ответ студента: "{answer or '(пусто)'}".
Контекст диалога (кратко): {dialogue_context[:500] if dialogue_context else 'нет'}.
Рекомендуй simplification_level (0–3) и rephrase_tactic для следующего сообщения студенту."""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            response_text = self.llm.chat(messages, temperature=0.3, max_tokens=200)
            result = self._safe_parse_json(response_text)
            if result:
                level = result.get("simplification_level", current_level)
                level = max(0, min(MAX_SIMPLIFICATION_LEVEL, int(level) if isinstance(level, (int, float)) else current_level))
                tactic = result.get("rephrase_tactic") or tactic
                if tactic not in ("rephrase", "simplify", "example", "ask_experience"):
                    tactic = "rephrase"
                return self._create_response(
                    True,
                    {
                        "simplification_level": level,
                        "rephrase_tactic": tactic,
                        "reasoning": result.get("reasoning", ""),
                    },
                )
        except Exception as e:
            logger.exception("recommend_response_strategy error: %s", e)

        return self._create_response(
            True,
            {
                "simplification_level": next_level,
                "rephrase_tactic": tactic,
                "reasoning": "rule-based fallback",
            },
        )

    async def _recommend_next_difficulty(
        self,
        context: Dict[str, Any],
        session_state: Optional[Any],
    ) -> AgentResponse:
        recent_evaluations = context.get("recent_evaluations", [])
        exam_config = context.get("exam_config", {})
        answered_count = context.get("answered_questions_count", 0)

        if not recent_evaluations:
            default = 0.5
            return self._create_response(
                True,
                {
                    "next_difficulty": default,
                    "ability_estimate": default,
                    "reasoning": "нет ответов, средняя сложность",
                },
            )

        scores = []
        for ev in recent_evaluations:
            s, m = ev.get("score", 0), ev.get("max_score", 100)
            if m and m > 0:
                scores.append(float(s) / float(m))
        ability = sum(scores) / len(scores) if scores else 0.5

        if ability >= 0.7:
            next_difficulty = min(1.0, ability + 0.1)
            reasoning = "хороший результат — повышаем сложность"
        elif ability < 0.56:
            next_difficulty = max(0.2, ability - 0.1)
            reasoning = "низкий балл — снижаем сложность"
        else:
            next_difficulty = ability
            reasoning = "удерживаем сложность около текущего уровня"

        next_difficulty = max(0.1, min(1.0, next_difficulty))

        return self._create_response(
            True,
            {
                "next_difficulty": round(next_difficulty, 2),
                "ability_estimate": round(ability, 2),
                "reasoning": reasoning,
            },
        )
