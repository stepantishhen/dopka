import json
import re
from typing import Dict, Any
from backend.services.agents.base_agent import BaseAgent
from backend.models.session import AgentRequest, AgentResponse, AgentType
from backend.services.llm_client import LLMClient
from backend.services.answer_scoring import get_answer_scoring_service


class CriticAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.CRITIC)
        self.llm = LLMClient()
        self._scoring = get_answer_scoring_service()
    
    def _safe_parse_json(self, text: str) -> Dict[str, Any]:
        if not text:
            return {}
        
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if not json_match:
            patterns = [
                r'```json\s*(.*?)\s*```',
                r'```\s*(.*?)\s*```',
                r'JSON:\s*(\{.*\})',
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if match:
                    json_match = match
                    break
        
        if not json_match:
            return {}
        
        json_text = json_match.group(1) if json_match and len(json_match.groups()) > 0 else (json_match.group() if json_match else text)
        
        try:
            json_text = json_text.replace('\ufeff', '').replace('\u200b', '')
            json_text = json_text.replace('"', '"').replace('"', '"')
            json_text = re.sub(r',\s*}', '}', json_text)
            json_text = re.sub(r',\s*]', ']', json_text)
            json_text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_text)
            json_text = json_text.strip()
            if json_text.startswith('{') and not json_text.endswith('}'):
                json_text = json_text.rsplit('}', 1)[0] + '}'
            if json_text.startswith('[') and not json_text.endswith(']'):
                json_text = json_text.rsplit(']', 1)[0] + ']'
            return json.loads(json_text)
        except Exception as e:
            print(f"JSON parsing error in CriticAgent: {e}")
            return {}
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        action = request.action
        context = request.context
        
        if action == "evaluate_answer":
            return await self._evaluate_answer(context)
        elif action == "analyze_reasoning":
            return await self._analyze_reasoning(context)
        elif action == "identify_error":
            return await self._identify_error(context)
        
        return self._create_response(False, error=f"Unknown action: {action}")
    
    def _format_dialogue_context(self, context: Dict[str, Any]) -> str:
        raw = context.get("dialogue_context", "").strip()
        if not raw:
            return ""
        return f"Контекст диалога (последние реплики):\n{raw}\n\n"

    async def _evaluate_answer(self, context: Dict[str, Any]) -> AgentResponse:
        question = context.get("question", "")
        if isinstance(question, dict):
            question = question.get("question", "") or str(question)
        answer = context.get("answer", "")
        reference_answer = context.get("reference_answer", "")
        criteria = context.get("criteria", [])
        dialogue_block = self._format_dialogue_context(context)

        max_for_question = float(context.get("max_score_for_this_question") or 100.0)
        answer_str = (answer or "").strip()
        if not answer_str or len(answer_str) < 3:
            return self._create_response(True, {"evaluation": {
                "score": 0,
                "max_score": max_for_question,
                "is_correct": False,
                "overall_feedback": "Ответ отсутствует или слишком краткий. Попробуйте ответить развёрнуто.",
                "criteria_scores": []
            }})

        num_questions = context.get("num_questions")
        question_number = context.get("question_number")
        already_earned = float(context.get("already_earned") or 0)
        question_info = ""
        if num_questions is not None and question_number is not None:
            question_info = (
                f"Это вопрос {question_number} из {num_questions}. Весь экзамен — 100 баллов суммарно. "
                f"Уже набрано за предыдущие вопросы: {already_earned:.0f}. "
                f"За этот вопрос можно выставить не более {max_for_question:.1f} баллов. "
                f"Минимум для сдачи экзамена — 56 баллов. Не выходи за 0 и за максимум для этого вопроса.\n\n"
            )

        try:
            result = self._scoring.compare_and_score(
                question=str(question),
                reference_answer=str(reference_answer or ""),
                student_answer=str(answer or ""),
                criteria=criteria if isinstance(criteria, list) else [],
                max_for_question=max_for_question,
                dialogue_context=dialogue_block,
                question_info=question_info,
            )
            if result:
                score_val = result.get("score", 0)
                result["max_score"] = max_for_question
                result["score"] = max(0.0, min(max_for_question, float(score_val) if score_val is not None else 0))
                if "is_correct" not in result or result.get("is_correct") is None:
                    result["is_correct"] = result["score"] >= (max_for_question * 0.56)
                if result["score"] < (max_for_question * 0.56):
                    result["is_correct"] = False
                return self._create_response(True, {"evaluation": result})

            return self._create_response(False, error="Failed to parse evaluation")

        except Exception as e:
            return self._create_response(False, error=str(e))
    
    async def _analyze_reasoning(self, context: Dict[str, Any]) -> AgentResponse:
        answer = context.get("answer", "")
        question = context.get("question", "")
        reference = context.get("reference_answer", "")
        dialogue_block = self._format_dialogue_context(context)

        system_prompt = "Ты эксперт, анализирующий цепочку рассуждений студентов. Учитывай контекст диалога. Выявляй логические ошибки и пропущенные шаги."
        user_prompt = f"""{dialogue_block}Вопрос: {question}
Ответ студента: {answer}

Проанализируй цепочку рассуждений. Формат ответа ТОЛЬКО JSON:
{{
    "reasoning_steps": ["Шаг 1", "Шаг 2"],
    "logical_errors": ["Ошибка в логике 1"],
    "missing_steps": ["Пропущенный шаг"],
    "correct_parts": ["Правильная часть"],
    "diagnosis": "Краткий диагноз проблемы"
}}"""
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response_text = self.llm.chat(messages, temperature=0.3, max_tokens=600)
            
            result = self._safe_parse_json(response_text)
            if result:
                return self._create_response(True, {"reasoning_analysis": result})
            
            return self._create_response(False, error="Failed to parse reasoning analysis")
        
        except Exception as e:
            return self._create_response(False, error=str(e))
    
    async def _identify_error(self, context: Dict[str, Any]) -> AgentResponse:
        question = context.get("question", "")
        answer = context.get("answer", "")
        reference_answer = context.get("reference_answer", "")
        reasoning_analysis = context.get("reasoning_analysis", {})
        dialogue_block = self._format_dialogue_context(context)

        system_prompt = "Ты эксперт, идентифицирующий конкретные ошибки в ответах студентов. Учитывай контекст диалога."
        user_prompt = f"""{dialogue_block}Вопрос: {question}
Эталонный ответ: {reference_answer}
Ответ студента: {answer}
Анализ рассуждений: {json.dumps(reasoning_analysis, ensure_ascii=False)}

Идентифицируй конкретную ошибку. Формат ответа ТОЛЬКО JSON:
{{
    "error_type": "conceptual|computational|logical",
    "error_description": "Описание ошибки",
    "correct_approach": "Правильный подход",
    "suggestions": ["Предложение 1", "Предложение 2"]
}}"""
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response_text = self.llm.chat(messages, temperature=0.3, max_tokens=500)
            
            result = self._safe_parse_json(response_text)
            if result:
                return self._create_response(True, {"error_analysis": result})
            
            return self._create_response(False, error="Failed to parse error identification")
        
        except Exception as e:
            return self._create_response(False, error=str(e))

