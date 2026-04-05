"""
Предзаполнение тестовой среды: демо-единицы базы знаний, тестовый экзамен, учётные записи для проверки без LLM.
Включается через SEED_TEST_ENV=true (см. Settings.seed_test_env).
"""
import logging
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from backend.services.knowledge_service import KnowledgeService
    from backend.services.exam_service import ExamService

logger = logging.getLogger("exam_system.test_environment")

from backend.models.didactic_unit import DidacticUnit
from backend.services.exam_service import TEST_JOIN_CODE, TEST_EXAM_ID

# Учётные записи только для dev (пароль одинаковый — см. /api/dev/test-environment)
DEV_USERS_SPEC = [
    ("dev_teacher_1", "teacher@test.local", "Преподаватель (тест)", "teacher", "testtest12"),
    ("dev_student_1", "student@test.local", "Студент (тест)", "student", "testtest12"),
    ("dev_admin_1", "admin@test.local", "Админ (тест)", "admin", "testtest12"),
]


def _demo_units() -> List[DidacticUnit]:
    return [
        DidacticUnit(
            unit_id="unit_demo_python_intro",
            title="Переменные и типы в Python",
            content_type="concept",
            definition="Переменная — имя, связанное с объектом в памяти. Тип можно узнать через type().",
            examples=["x = 10", "name = 'мир'"],
            common_errors=["Путаница изменяемых и неизменяемых типов"],
            questions={
                "understanding": [
                    {
                        "question_id": "unit_demo_python_intro_u1",
                        "question": "Что такое переменная в Python?",
                        "type": "understanding",
                        "difficulty": 0.3,
                        "criteria": [{"name": "Определение", "max_score": 5}],
                        "reference_answer": "Имя, указывающее на объект в памяти.",
                    }
                ],
                "application": [],
                "analysis": [],
            },
        ),
        DidacticUnit(
            unit_id="unit_demo_python_structures",
            title="Списки и кортежи",
            content_type="concept",
            definition="list — изменяемая последовательность в [], tuple — неизменяемая в ().",
            examples=["a = [1, 2]", "b = (1, 2)"],
            common_errors=["Попытка изменить элемент tuple на месте"],
            questions={
                "understanding": [
                    {
                        "question_id": "unit_demo_python_structures_u1",
                        "question": "Чем list отличается от tuple?",
                        "type": "understanding",
                        "difficulty": 0.4,
                        "criteria": [{"name": "Изменяемость", "max_score": 5}],
                        "reference_answer": "list изменяемый, tuple — нет.",
                    }
                ],
                "application": [],
                "analysis": [],
            },
        ),
    ]


def seed_dev_users() -> None:
    from backend.database import SessionLocal
    from backend.models.user_db import User
    from backend.routers.auth import _hash_password

    db = SessionLocal()
    try:
        for uid, email, name, role, pwd in DEV_USERS_SPEC:
            if db.query(User).filter(User.email == email).first():
                continue
            db.add(
                User(
                    id=uid,
                    email=email,
                    password_hash=_hash_password(pwd),
                    name=name,
                    role=role,
                )
            )
            logger.info("seed_dev_users created %s", email)
        db.commit()
    except Exception as e:
        logger.exception("seed_dev_users error: %s", e)
        db.rollback()
    finally:
        db.close()


def seed_test_environment(
    knowledge_service: "KnowledgeService",
    exam_service: "ExamService",
    *,
    seed_users: bool = True,
) -> None:
    """
    Идемпотентно: тестовый экзамен exam_test, демо-единицы в базе знаний, опционально пользователи в БД.
    """
    exam_service.get_or_create_test_exam()

    added = 0
    for unit in _demo_units():
        if unit.unit_id in knowledge_service.knowledge_base:
            continue
        knowledge_service.register_unit_without_embeddings(unit)
        added += 1
    logger.info(
        "seed_test_environment: exam_test OK, knowledge units added=%s total=%s",
        added,
        len(knowledge_service.knowledge_base),
    )

    if seed_users:
        seed_dev_users()


def test_environment_payload(
    knowledge_service: "KnowledgeService",
    exam_service: "ExamService",
) -> dict:
    """JSON для GET /api/dev/test-environment."""
    exam = exam_service.get_exam(TEST_EXAM_ID)
    nq = len(exam.questions) if exam else 0
    return {
        "enabled": True,
        "description": "Предзаполненные данные для проверки экзамена и входа под тестовыми пользователями.",
        "exam": {
            "exam_id": TEST_EXAM_ID,
            "name": exam.config.name if exam else "Тестовый экзамен",
            "join_code": TEST_JOIN_CODE,
            "join_path": f"/join/{TEST_JOIN_CODE}",
            "exam_path": f"/exam/{TEST_EXAM_ID}",
            "questions_count": nq,
        },
        "knowledge_demo_unit_ids": [u.unit_id for u in _demo_units()],
        "knowledge_units_total": len(knowledge_service.knowledge_base),
        "accounts": [
            {"email": e, "password": p, "role": r, "name": n}
            for _, e, n, r, p in DEV_USERS_SPEC
        ],
        "hints": [
            "Студент: войти student@test.local / testtest12 → «Войти по коду» TEST01 или главная → тестовый экзамен.",
            "Преподаватель: teacher@test.local — база знаний, экзамены, аналитика.",
            "Экзамен без LLM на генерацию вопросов: вопросы уже зашиты в exam_test.",
        ],
    }
