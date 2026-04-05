import json
import logging
import random
import re
from typing import Dict, List, Optional
from datetime import datetime

from backend.models.exam_system import Exam, ExamConfig, StudentAnswer, StudentProfile, EmotionalState
from backend.services.knowledge_service import KnowledgeService

logger = logging.getLogger("exam_system.exam_service")

TEST_EXAM_ID = "exam_test"
TEST_JOIN_CODE = "TEST01"

TEST_EXAM_QUESTIONS = [
    {
        "question_id": "q_test_1",
        "topic": "Переменные и память",
        "question": "Что такое переменная в программировании?",
        "type": "understanding",
        "difficulty": 0.3,
        "criteria": [{"name": "Определение", "max_score": 5}, {"name": "Пример", "max_score": 5}],
        "reference_answer": "Переменная - именованная область памяти, хранящая значение.",
        "choices": [
            "Именованная область памяти для хранения значения",
            "Константа, которую нельзя изменить после создания",
            "Только целое число",
            "Имя файла с исходным кодом",
        ],
        "correct_choice": 0,
    },
    {
        "question_id": "q_test_2",
        "topic": "Структуры данных",
        "question": "В чём главное отличие list от tuple в Python?",
        "type": "understanding",
        "difficulty": 0.5,
        "criteria": [{"name": "Изменяемость", "max_score": 5}, {"name": "Синтаксис", "max_score": 5}],
        "reference_answer": "List изменяемый, tuple неизменяемый. List использует [], tuple (.",
        "choices": [
            "Список (list) можно изменять, кортеж (tuple) — нет",
            "Отличий нет, это синонимы",
            "tuple всегда короче list",
            "list можно использовать только для строк",
        ],
        "correct_choice": 0,
    },
    {
        "question_id": "q_test_3",
        "topic": "Циклы",
        "question": "Какой фрагмент корректно выводит числа от 1 до 10 в Python?",
        "type": "application",
        "difficulty": 0.4,
        "criteria": [{"name": "Синтаксис цикла", "max_score": 5}, {"name": "Корректный вывод", "max_score": 5}],
        "reference_answer": "for i in range(1, 11): print(i)",
        "choices": [
            "for i in range(1, 11): print(i)",
            "for i in range(10): print(i)",
            "print(list(1, 10))",
            "for i in 1..10: print(i)",
        ],
        "correct_choice": 0,
    },
    {
        "question_id": "q_test_4",
        "topic": "Рекурсия",
        "question": "Что верно про рекурсию?",
        "type": "analysis",
        "difficulty": 0.6,
        "criteria": [{"name": "Определение", "max_score": 5}, {"name": "Базовый случай", "max_score": 5}],
        "reference_answer": "Рекурсия - вызов функцией самой себя. Базовый случай обязателен.",
        "choices": [
            "Функция может вызывать сама себя; нужен базовый случай остановки",
            "Рекурсия запрещена в Python",
            "Это только синоним цикла while",
            "Глубина рекурсии не ограничена интерпретатором",
        ],
        "correct_choice": 0,
    },
    {
        "question_id": "q_test_5",
        "topic": "Типы",
        "question": "Что выведет print(type([])) в Python 3?",
        "type": "understanding",
        "difficulty": 0.2,
        "criteria": [{"name": "Правильный тип", "max_score": 10}],
        "reference_answer": "<class 'list'>",
        "choices": [
            "<class 'list'>",
            "list",
            "array",
            "TypeError",
        ],
        "correct_choice": 0,
    },
]


class ExamService:
    def __init__(self, knowledge_service: KnowledgeService):
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
            logger.debug("safe_parse_json error: %s", e)
            return None

    def _generate_join_code(self) -> str:
        import random
        import string
        chars = string.ascii_uppercase + string.digits
        return "".join(random.choices(chars, k=6))

    def create_exam(self, exam_config: ExamConfig, questions: Optional[List[Dict]] = None) -> Exam:
        exam_id = f"exam_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        join_code = self._generate_join_code()
        logger.debug("create_exam exam_id=%s name=%s questions_provided=%s", exam_id, exam_config.name, questions is not None)
        if questions is None:
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
            link=f"/exam/{exam_id}",
            join_code=join_code
        )
        
        while any(e.join_code == join_code for e in self.exams.values()):
            join_code = self._generate_join_code()
            exam.join_code = join_code
        
        self.exams[exam_id] = exam
        self.current_exam = exam
        logger.info("create_exam stored exam_id=%s join_code=%s questions=%s", exam_id, exam.join_code, len(exam.questions))
        return exam

    def get_exam_by_join_code(self, join_code: str) -> Optional[Exam]:
        for exam in self.exams.values():
            if exam.join_code and exam.join_code.upper() == join_code.upper():
                return exam
        return None

    def get_or_create_test_exam(self) -> Exam:
        existing = self.exams.get(TEST_EXAM_ID)
        if existing:
            return existing
        config = ExamConfig(
            name="Тестовый экзамен (5 вопросов)",
            adaptive=False,
            num_questions=5,
            unit_ids=None,
        )
        exam = Exam(
            exam_id=TEST_EXAM_ID,
            config=config,
            status="active",
            questions=list(TEST_EXAM_QUESTIONS),
            link=f"/exam/{TEST_EXAM_ID}",
            join_code=TEST_JOIN_CODE,
        )
        self.exams[TEST_EXAM_ID] = exam
        logger.info("get_or_create_test_exam created exam_id=%s join_code=%s questions=5", TEST_EXAM_ID, TEST_JOIN_CODE)
        return exam

    def create_sample_exam(self) -> Exam:
        config = ExamConfig(
            name="Тестовый экзамен (без LLM)",
            adaptive=False,
            num_questions=5,
            unit_ids=None,
        )
        return self.create_exam(config, questions=list(TEST_EXAM_QUESTIONS))
    
    def _generate_adaptive_questions(self, config: ExamConfig) -> List[Dict]:
        questions = []
        unit_ids = config.unit_ids or list(self.knowledge_service.knowledge_base.keys())
        random.shuffle(unit_ids)
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
        random.shuffle(unit_ids)
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
    
    def _resolve_question(self, question_id: str, exam: Optional[Exam]) -> Optional[Dict]:
        if exam and getattr(exam, "questions", None):
            for q in exam.questions:
                if isinstance(q, dict) and q.get("question_id") == question_id:
                    return q
        return self.knowledge_service.find_question_by_id(question_id)

    def evaluate_student_answers(
        self,
        student_id: str,
        answers: List[StudentAnswer],
        exam: Optional[Exam] = None,
    ) -> Dict:
        total_score = 0
        max_score = 0
        evaluations = []
        knowledge_gaps = []
        
        for answer in answers:
            question = self._resolve_question(answer.question_id, exam)
            
            if question:
                evaluation = self._evaluate_single_answer(question, answer.answer)
                evaluations.append(evaluation)
                total_score += evaluation.get("score", 0)
                max_score += sum(c.get("max_score", 1) for c in question.get("criteria", []))
            else:
                evaluations.append({
                    "score": 0,
                    "max_score": 0,
                    "overall_feedback": f"Вопрос не найден: {answer.question_id}",
                    "errors": ["unknown_question"],
                })
                knowledge_gaps.append(answer.question_id)
        
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
        from backend.services.answer_scoring import get_answer_scoring_service

        criteria = question.get("criteria", [])
        max_q = sum(float(c.get("max_score", 0) or 0) for c in criteria) if criteria else 10.0
        try:
            ev = get_answer_scoring_service().compare_and_score(
                question=str(question.get("question", "")),
                reference_answer=str(question.get("reference_answer", "") or ""),
                student_answer=str(answer or ""),
                criteria=criteria if isinstance(criteria, list) else [],
                max_for_question=max_q,
            )
            return {
                "score": ev.get("score", 0),
                "max_score": max_q,
                "criteria_scores": ev.get("criteria_scores", []),
                "overall_feedback": ev.get("overall_feedback", ""),
                "errors": [],
                "strengths": [],
                "improvement_suggestions": [],
            }
        except Exception as e:
            logger.exception("_evaluate_single_answer: %s", e)
            return {
                "score": 0,
                "max_score": max_q,
                "criteria_scores": [],
                "overall_feedback": f"Ошибка при оценке: {str(e)}",
                "errors": [],
                "strengths": [],
                "improvement_suggestions": [],
            }
    
    def get_or_create_student(self, student_id: str, name: str = "", group: str = "") -> StudentProfile:
        if student_id not in self.student_profiles:
            self.student_profiles[student_id] = StudentProfile(
                student_id=student_id,
                name=name,
                group=group
            )
        return self.student_profiles[student_id]

