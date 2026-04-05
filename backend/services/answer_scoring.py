"""
Отдельная scoring-модель (OPENAI_SCORING_MODEL): сравнение эталонного ответа с ответом студента.
При сбое structured output — fallback на свободный JSON тем же клиентом/моделью.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.schemas.scoring import AnswerScoringResult
from backend.services.llm_client import LLMClient

logger = logging.getLogger("exam_system.answer_scoring")


class AnswerScoringService:
    """Оценка ответа по эталону; использует отдельное имя модели из настроек."""

    def __init__(self) -> None:
        model = (settings.openai_scoring_model or "").strip() or settings.openai_model
        self._model_name = model
        self._llm = LLMClient(model=model)
        logger.info("AnswerScoringService: модель оценки ответов (эталон vs студент): %s", self._model_name)

    @property
    def model_name(self) -> str:
        return self._model_name

    def compare_and_score(
        self,
        *,
        question: str,
        reference_answer: str,
        student_answer: str,
        criteria: List[Dict[str, Any]],
        max_for_question: float,
        dialogue_context: str = "",
        question_info: str = "",
    ) -> Dict[str, Any]:
        """
        Возвращает словарь evaluation в формате, ожидаемом оркестратором:
        score, max_score, is_correct, overall_feedback, criteria_scores (list of dicts).
        """
        answer_str = (student_answer or "").strip()
        if not answer_str or len(answer_str) < 3:
            return {
                "score": 0.0,
                "max_score": max_for_question,
                "is_correct": False,
                "overall_feedback": "Ответ отсутствует или слишком краткий. Попробуйте ответить развёрнуто.",
                "criteria_scores": [],
            }

        crit_json = json.dumps(criteria, ensure_ascii=False) if criteria else "[]"
        dialogue_block = f"Контекст диалога (фрагмент):\n{dialogue_context}\n\n" if dialogue_context.strip() else ""

        system_prompt = """Ты модель оценивания ответов на экзамене. Твоя задача — сравнить ответ студента с эталонным и критериями.
Правила:
- Выставь score строго от 0 до переданного максимума за вопрос (не выходи за границы).
- max_score в ответе должен совпадать с переданным максимумом за этот вопрос.
- is_correct = true только если ответ по смыслу верен относительно эталона и вопроса (допускаются перефразирование и другие формулировки).
- Частичное понимание: низкий score, is_correct = false, объясни в overall_feedback.
- criteria_scores заполни, если критерии переданы; иначе оставь пустым список.
Ответ строго в формате JSON-схемы (structured output)."""

        user_prompt = f"""{question_info}{dialogue_block}Вопрос:
{question}

Эталонный ответ:
{reference_answer}

Критерии оценивания (JSON):
{crit_json}

Ответ студента:
{answer_str}

Максимум баллов за этот вопрос (не превышай score): {max_for_question:.1f}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            parsed = self._llm.chat_structured(
                messages,
                AnswerScoringResult,
                temperature=0.2,
                max_tokens=2000,
                model=self._model_name,
            )
            ev = self._result_to_evaluation(parsed, max_for_question)
            logger.info(
                "answer_scoring structured OK model=%s score=%s max=%s is_correct=%s",
                self._model_name,
                ev.get("score"),
                ev.get("max_score"),
                ev.get("is_correct"),
            )
            return ev
        except Exception as e:
            logger.warning("answer_scoring structured failed (%s), fallback JSON chat", e)
            return self._fallback_json_chat(
                messages,
                max_for_question,
            )

    def _result_to_evaluation(self, parsed: AnswerScoringResult, max_for_question: float) -> Dict[str, Any]:
        raw = float(parsed.score or 0)
        score = max(0.0, min(max_for_question, raw))
        max_score = max_for_question
        is_correct = bool(parsed.is_correct)
        if score < (max_for_question * 0.56):
            is_correct = False
        criteria_scores = [cs.model_dump() for cs in parsed.criteria_scores]
        return {
            "score": score,
            "max_score": max_score,
            "is_correct": is_correct,
            "overall_feedback": parsed.overall_feedback or "",
            "criteria_scores": criteria_scores,
        }

    def _fallback_json_chat(
        self,
        messages: List[Dict[str, str]],
        max_for_question: float,
    ) -> Dict[str, Any]:
        try:
            text = self._llm.chat(messages, temperature=0.2, max_tokens=1500, model=self._model_name)
            data = self._safe_parse_json(text)
            if not data:
                raise ValueError("empty parse")
            score = max(0.0, min(max_for_question, float(data.get("score", 0) or 0)))
            is_correct = data.get("is_correct")
            if is_correct is None:
                is_correct = score >= (max_for_question * 0.56)
            return {
                "score": score,
                "max_score": max_for_question,
                "is_correct": bool(is_correct),
                "overall_feedback": str(data.get("overall_feedback", "")),
                "criteria_scores": data.get("criteria_scores") if isinstance(data.get("criteria_scores"), list) else [],
            }
        except Exception as e:
            logger.exception("answer_scoring fallback failed: %s", e)
            return {
                "score": 0.0,
                "max_score": max_for_question,
                "is_correct": False,
                "overall_feedback": "Не удалось автоматически оценить ответ. Попробуйте ещё раз.",
                "criteria_scores": [],
            }

    @staticmethod
    def _safe_parse_json(text: str) -> Optional[Dict[str, Any]]:
        import re

        if not text:
            return None
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except Exception:
            return None


_service: Optional[AnswerScoringService] = None


def get_answer_scoring_service() -> AnswerScoringService:
    global _service
    if _service is None:
        _service = AnswerScoringService()
    return _service
