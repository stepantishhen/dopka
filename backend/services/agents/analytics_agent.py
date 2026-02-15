import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from backend.services.agents.base_agent import BaseAgent
from backend.models.session import AgentRequest, AgentResponse, AgentType
from backend.services.llm_client import LLMClient


class AnalyticsAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.ANALYTICS)
        self.llm = LLMClient()
        self.metrics_store: Dict[str, List[Dict[str, Any]]] = {}
    
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
            print(f"JSON parsing error in AnalyticsAgent: {e}")
            return {}
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        action = request.action
        context = request.context
        
        if action == "record_metric":
            return await self._record_metric(context)
        elif action == "generate_insights":
            return await self._generate_insights(context)
        elif action == "analyze_group_performance":
            return await self._analyze_group_performance(context)
        
        return self._create_response(False, error=f"Unknown action: {action}")
    
    async def _record_metric(self, context: Dict[str, Any]) -> AgentResponse:
        session_id = context.get("session_id")
        if not session_id:
            return self._create_response(False, error="session_id required")
        
        if session_id not in self.metrics_store:
            self.metrics_store[session_id] = []
        
        metric = {
            "timestamp": datetime.now().isoformat(),
            "question_id": context.get("question_id"),
            "answer": context.get("answer"),
            "evaluation": context.get("evaluation", {}),
            "response_time": context.get("response_time"),
            "tactic_used": context.get("tactic_used"),
            "emotional_state": context.get("emotional_state")
        }
        
        self.metrics_store[session_id].append(metric)
        
        return self._create_response(True, {"metric": metric})
    
    async def _generate_insights(self, context: Dict[str, Any]) -> AgentResponse:
        session_id = context.get("session_id")
        student_id = context.get("student_id")
        report_type = context.get("report_type", "student")
        
        metrics = self.metrics_store.get(session_id, [])
        
        if not metrics:
            return self._create_response(False, error="No metrics available")

        total_questions = len(metrics)
        scores = []
        response_times = []
        tactics_used = {}
        
        for metric in metrics:
            eval_data = metric.get("evaluation", {})
            score = eval_data.get("score", 0)
            max_s = eval_data.get("max_score", 10)
            if max_s > 0:
                scores.append(score / max_s)
            
            rt = metric.get("response_time")
            if rt:
                response_times.append(rt)
            
            tactic = metric.get("tactic_used")
            if tactic:
                tactics_used[tactic] = tactics_used.get(tactic, 0) + 1
        
        avg_score = sum(scores) / len(scores) if scores else 0
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        metrics_summary = {
            "total_questions": total_questions,
            "avg_score": avg_score,
            "avg_response_time": avg_response_time,
            "tactics_distribution": tactics_used
        }
        
        system_prompt = "Ты аналитик образовательных данных, генерирующий инсайты из метрик студентов."
        user_prompt = f"""Метрики студента {student_id}:
{json.dumps(metrics_summary, ensure_ascii=False, indent=2)}

Сгенерируй инсайты. Формат ответа ТОЛЬКО JSON:
{{
    "strengths": ["Сильная сторона 1", "Сильная сторона 2"],
    "weaknesses": ["Слабая сторона 1"],
    "key_insights": [
        "Группа слабо усвоила тему X из-за типовой ошибки Y",
        "Студент показывает прогресс в области Z"
    ],
    "recommendations": [
        "Рекомендация для преподавателя 1",
        "Рекомендация для студента 1"
    ],
    "trends": "Описание трендов производительности"
}}"""
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response_text = self.llm.chat(messages, temperature=0.5, max_tokens=800)
            
            result = self._safe_parse_json(response_text)
            if result:
                return self._create_response(True, {"insights": result})
            
            return self._create_response(False, error="Failed to parse insights")
        
        except Exception as e:
            return self._create_response(False, error=str(e))
    
    async def _analyze_group_performance(self, context: Dict[str, Any]) -> AgentResponse:
        import json
        group_summary = context.get("group_summary", {})
        
        system_prompt = "Ты аналитик образовательных данных, генерирующий групповые инсайты."
        user_prompt = f"""Групповая статистика:
{json.dumps(group_summary, ensure_ascii=False, indent=2)}

Сгенерируй групповые инсайты. Формат ответа ТОЛЬКО JSON:
{{
    "group_strengths": ["Сильная сторона группы"],
    "group_weaknesses": ["Слабая сторона группы"],
    "key_insights": [
        "Группа слабо усвоила тему X из-за типовой ошибки Y",
        "Большинство студентов испытывают трудности с Z"
    ],
    "recommendations": [
        "Рекомендация для преподавателя 1",
        "Рекомендация для преподавателя 2"
    ]
}}"""
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response_text = self.llm.chat(messages, temperature=0.5, max_tokens=800)
            
            result = self._safe_parse_json(response_text)
            if result:
                return self._create_response(True, {"group_insights": result})
            
            return self._create_response(False, error="Failed to parse group insights")
        
        except Exception as e:
            return self._create_response(False, error=str(e))
