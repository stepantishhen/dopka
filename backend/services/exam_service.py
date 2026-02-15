import json
from typing import Dict, List, Optional
from datetime import datetime
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
import re

from backend.models.exam_system import Exam, ExamConfig, StudentAnswer, StudentProfile, EmotionalState
from backend.config import settings
from backend.services.knowledge_service import KnowledgeService


class ExamService:
    def __init__(self, knowledge_service: KnowledgeService):
        self.giga = GigaChat(credentials=settings.gigachat_credentials, verify_ssl_certs=False)
        self.knowledge_service = knowledge_service
        self.exams: Dict[str, Exam] = {}
        self.current_exam: Optional[Exam] = None
        self.student_profiles: Dict[str, StudentProfile] = {}
        self.exam_results: List[Dict] = []
    
    def safe_parse_json(self, text: str) -> Optional[Dict]:
        if not text:
            return None
        
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
            return None
        
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
            print(f"JSON parsing error: {e}")
            return None
    
    def create_exam(self, exam_config: ExamConfig) -> Exam:
        exam_id = f"exam_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        questions = []
        if exam_config.adaptive:
            questions = self._generate_adaptive_questions(exam_config)
        else:
            questions = self._generate_fixed_questions(exam_config)
        
        exam = Exam(
            exam_id=exam_id,
            config=exam_config,
            status="active",
            questions=questions,
            link=f"/exam/{exam_id}"
        )
        
        self.exams[exam_id] = exam
        self.current_exam = exam
        
        return exam
    
    def _generate_adaptive_questions(self, config: ExamConfig) -> List[Dict]:
        questions = []
        unit_ids = config.unit_ids or list(self.knowledge_service.knowledge_base.keys())
        
        for unit_id in unit_ids[:config.num_questions]:
            unit = self.knowledge_service.get_unit(unit_id)
            if unit and unit.questions.get("understanding"):
                if questions:
                    break
                question = unit.questions["understanding"][0].copy()
                question["adaptive_data"] = {
                    "unit_id": unit_id,
                    "estimated_difficulty": unit.difficulty_level
                }
                questions.append(question)
        
        return questions
    
    def _generate_fixed_questions(self, config: ExamConfig) -> List[Dict]:
        questions = []
        unit_ids = config.unit_ids or list(self.knowledge_service.knowledge_base.keys())
        
        for unit_id in unit_ids:
            if len(questions) >= config.num_questions:
                break
            
            unit = self.knowledge_service.get_unit(unit_id)
            if not unit:
                continue
            
            for q_type in ["understanding", "application", "analysis"]:
                if len(questions) >= config.num_questions:
                    break
                
                if unit.questions.get(q_type):
                    for q in unit.questions[q_type][:2]:
                        questions.append(q.copy())
        
        return questions[:config.num_questions]
    
    def get_exam(self, exam_id: str) -> Optional[Exam]:
        return self.exams.get(exam_id)
    
    def get_current_exam(self) -> Optional[Exam]:
        return self.current_exam
    
    def evaluate_student_answers(self, student_id: str, answers: List[StudentAnswer]) -> Dict:
        total_score = 0
        max_score = 0
        evaluations = []
        knowledge_gaps = []
        
        for answer in answers:
            question = None
            for q in self.knowledge_service.questions_db:
                if q.get("question_id") == answer.question_id:
                    question = q
                    break
            
            if question:
                evaluation = self._evaluate_single_answer(question, answer.answer)
                evaluations.append(evaluation)
                total_score += evaluation.get("score", 0)
                max_score += sum(c.get("max_score", 1) for c in question.get("criteria", []))
        
        report = {
            "student_id": student_id,
            "evaluation_date": datetime.now().isoformat(),
            "total_score": total_score,
            "max_score": max_score,
            "percentage": (total_score / max_score * 100) if max_score > 0 else 0,
            "evaluations": evaluations,
            "knowledge_gaps": knowledge_gaps,
            "recommendations": [],
            "strengths": []
        }
        
        self.exam_results.append(report)
        
        if student_id in self.student_profiles:
            profile = self.student_profiles[student_id]
            profile.last_evaluation = report
            profile.learning_history.append({
                "timestamp": datetime.now().isoformat(),
                "type": "evaluation",
                "report": report
            })
        
        return report
    
    def _evaluate_single_answer(self, question: Dict, answer: str) -> Dict:
        system_prompt = "Ты эксперт-преподаватель, оценивающий ответы студентов. Оценивай объективно и конструктивно."
        user_prompt = f"""Вопрос: {question.get('question', '')}
Критерии: {json.dumps(question.get('criteria', []), ensure_ascii=False)}
Эталонный ответ: {question.get('reference_answer', 'Не предоставлен')}
Ответ студента: {answer}

Оцени ответ. Формат ответа ТОЛЬКО JSON:
{{
    "score": 8.5,
    "max_score": 10,
    "criteria_scores": [],
    "overall_feedback": "Обратная связь",
    "errors": [],
    "strengths": [],
    "improvement_suggestions": []
}}"""
        
        try:
            messages = [
                Messages(role=MessagesRole.SYSTEM, content=system_prompt),
                Messages(role=MessagesRole.USER, content=user_prompt)
            ]
            payload = Chat(messages=messages, temperature=0.3, max_tokens=1000)
            response = self.giga.chat(payload)
            response_text = response.choices[0].message.content
            
            data = self.safe_parse_json(response_text)
            if data:
                return data
            
            return {
                "score": 0,
                "max_score": 10,
                "criteria_scores": [],
                "overall_feedback": "Не удалось оценить ответ",
                "errors": [],
                "strengths": [],
                "improvement_suggestions": []
            }
        except Exception as e:
            print(f"Ошибка при оценке ответа: {e}")
            return {
                "score": 0,
                "max_score": 10,
                "criteria_scores": [],
                "overall_feedback": f"Ошибка при оценке: {str(e)}",
                "errors": [],
                "strengths": [],
                "improvement_suggestions": []
            }
    
    def get_or_create_student(self, student_id: str, name: str = "", group: str = "") -> StudentProfile:
        if student_id not in self.student_profiles:
            self.student_profiles[student_id] = StudentProfile(
                student_id=student_id,
                name=name,
                group=group
            )
        return self.student_profiles[student_id]

