from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from backend.models.session import (
    SessionState, SessionStatus, AgentRequest, AgentResponse,
    Workflow, WorkflowStep, AgentType, DialogueTactic
)
from backend.services.agents import (
    KnowledgeAgent, DialogueAgent, CriticAgent,
    PlanningAgent, AnalyticsAgent
)
from backend.services.knowledge_service import KnowledgeService


class CoreOrchestrator:
    def __init__(self, knowledge_service: KnowledgeService):
        self.knowledge_service = knowledge_service
        self.knowledge_agent = KnowledgeAgent(knowledge_service)
        self.dialogue_agent = DialogueAgent()
        self.critic_agent = CriticAgent()
        self.planning_agent = PlanningAgent(knowledge_service)
        self.analytics_agent = AnalyticsAgent()
        self.sessions: Dict[str, SessionState] = {}
        self.workflows: Dict[str, Workflow] = {}
    
    def create_session(self, student_id: str, exam_id: Optional[str] = None) -> SessionState:
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        session = SessionState(
            session_id=session_id,
            student_id=student_id,
            exam_id=exam_id
        )
        self.sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        return self.sessions.get(session_id)
    
    async def process_student_answer(
        self,
        session_id: str,
        question_id: str,
        answer: str,
        question_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        critic_request = AgentRequest(
            agent_type=AgentType.CRITIC,
            action="evaluate_answer",
            context={
                "question": question_data.get("question", ""),
                "answer": answer,
                "reference_answer": question_data.get("reference_answer", ""),
                "criteria": question_data.get("criteria", [])
            },
            session_state=session
        )
        
        evaluation_response = await self.critic_agent.process(critic_request)
        
        if not evaluation_response.success:
            raise ValueError("Failed to evaluate answer")
        
        evaluation = evaluation_response.data.get("evaluation", {})
        is_correct = evaluation.get("is_correct", False)
        score = evaluation.get("score", 0)
        max_score = evaluation.get("max_score", 10)
        
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
                    "reference_answer": question_data.get("reference_answer", "")
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
                    "reasoning_analysis": result.get("reasoning_analysis", {})
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
                    "error_analysis": result.get("error_analysis", {})
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
                "question_id": question_id,
                "evaluation": evaluation,
                "tactic_used": result.get("tactic")
            },
            session_state=session
        )
        await self.analytics_agent.process(analytics_request)
        
        session.updated_at = datetime.now().isoformat()
        
        return result
    
    async def get_next_question(
        self,
        session_id: str,
        exam_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        recent_evaluations = []
        for msg in session.dialogue_history:
            if msg.get("evaluation"):
                recent_evaluations.append(msg.get("evaluation"))
        
        student_performance = {
            "answered_questions": len(session.answered_questions),
            "knowledge_gaps": session.knowledge_gaps
        }
        
        if recent_evaluations:
            scores = [e.get("score", 0) / e.get("max_score", 10) 
                     for e in recent_evaluations if e.get("max_score", 10) > 0]
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
            return question_data
        
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
            return response.data
        
        raise ValueError("Failed to generate insights")
    
    def get_dialogue_history(self, session_id: str) -> List[Dict[str, Any]]:
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        return session.dialogue_history
