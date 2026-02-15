from typing import Dict, Any, List, Optional
from backend.services.agents.base_agent import BaseAgent
from backend.models.session import AgentRequest, AgentResponse, AgentType, DialogueTactic
from backend.services.llm_client import LLMClient


class DialogueAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.DIALOGUE)
        self.llm = LLMClient()
    
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
            elif action == "rephrase_or_prompt_question":
                return await self._rephrase_or_prompt_question(context, session_state)

            return self._create_response(False, error=f"Unknown action: {action}")
        
        except Exception as e:
            return self._create_response(False, error=str(e))
    
    def _get_dialogue_context(self, session_state, max_messages: int = 12) -> str:
        if not session_state or not session_state.dialogue_history:
            return ""
        recent_messages = session_state.dialogue_history[-max_messages:]
        context_parts = []
        for msg in recent_messages:
            sender = msg.get("sender", "unknown")
            text = (msg.get("text") or "")[:350]
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
            tactic_instruction = "Одно короткое сообщение: подсказка или указание на ошибку. Без уточняющих вопросов."
        elif tactic == DialogueTactic.HINT:
            tactic_instruction = "Одна короткая подсказка (1 предложение), не раскрывая ответ полностью."
        elif tactic == DialogueTactic.ANALOGY:
            tactic_instruction = "Краткая аналогия или пример (1-2 предложения)."
        elif tactic == DialogueTactic.ENCOURAGEMENT:
            tactic_instruction = "Короткая поддержка (1 предложение)."
        
        system_prompt = "Ты преподаватель. Отвечай кратко, без лишних переспросов и уточнений."
        user_prompt = f"""Контекст диалога:
{dialogue_context}

Сообщение студента: {user_message}

{tactic_instruction}"""
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response_text = self.llm.chat(messages, temperature=0.7, max_tokens=300)
            
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
        dialogue_context = context.get("dialogue_context") or self._get_dialogue_context(session_state)
        context_block = f"Контекст диалога:\n{dialogue_context}\n\n" if dialogue_context else ""

        system_prompt = """Ты преподаватель. Не перегружай студента уточнениями.
Дай одну короткую обратную связь: что не так и как лучше (1-2 предложения). Не задавай уточняющий вопрос — сразу кратко направь к правильной мысли или укажи ошибку. Без переспросов."""
        user_prompt = f"""{context_block}Вопрос: {question}
Ответ студента: {answer}
Ошибка: {error_analysis.get('error_description', '')}

Дай одну короткую подсказку или указание на ошибку (1-2 предложения). Не задавай вопрос, не проси переформулировать."""
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response_text = self.llm.chat(messages, temperature=0.6, max_tokens=120)
            
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
        
        system_prompt = "Ты преподаватель. Кратко (1-2 предложения) — аналогия или пример. Без длинных объяснений."
        user_prompt = f"""Концепция: {concept}
Вопрос: {question}

Одна короткая аналогия или пример."""
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response_text = self.llm.chat(messages, temperature=0.6, max_tokens=400)
            
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
        
        system_prompt = "Ты преподаватель. Одна короткая подсказка (1 предложение), без раскрытия ответа. Без переспросов."
        user_prompt = f"""Вопрос: {question}
Ответ студента: {answer}

Одна короткая подсказка, направляющая к правильному ответу."""
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response_text = self.llm.chat(messages, temperature=0.6, max_tokens=200)
            
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
        
        system_prompt = "Ты преподаватель. Кратко объясни правильный ответ (2-3 предложения). Без лишнего."
        user_prompt = f"""Вопрос: {question}
Правильный ответ: {correct_answer}
Концепция: {concept}

Краткое объяснение (2-3 предложения)."""
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response_text = self.llm.chat(messages, temperature=0.5, max_tokens=500)
            
            return self._create_response(
                True,
                {"response": response_text}
            )
        
        except Exception as e:
            return self._create_response(False, error=str(e))

    async def _rephrase_or_prompt_question(
        self,
        context: Dict[str, Any],
        session_state: Optional[Any],
    ) -> AgentResponse:
        question = context.get("question", "")
        answer = (context.get("answer") or "").strip()
        level = context.get("simplification_level", 0)
        rephrase_tactic = context.get("rephrase_tactic", "rephrase")
        dialogue_context = context.get("dialogue_context") or self._get_dialogue_context(session_state)
        context_block = f"Контекст диалога (что уже было):\n{dialogue_context}\n\n" if dialogue_context else ""

        tactic_focus = {
            "rephrase": "переформулируй вопрос проще или другими словами",
            "simplify": "упрости вопрос до предела, самый простой вариант",
            "example": "приведи пример из жизни и задай вопрос про этот пример",
            "ask_experience": "спроси про занятость или опыт студента, чтобы опереться на его опыт",
        }.get(rephrase_tactic, "переформулируй вопрос")

        level_instructions = {
            0: f"""Уровень 0: {tactic_focus}. Одно короткое сообщение. Не давай правильный ответ.""",
            1: f"""Уровень 1: упрости вопрос сильнее ИЛИ пример из жизни. Приоритет тактики: {tactic_focus}. Одно сообщение. Не давай правильный ответ.""",
            2: f"""Уровень 2: упрости до предела ИЛИ спроси про работу/учёбу студента. Приоритет: {tactic_focus}. Одно сообщение. Не давай правильный ответ.""",
            3: f"""Уровень 3: спроси про опыт/занятость студента или самый простой вопрос. Приоритет: {tactic_focus}. Одно сообщение. Не давай правильный ответ.""",
        }
        level_instruction = level_instructions.get(min(level, 3), level_instructions[0])

        system_prompt = f"""Ты преподаватель на экзамене. Студент ответил пусто или очень коротко.
Используй лестницу упрощений: с каждым уровнем упрощай вопрос или подключай примеры из жизни и опыт студента.
{level_instruction}
Ответь одним коротким сообщением (1-3 предложения). Не повторяй один и тот же вопрос. Без лишних слов."""

        user_prompt = f"""{context_block}Вопрос: {question}
Ответ студента: "{answer}"

Сформируй одно сообщение по инструкции для уровня {level}."""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            response_text = self.llm.chat(messages, temperature=0.5, max_tokens=180)
            return self._create_response(
                True,
                {"response": response_text, "tactic": "rephrase"}
            )
        except Exception as e:
            return self._create_response(False, error=str(e))
