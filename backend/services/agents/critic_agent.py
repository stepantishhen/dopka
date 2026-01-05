import json
import re
from typing import Dict, Any
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from backend.services.agents.base_agent import BaseAgent
from backend.models.session import AgentRequest, AgentResponse, AgentType
from backend.config import settings


class CriticAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.CRITIC)
        self.giga = GigaChat(credentials=settings.gigachat_credentials, verify_ssl_certs=False)
    
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
    
    async def _evaluate_answer(self, context: Dict[str, Any]) -> AgentResponse:
        question = context.get("question", {})
        answer = context.get("answer", "")
        reference_answer = context.get("reference_answer", "")
        criteria = context.get("criteria", [])
        
        system_prompt = "Ты эксперт-преподаватель, оценивающий ответы студентов. Оценивай объективно и конструктивно."
        user_prompt = f"""Вопрос: {question}
Эталонный ответ: {reference_answer}
Критерии: {json.dumps(criteria, ensure_ascii=False)}
Ответ студента: {answer}

Оцени ответ. Формат ответа ТОЛЬКО JSON:
{{
    "score": 8.5,
    "max_score": 10,
    "is_correct": false,
    "overall_feedback": "Обратная связь",
    "criteria_scores": []
}}"""
        
        try:
            messages = [
                Messages(role=MessagesRole.SYSTEM, content=system_prompt),
                Messages(role=MessagesRole.USER, content=user_prompt)
            ]
            payload = Chat(messages=messages, temperature=0.3, max_tokens=1000)
            response = self.giga.chat(payload)
            response_text = response.choices[0].message.content
            
            result = self._safe_parse_json(response_text)
            if result:
                return self._create_response(True, {"evaluation": result})
            
            return self._create_response(False, error="Failed to parse evaluation")
        
        except Exception as e:
            return self._create_response(False, error=str(e))
    
    async def _analyze_reasoning(self, context: Dict[str, Any]) -> AgentResponse:
        answer = context.get("answer", "")
        question = context.get("question", "")
        reference = context.get("reference_answer", "")
        
        system_prompt = "Ты эксперт, анализирующий цепочку рассуждений студентов. Выявляй логические ошибки и пропущенные шаги."
        user_prompt = f"""Вопрос: {question}
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
                Messages(role=MessagesRole.SYSTEM, content=system_prompt),
                Messages(role=MessagesRole.USER, content=user_prompt)
            ]
            payload = Chat(messages=messages, temperature=0.3, max_tokens=600)
            response = self.giga.chat(payload)
            response_text = response.choices[0].message.content
            
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
        
        system_prompt = "Ты эксперт, идентифицирующий конкретные ошибки в ответах студентов."
        user_prompt = f"""Вопрос: {question}
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
                Messages(role=MessagesRole.SYSTEM, content=system_prompt),
                Messages(role=MessagesRole.USER, content=user_prompt)
            ]
            payload = Chat(messages=messages, temperature=0.3, max_tokens=500)
            response = self.giga.chat(payload)
            response_text = response.choices[0].message.content
            
            result = self._safe_parse_json(response_text)
            if result:
                return self._create_response(True, {"error_analysis": result})
            
            return self._create_response(False, error="Failed to parse error identification")
        
        except Exception as e:
            return self._create_response(False, error=str(e))

