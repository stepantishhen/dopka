import json
import logging
from typing import Dict, Any, List, Optional

from backend.database import SessionLocal
from backend.models.student_analytics_db import StudentSessionAnalytics
from backend.models.user_db import User

logger = logging.getLogger("exam_system.student_analytics")


def _parse_json(text: Optional[str], default=None):
    if default is None:
        default = [] if "[" in str(type(text)) else {}
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


def append_metric(
    session_id: str,
    student_id: str,
    exam_id: Optional[str],
    metric: Dict[str, Any],
    total_score: Optional[float] = None,
    max_total_score: Optional[float] = None,
    questions_answered: Optional[int] = None,
) -> None:
    db = SessionLocal()
    try:
        row = db.query(StudentSessionAnalytics).filter(
            StudentSessionAnalytics.session_id == session_id
        ).first()
        metrics = _parse_json(row.metrics if row else None, [])
        metrics.append(metric)
        if row:
            row.metrics = json.dumps(metrics, ensure_ascii=False)
            if total_score is not None:
                row.total_score = str(total_score)
            if max_total_score is not None:
                row.max_total_score = str(max_total_score)
            if questions_answered is not None:
                row.questions_answered = questions_answered
            row.updated_at = __import__("datetime").datetime.utcnow()
        else:
            row = StudentSessionAnalytics(
                student_id=student_id,
                session_id=session_id,
                exam_id=exam_id,
                metrics=json.dumps(metrics, ensure_ascii=False),
                total_score=str(total_score) if total_score is not None else None,
                max_total_score=str(max_total_score) if max_total_score is not None else None,
                questions_answered=questions_answered or 0,
            )
            db.add(row)
        db.commit()
    except Exception as e:
        logger.exception("append_metric error: %s", e)
        db.rollback()
    finally:
        db.close()


def save_insights(
    session_id: str,
    student_id: str,
    insights: Dict[str, Any],
) -> None:
    db = SessionLocal()
    try:
        row = db.query(StudentSessionAnalytics).filter(
            StudentSessionAnalytics.session_id == session_id
        ).first()
        if row:
            row.insights = json.dumps(insights, ensure_ascii=False)
            row.updated_at = __import__("datetime").datetime.utcnow()
        else:
            row = StudentSessionAnalytics(
                student_id=student_id,
                session_id=session_id,
                insights=json.dumps(insights, ensure_ascii=False),
            )
            db.add(row)
        db.commit()
    except Exception as e:
        logger.exception("save_insights error: %s", e)
        db.rollback()
    finally:
        db.close()


def get_by_student_id(student_id: str) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        rows = (
            db.query(StudentSessionAnalytics)
            .filter(StudentSessionAnalytics.student_id == student_id)
            .order_by(StudentSessionAnalytics.updated_at.desc())
            .all()
        )
        out = []
        for r in rows:
            out.append({
                "session_id": r.session_id,
                "exam_id": r.exam_id,
                "metrics": _parse_json(r.metrics, []),
                "insights": _parse_json(r.insights, {}),
                "total_score": float(r.total_score) if r.total_score else None,
                "max_total_score": float(r.max_total_score) if r.max_total_score else None,
                "questions_answered": r.questions_answered or 0,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            })
        return out
    finally:
        db.close()


def get_by_session_id(session_id: str) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        row = db.query(StudentSessionAnalytics).filter(
            StudentSessionAnalytics.session_id == session_id
        ).first()
        if not row:
            return None
        return {
            "student_id": row.student_id,
            "session_id": row.session_id,
            "exam_id": row.exam_id,
            "metrics": _parse_json(row.metrics, []),
            "insights": _parse_json(row.insights, {}),
            "total_score": float(row.total_score) if row.total_score else None,
            "max_total_score": float(row.max_total_score) if row.max_total_score else None,
            "questions_answered": row.questions_answered or 0,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
    finally:
        db.close()


def list_students_with_analytics() -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        rows = (
            db.query(StudentSessionAnalytics)
            .order_by(StudentSessionAnalytics.student_id, StudentSessionAnalytics.updated_at.desc())
            .all()
        )
        by_student: Dict[str, StudentSessionAnalytics] = {}
        for r in rows:
            if r.student_id not in by_student:
                by_student[r.student_id] = r
        student_ids = list(by_student.keys())
        users = db.query(User).filter(User.id.in_(student_ids)).all() if student_ids else []
        user_map = {u.id: {"name": u.name, "email": u.email} for u in users}
        out = []
        for sid, r in by_student.items():
            out.append({
                "student_id": sid,
                "name": user_map.get(sid, {}).get("name", sid),
                "email": user_map.get(sid, {}).get("email", ""),
                "last_session_id": r.session_id,
                "last_exam_id": r.exam_id,
                "last_total_score": float(r.total_score) if r.total_score else None,
                "last_max_total_score": float(r.max_total_score) if r.max_total_score else None,
                "last_questions_answered": r.questions_answered or 0,
                "last_updated_at": r.updated_at.isoformat() if r.updated_at else None,
            })
        return sorted(out, key=lambda x: (x["last_updated_at"] or ""), reverse=True)
    finally:
        db.close()
