from typing import Dict, Any, List, Optional
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from backend.services.agents.base_agent import BaseAgent
from backend.models.session import AgentRequest, AgentResponse, AgentType, DialogueTactic
from backend.config import settings


class DialogueAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.DIALOGUE)
        self.giga = GigaChat(credentials=settings.gigachat_credentials, verify_ssl_certs=False)
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        action = request.action
        context = request.context
        session_state = request.session_state
        
        try:
            if action == "generate_response":
                return await self._generate_response(context, session_state)
            elif action == "generate_clarification":
                return await self._generate_clarification(context, session_state)
            elif action == "generate_hint":
                return await self._generate_hint(context, session_state)
            elif action == "generate_analogy":
                return await self._generate_analogy(context, session_state)
            elif action == "generate_explanation":
                return await self._generate_explanation(context, session_state)
            
            return self._create_response(False, error=f"Unknown action: {action}")
        
        except Exception as e:
            return self._create_response(False, error=str(e))
    
    def _get_dialogue_context(self, session_state) -> str:
        if not session_state or not session_state.dialogue_history:
            return ""
        
        recent_messages = session_state.dialogue_history[-5:]
        context_parts = []
        for msg in recent_messages:
            sender = msg.get("sender", "unknown")
            text = msg.get("text", "")
            context_parts.append(f"{sender}: {text}")
        
        return "\n".join(context_parts)
    
    async def _generate_response(
        self,
        context: Dict[str, Any],
        session_state: Optional[Any]
    ) -> AgentResponse:
        user_message = context.get("message", "")
        tactic = context.get("tactic")
        
        dialogue_context = self._get_dialogue_context(session_state)
        
        tactic_instruction = ""
        if tactic == DialogueTactic.CLARIFICATION:
            tactic_instruction = "Задай уточняющий вопрос, чтобы понять ход мыслей студента."
        elif tactic == DialogueTactic.HINT:
            tactic_instruction = "Дай небольшую подсказку, не раскрывая ответ полностью."
        elif tactic == DialogueTactic.ANALOGY:
            tactic_instruction = "Приведи аналогию или пример, чтобы помочь понять."
        elif tactic == DialogueTactic.ENCOURAGEMENT:
            tactic_instruction = "Поддержи студента, отметь прогресс."
        
        system_prompt = "Ты опытный преподаватель, ведущий диалог со студентом для помощи в обучении."
        user_prompt = f"""Контекст диалога:
{dialogue_context}

Сообщение студента: {user_message}

{tactic_instruction}"""
        
        try:
            messages = [
                Messages(role=MessagesRole.SYSTEM, content=system_prompt),
                Messages(role=MessagesRole.USER, content=user_prompt)
            ]
            payload = Chat(messages=messages, temperature=0.7, max_tokens=300)
            response = self.giga.chat(payload)
            response_text = response.choices[0].message.content
            
            return self._create_response(
                True,
                {"response": response_text, "tactic": str(tactic) if tactic else None}
            )
        
        except Exception as e:
            return self._create_response(False, error=str(e))
    
    async def _generate_clarification(
        self,
        context: Dict[str, Any],
        session_state: Optional[Any]
    ) -> AgentResponse:
        answer = context.get("answer", "")
        error_analysis = context.get("error_analysis", {})
        question = context.get("question", "")
        knowledge_gaps = context.get("knowledge_gaps", [])
        
        system_prompt = "Ты опытный преподаватель, задающий уточняющие вопросы для помощи студентам."
        user_prompt = f"""Ответ студента: {answer}
Анализ ошибки: {error_analysis.get('error_description', '')}

Задай уточняющий вопрос, который поможет студенту понять свою ошибку.
Не давай прямой ответ, только направляй."""
        
        try:
            messages = [
                Messages(role=MessagesRole.SYSTEM, content=system_prompt),
                Messages(role=MessagesRole.USER, content=user_prompt)
            ]
            payload = Chat(messages=messages, temperature=0.7, max_tokens=200)
            response = self.giga.chat(payload)
            response_text = response.choices[0].message.content
            
            return self._create_response(
                True,
                {
                    "response": response_text,
                    "tactic": str(DialogueTactic.CLARIFICATION)
                }
            )
        
        except Exception as e:
            return self._create_response(False, error=str(e))
    
    async def _generate_analogy(
        self,
        context: Dict[str, Any],
        session_state: Optional[Any]
    ) -> AgentResponse:
        concept = context.get("concept", "")
        question = context.get("question", "")
        error_analysis = context.get("error_analysis", {})
        correct_answer = context.get("correct_answer", "")
        
        system_prompt = "Ты преподаватель, использующий аналогии и примеры для объяснения сложных концепций."
        user_prompt = f"""Концепция: {concept}
Вопрос: {question}

Приведи аналогию или пример, который поможет студенту понять концепцию."""
        
        try:
            messages = [
                Messages(role=MessagesRole.SYSTEM, content=system_prompt),
                Messages(role=MessagesRole.USER, content=user_prompt)
            ]
            payload = Chat(messages=messages, temperature=0.6, max_tokens=400)
            response = self.giga.chat(payload)
            response_text = response.choices[0].message.content
            
            return self._create_response(
                True,
                {"response": response_text}
            )
        
        except Exception as e:
            return self._create_response(False, error=str(e))
    
    async def _generate_hint(
        self,
        context: Dict[str, Any],
        session_state: Optional[Any]
    ) -> AgentResponse:
        question = context.get("question", "")
        answer = context.get("answer", "")
        
        system_prompt = "Ты преподаватель, дающий подсказки студентам без раскрытия полного ответа."
        user_prompt = f"""Вопрос: {question}
Ответ студента: {answer}

Дай небольшую подсказку, которая направит студента к правильному ответу, но не раскрывай ответ полностью."""
        
        try:
            messages = [
                Messages(role=MessagesRole.SYSTEM, content=system_prompt),
                Messages(role=MessagesRole.USER, content=user_prompt)
            ]
            payload = Chat(messages=messages, temperature=0.6, max_tokens=200)
            response = self.giga.chat(payload)
            response_text = response.choices[0].message.content
            
            return self._create_response(
                True,
                {"response": response_text, "tactic": str(DialogueTactic.HINT)}
            )
        
        except Exception as e:
            return self._create_response(False, error=str(e))
    
    async def _generate_explanation(
        self,
        context: Dict[str, Any],
        session_state: Optional[Any]
    ) -> AgentResponse:
        question = context.get("question", "")
        correct_answer = context.get("correct_answer", "")
        concept = context.get("concept", "")
        
        system_prompt = "Ты преподаватель, объясняющий концепции и правильные ответы студентам."
        user_prompt = f"""Вопрос: {question}
Правильный ответ: {correct_answer}
Концепция: {concept}

Объясни студенту правильный ответ и связанную концепцию."""
        
        try:
            messages = [
                Messages(role=MessagesRole.SYSTEM, content=system_prompt),
                Messages(role=MessagesRole.USER, content=user_prompt)
            ]
            payload = Chat(messages=messages, temperature=0.5, max_tokens=500)
            response = self.giga.chat(payload)
            response_text = response.choices[0].message.content
            
            return self._create_response(
                True,
                {"response": response_text}
            )
        
        except Exception as e:
            return self._create_response(False, error=str(e))

