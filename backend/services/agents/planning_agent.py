from typing import Dict, Any, List, Optional
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from backend.services.agents.base_agent import BaseAgent
from backend.models.session import AgentRequest, AgentResponse, AgentType
from backend.config import settings
import json
import random
import re
import uuid


class PlanningAgent(BaseAgent):
    def __init__(self, knowledge_service):
        super().__init__(AgentType.PLANNING)
        self.knowledge_service = knowledge_service
    
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
            print(f"JSON parsing error in PlanningAgent: {e}")
            return {}
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        action = request.action
        context = request.context
        
        if action == "select_next_question":
            return await self._select_next_question(context)
        elif action == "plan_sequence":
            return await self._plan_sequence(context, request.session_state)
        elif action == "plan_exam":
            return await self._plan_exam(context)

        return self._create_response(False, error=f"Unknown action: {action}")
    
    async def _select_next_question(self, context: Dict[str, Any]) -> AgentResponse:
        exam_config = context.get("exam_config", {})
        answered_questions = context.get("answered_questions", [])
        student_performance = context.get("student_performance", {})
        knowledge_gaps = student_performance.get("knowledge_gaps", [])
        

        unit_ids = exam_config.get("unit_ids") or list(self.knowledge_service.knowledge_base.keys())
        

        avg_score = student_performance.get("avg_score", 0.5)
        current_difficulty = student_performance.get("current_difficulty", 0.5)
        

        if avg_score > 0.8:
            target_difficulty = min(1.0, current_difficulty + 0.1)
        elif avg_score < 0.5:
            target_difficulty = max(0.2, current_difficulty - 0.1)
        else:
            target_difficulty = current_difficulty
        

        available_questions = []
        for unit_id in unit_ids:
            unit = self.knowledge_service.get_unit(unit_id)
            if not unit:
                continue
            

            priority = 1.0
            if unit_id in knowledge_gaps:
                priority = 2.0
            
            for q_type in ["understanding", "application", "analysis"]:
                if unit.questions.get(q_type):
                    for q in unit.questions[q_type]:
                        q_id = q.get("question_id")
                        if q_id and q_id not in answered_questions:
                            q_difficulty = q.get("difficulty", 0.5)

                            diff_score = 1.0 - abs(q_difficulty - target_difficulty)
                            score = priority * diff_score
                            
                            available_questions.append({
                                **q,
                                "unit_id": unit_id,
                                "priority_score": score
                            })
        

        available_questions.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        
        if available_questions:
            top_n = 5
            candidates = available_questions[:top_n]
            selected = random.choice(candidates)
            if not selected.get("question_id"):
                selected["question_id"] = f"q_{uuid.uuid4().hex[:8]}"
            return self._create_response(
                True,
                {
                    "question": selected,
                    "target_difficulty": target_difficulty,
                    "reasoning": f"Selected based on performance (avg_score={avg_score:.2f})"
                }
            )
        
        return self._create_response(False, error="No available questions")
    
    async def _plan_sequence(
        self,
        context: Dict[str, Any],
        session_state: Optional[Any]
    ) -> AgentResponse:
        current_difficulty = context.get("current_difficulty", 0.5)
        recent_scores = context.get("recent_scores", [])
        
        if not recent_scores:
            return self._create_response(True, {"adjusted_difficulty": current_difficulty})
        
        avg_score = sum(recent_scores) / len(recent_scores)
        

        if avg_score > 0.8:
            new_difficulty = min(1.0, current_difficulty + 0.15)
        elif avg_score < 0.5:
            new_difficulty = max(0.2, current_difficulty - 0.15)
        else:
            new_difficulty = current_difficulty
        
        return self._create_response(
            True,
            {
                "adjusted_difficulty": new_difficulty,
                "previous_difficulty": current_difficulty,
                "avg_score": avg_score
            }
        )

    async def _plan_exam(self, context: Dict[str, Any]) -> AgentResponse:
        num_questions = context.get("num_questions", 10)
        adaptive = context.get("adaptive", True)
        unit_ids = context.get("unit_ids") or list(self.knowledge_service.knowledge_base.keys())

        max_score_per_question = 100
        pass_percent = 0.56
        total_max = num_questions * max_score_per_question
        pass_score = round(total_max * pass_percent, 1)

        plan = {
            "num_questions": num_questions,
            "adaptive": adaptive,
            "scoring": {
                "max_score_per_question": max_score_per_question,
                "total_max_score": total_max,
                "pass_percent": pass_percent,
                "pass_score": pass_score,
            },
            "difficulty_curve": "adaptive",
            "unit_ids": unit_ids[: num_questions + 5],
        }
        return self._create_response(True, {"exam_plan": plan, "scoring_config": plan["scoring"]})

