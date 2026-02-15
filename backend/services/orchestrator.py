import logging
import random
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from backend.repositories import student_analytics as student_analytics_repo
from backend.models.session import (
    SessionState, SessionStatus, AgentRequest, AgentResponse,
    Workflow, WorkflowStep, AgentType, DialogueTactic
)
from backend.services.agents import (
    KnowledgeAgent, DialogueAgent, CriticAgent,
    PlanningAgent, AnalyticsAgent, AdaptiveExamAgent
)
from backend.services.knowledge_service import KnowledgeService

logger = logging.getLogger("exam_system.orchestrator")


class CoreOrchestrator:
    def __init__(self, knowledge_service: KnowledgeService):
        self.knowledge_service = knowledge_service
        self.knowledge_agent = KnowledgeAgent(knowledge_service)
        self.dialogue_agent = DialogueAgent()
        self.critic_agent = CriticAgent()
        self.planning_agent = PlanningAgent(knowledge_service)
        self.analytics_agent = AnalyticsAgent()
        self.adaptive_exam_agent = AdaptiveExamAgent()
        self.sessions: Dict[str, SessionState] = {}
        self.workflows: Dict[str, Workflow] = {}
    
    def create_session(self, student_id: str, exam_id: Optional[str] = None) -> SessionState:
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        logger.info("create_session session_id=%s student_id=%s exam_id=%s", session_id, student_id, exam_id)
        session = SessionState(
            session_id=session_id,
            student_id=student_id,
            exam_id=exam_id,
            status=SessionStatus.ACTIVE,
        )
        self.sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        return self.sessions.get(session_id)
    
    def _is_answer_empty_or_skip(self, answer: str) -> bool:
        if not answer or not answer.strip():
            return True
        s = answer.strip().lower()
        if len(s) < 3:
            return True
        skip_phrases = ("не знаю", "пропустить", "не могу", "нет", "не помню", "skip", "idk")
        return any(s.startswith(p) or p in s for p in skip_phrases)

    def _session_scores(self, session: SessionState) -> tuple:
        total, max_total = 0.0, 0.0
        for msg in session.dialogue_history or []:
            ev = msg.get("evaluation") or {}
            if not ev.get("is_correct"):
                continue
            s, m = ev.get("score", 0), ev.get("max_score", 100)
            if m and m > 0:
                total += float(s)
                max_total += float(m)
        return (total if total else None, max_total if max_total else None)

    def _build_dialogue_context(
        self,
        session: SessionState,
        max_messages: int = 14,
        max_chars: int = 3500,
        min_messages: int = 4,
    ) -> str:
        if not session or not session.dialogue_history:
            return ""
        recent = session.dialogue_history[-max_messages:]
        n_required = min(min_messages, len(recent))
        required = recent[-n_required:] if n_required else []
        optional = recent[:-n_required] if len(recent) > n_required else []
        parts = []
        total = 0
        for msg in optional:
            sender = msg.get("sender", "unknown")
            text = (msg.get("text") or "")[:400]
            line = f"{sender}: {text}"
            if total + len(line) > max_chars:
                parts.append(line[: max_chars - total])
                break
            parts.append(line)
            total += len(line)
        for msg in required:
            sender = msg.get("sender", "unknown")
            text = (msg.get("text") or "")[:400]
            parts.append(f"{sender}: {text}")
        return "\n".join(parts)

    async def process_student_answer(
        self,
        session_id: str,
        question_id: str,
        answer: str,
        question_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        logger.info("process_student_answer session_id=%s question_id=%s answer_len=%s", session_id, question_id, len(answer or ""))
        session = self.get_session(session_id)
        if not session:
            logger.warning("process_student_answer session not found session_id=%s", session_id)
            raise ValueError(f"Session {session_id} not found")
        if session.status == SessionStatus.COMPLETED:
            raise ValueError("Экзамен уже завершён")

        if self._is_answer_empty_or_skip(answer):
            level = getattr(session, "current_simplification_level", 0)
            strategy_request = AgentRequest(
                agent_type=AgentType.ADAPTIVE_EXAM,
                action="recommend_response_strategy",
                context={
                    "question": question_data.get("question", ""),
                    "answer": answer or "",
                    "dialogue_context": self._build_dialogue_context(session),
                    "current_simplification_level": level,
                },
                session_state=session,
            )
            strategy_response = await self.adaptive_exam_agent.process(strategy_request)
            if strategy_response.success:
                level = strategy_response.data.get("simplification_level", level)
                rephrase_tactic = strategy_response.data.get("rephrase_tactic", "rephrase")
            else:
                rephrase_tactic = "rephrase"
            logger.info("process_student_answer empty/skip rephrasing question_id=%s level=%s tactic=%s", question_id, level, rephrase_tactic)
            rephrase_request = AgentRequest(
                agent_type=AgentType.DIALOGUE,
                action="rephrase_or_prompt_question",
                context={
                    "question": question_data.get("question", ""),
                    "answer": answer or "",
                    "dialogue_context": self._build_dialogue_context(session),
                    "simplification_level": level,
                    "rephrase_tactic": rephrase_tactic,
                },
                session_state=session,
            )
            rephrase_response = await self.dialogue_agent.process(rephrase_request)
            rephrase_text = rephrase_response.data.get("response", "Попробуйте сформулировать ответ своими словами.") if rephrase_response.success else "Попробуйте сформулировать ответ."
            dialogue_user = {"sender": "user", "text": answer or "(пусто)", "timestamp": datetime.now().isoformat(), "question_id": question_id}
            session.dialogue_history.append(dialogue_user)
            session.dialogue_history.append({
                "sender": "ai",
                "text": rephrase_text,
                "timestamp": datetime.now().isoformat(),
                "tactic": "rephrase",
                "type": "rephrase",
            })
            session.current_simplification_level = min(3, level + 1)
            session.updated_at = datetime.now().isoformat()
            return {
                "evaluation": {},
                "is_correct": False,
                "score": 0,
                "max_score": 100,
                "clarification": rephrase_text,
                "error_analysis": None,
                "reasoning_analysis": None,
                "tactic": "rephrase",
            }

        total_so_far, _ = self._session_scores(session)
        already_earned = float(total_so_far or 0)
        max_for_question = float(question_data.get("max_score_for_this_question") or 100.0)

        critic_request = AgentRequest(
            agent_type=AgentType.CRITIC,
            action="evaluate_answer",
            context={
                "question": question_data.get("question", ""),
                "answer": answer,
                "reference_answer": question_data.get("reference_answer", ""),
                "criteria": question_data.get("criteria", []),
                "dialogue_context": self._build_dialogue_context(session),
                "num_questions": question_data.get("total_questions"),
                "question_number": question_data.get("question_number"),
                "total_exam_points": 100,
                "min_to_pass": 56,
                "already_earned": already_earned,
                "max_score_for_this_question": max_for_question,
            },
            session_state=session
        )
        
        evaluation_response = await self.critic_agent.process(critic_request)
        
        if not evaluation_response.success:
            raise ValueError("Failed to evaluate answer")
        
        evaluation = evaluation_response.data.get("evaluation", {})
        raw_score = float(evaluation.get("score", 0) or 0)
        score = max(0.0, min(max_for_question, raw_score))
        evaluation["score"] = score
        evaluation["max_score"] = max_for_question
        max_score = max_for_question
        is_correct = evaluation.get("is_correct", False)
        if is_correct:
            session.current_simplification_level = 0
        session.answered_questions.append(question_id)
        
        dialogue_message = {
            "sender": "user",
            "text": answer,
            "timestamp": datetime.now().isoformat(),
            "question_id": question_id
        }
        session.dialogue_history.append(dialogue_message)
        
        result = {
            "evaluation": evaluation,
            "is_correct": is_correct,
            "score": score,
            "max_score": max_score,
            "clarification": None,
            "error_analysis": None,
            "reasoning_analysis": None,
            "tactic": None
        }
        
        if not is_correct:
            reasoning_request = AgentRequest(
                agent_type=AgentType.CRITIC,
                action="analyze_reasoning",
                context={
                    "question": question_data.get("question", ""),
                    "answer": answer,
                    "reference_answer": question_data.get("reference_answer", ""),
                    "dialogue_context": self._build_dialogue_context(session),
                },
                session_state=session
            )
            
            reasoning_response = await self.critic_agent.process(reasoning_request)
            if reasoning_response.success:
                result["reasoning_analysis"] = reasoning_response.data.get("reasoning_analysis", {})
            
            error_request = AgentRequest(
                agent_type=AgentType.CRITIC,
                action="identify_error",
                context={
                    "question": question_data.get("question", ""),
                    "answer": answer,
                    "reference_answer": question_data.get("reference_answer", ""),
                    "reasoning_analysis": result.get("reasoning_analysis", {}),
                    "dialogue_context": self._build_dialogue_context(session),
                },
                session_state=session
            )
            
            error_response = await self.critic_agent.process(error_request)
            if error_response.success:
                result["error_analysis"] = error_response.data.get("error_analysis", {})
            
            clarification_request = AgentRequest(
                agent_type=AgentType.DIALOGUE,
                action="generate_clarification",
                context={
                    "question": question_data.get("question", ""),
                    "answer": answer,
                    "error_analysis": result.get("error_analysis", {}),
                    "dialogue_context": self._build_dialogue_context(session),
                },
                session_state=session
            )
            
            clarification_response = await self.dialogue_agent.process(clarification_request)
            if clarification_response.success:
                result["clarification"] = clarification_response.data.get("response", "")
                result["tactic"] = str(DialogueTactic.CLARIFICATION)
            
            session.current_tactic = DialogueTactic.CLARIFICATION
            if result.get("error_analysis"):
                error_desc = result["error_analysis"].get("error_description", "")
                if error_desc:
                    session.knowledge_gaps.append(error_desc)
        
        dialogue_response = {
            "sender": "system",
            "text": result.get("clarification") or evaluation.get("overall_feedback", ""),
            "timestamp": datetime.now().isoformat(),
            "evaluation": evaluation,
            "tactic": result.get("tactic")
        }
        session.dialogue_history.append(dialogue_response)
        
        analytics_request = AgentRequest(
            agent_type=AgentType.ANALYTICS,
            action="record_metric",
            context={
                "session_id": session_id,
                "student_id": session.student_id,
                "question_id": question_id,
                "evaluation": evaluation,
                "tactic_used": result.get("tactic")
            },
            session_state=session
        )
        await self.analytics_agent.process(analytics_request)

        total_score, max_total = self._session_scores(session)
        metric_record = {
            "timestamp": datetime.now().isoformat(),
            "question_id": question_id,
            "evaluation": evaluation,
            "tactic_used": result.get("tactic"),
        }
        student_analytics_repo.append_metric(
            session_id=session_id,
            student_id=session.student_id,
            exam_id=session.exam_id,
            metric=metric_record,
            total_score=total_score,
            max_total_score=max_total,
            questions_answered=len(session.answered_questions),
        )

        session.updated_at = datetime.now().isoformat()
        
        logger.info("process_student_answer done session_id=%s is_correct=%s has_clarification=%s",
                    session_id, result.get("is_correct"), bool(result.get("clarification")))
        return result

    async def get_next_question(
        self,
        session_id: str,
        exam_config: Dict[str, Any],
        exam_service: Optional[Any] = None,
    ) -> Dict[str, Any]:
        logger.info("get_next_question session_id=%s exam_id=%s", session_id, getattr(self.get_session(session_id), "exam_id", None))
        session = self.get_session(session_id)
        if not session:
            logger.warning("get_next_question session not found session_id=%s", session_id)
            raise ValueError(f"Session {session_id} not found")
        if session.status == SessionStatus.COMPLETED:
            raise ValueError("Экзамен уже завершён")

        if exam_service and session.exam_id:
            exam = exam_service.get_exam(session.exam_id)
            if exam and getattr(exam, "questions", None):
                answered = set(session.answered_questions)
                if session.question_order is None:
                    ids = [q.get("question_id") or q.get("id") for q in exam.questions if q.get("question_id") or q.get("id")]
                    session.question_order = list(ids)
                    random.shuffle(session.question_order)
                q_by_id = {q.get("question_id") or q.get("id"): q for q in exam.questions if q.get("question_id") or q.get("id")}
                for qid in session.question_order:
                    if qid not in answered and qid in q_by_id:
                        q = q_by_id[qid]
                        question_data = dict(q)
                        if not question_data.get("question_id"):
                            question_data["question_id"] = qid
                        session.current_question_id = question_data.get("question_id")
                        session.dialogue_history.append({
                            "sender": "ai",
                            "text": question_data.get("question", ""),
                            "type": "question",
                            "question_id": question_data.get("question_id"),
                            "timestamp": datetime.now().isoformat(),
                        })
                        logger.info("get_next_question from exam session_id=%s question_id=%s", session_id, question_data.get("question_id"))
                        return question_data
                logger.info("get_next_question no more questions in exam session_id=%s", session_id)
                raise ValueError("No more questions in exam")

        recent_evaluations = []
        for msg in session.dialogue_history:
            if msg.get("evaluation"):
                recent_evaluations.append(msg.get("evaluation"))
        student_performance = {
            "answered_questions": len(session.answered_questions),
            "knowledge_gaps": session.knowledge_gaps,
        }
        cat_request = AgentRequest(
            agent_type=AgentType.ADAPTIVE_EXAM,
            action="recommend_next_difficulty",
            context={
                "recent_evaluations": recent_evaluations,
                "exam_config": exam_config,
                "answered_questions_count": len(session.answered_questions),
            },
            session_state=session,
        )
        cat_response = await self.adaptive_exam_agent.process(cat_request)
        if cat_response.success:
            next_difficulty = cat_response.data.get("next_difficulty", 0.5)
            student_performance["current_difficulty"] = next_difficulty
            student_performance["ability_estimate"] = cat_response.data.get("ability_estimate", 0.5)
        if recent_evaluations:
            scores = [e.get("score", 0) / e.get("max_score", 100)
                     for e in recent_evaluations if e.get("max_score", 100) > 0]
            if scores:
                student_performance["avg_score"] = sum(scores) / len(scores)
        planning_request = AgentRequest(
            agent_type=AgentType.PLANNING,
            action="select_next_question",
            context={
                "exam_config": exam_config,
                "answered_questions": session.answered_questions,
                "student_performance": student_performance
            },
            session_state=session
        )
        response = await self.planning_agent.process(planning_request)
        if response.success:
            question_data = response.data.get("question", {})
            session.current_question_id = question_data.get("question_id")
            session.dialogue_history.append({
                "sender": "ai",
                "text": question_data.get("question", ""),
                "type": "question",
                "question_id": question_data.get("question_id"),
                "timestamp": datetime.now().isoformat(),
            })
            logger.info("get_next_question success session_id=%s question_id=%s", session_id, question_data.get("question_id"))
            return question_data
        logger.warning("get_next_question no question session_id=%s", session_id)
        raise ValueError("Failed to get next question")
    
    async def generate_insights(
        self,
        session_id: str,
        student_id: str
    ) -> Dict[str, Any]:
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        analytics_request = AgentRequest(
            agent_type=AgentType.ANALYTICS,
            action="generate_insights",
            context={
                "session_id": session_id,
                "student_id": student_id
            },
            session_state=session
        )
        
        response = await self.analytics_agent.process(analytics_request)

        if response.success:
            insights = response.data.get("insights", {})
            student_analytics_repo.save_insights(session_id, student_id, insights)
            return response.data

        raise ValueError("Failed to generate insights")
    
    def get_dialogue_history(self, session_id: str) -> List[Dict[str, Any]]:
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        return session.dialogue_history

    def complete_session(self, session_id: str) -> Dict[str, Any]:
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        if session.status == SessionStatus.COMPLETED:
            total_score, max_total = self._session_scores(session)
            total = min(100, total_score or 0)
            return {
                "session_id": session_id,
                "status": "completed",
                "total_score": total,
                "max_total_score": max_total or 100,
                "questions_answered": len(session.answered_questions),
                "passed": total >= 56,
            }
        session.status = SessionStatus.COMPLETED
        session.updated_at = datetime.now().isoformat()
        total_score, max_total = self._session_scores(session)
        total = min(100, total_score or 0)
        student_analytics_repo.append_metric(
            session_id=session_id,
            student_id=session.student_id,
            exam_id=session.exam_id,
            metric={"type": "session_completed", "timestamp": datetime.now().isoformat()},
            total_score=total,
            max_total_score=max_total or 100,
            questions_answered=len(session.answered_questions),
        )
        logger.info("complete_session session_id=%s total=%s max=%s", session_id, total_score, max_total)
        return {
            "session_id": session_id,
            "status": "completed",
            "total_score": total,
            "max_total_score": max_total or 100,
            "questions_answered": len(session.answered_questions),
            "passed": total >= 56,
        }
