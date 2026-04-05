import csv
import io
import logging
import secrets
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.user_db import User
from backend.repositories import student_analytics as student_analytics_repo
from backend.routers.auth import _hash_password, require_staff

logger = logging.getLogger("exam_system.teacher")
router = APIRouter()


@router.get("/students")
async def list_students_with_analytics(
    _: User = Depends(require_staff),
):
    try:
        students = student_analytics_repo.list_students_with_analytics()
        return {"students": students}
    except Exception as e:
        logger.exception("list_students_with_analytics error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/students/{student_id}/analytics")
async def get_student_analytics(
    student_id: str,
    _: User = Depends(require_staff),
):
    try:
        sessions = student_analytics_repo.get_by_student_id(student_id)
        return {"student_id": student_id, "sessions": sessions}
    except Exception as e:
        logger.exception("get_student_analytics error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/sessions")
async def monitoring_active_sessions(
    request: Request,
    _: User = Depends(require_staff),
):
    orchestrator = request.app.state.orchestrator
    return {"sessions": orchestrator.list_active_sessions()}


@router.get("/analytics/by-exam")
async def analytics_by_exam(
    _: User = Depends(require_staff),
):
    """Сводка по экзаменам: сколько прохождений, средний результат, учёт ссылок на практику в ответах."""
    try:
        rows = student_analytics_repo.summarize_by_exam()
        return {"exams": rows}
    except Exception as e:
        logger.exception("analytics_by_exam error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/analytics")
async def export_analytics(
    fmt: str = Query("json", alias="format", description="json или csv"),
    _: User = Depends(require_staff),
):
    rows = student_analytics_repo.list_all_sessions()
    if fmt.lower() == "csv":
        fn = [
            "student_id",
            "session_id",
            "exam_id",
            "total_score",
            "max_total_score",
            "questions_answered",
            "updated_at",
        ]
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=fn, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fn})
        return StreamingResponse(
            iter([out.getvalue()]),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="analytics_{datetime.utcnow().strftime("%Y%m%d_%H%M")}.csv"'
            },
        )

    return {"exported_at": datetime.utcnow().isoformat(), "sessions": rows, "count": len(rows)}


@router.post("/students/import")
async def import_students_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """
    CSV: колонки email, name; опционально group.
    Для новых пользователей в ответе один раз возвращается сгенерированный пароль.
    """
    try:
        raw = await file.read()
        text = raw.decode("utf-8-sig")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Не удалось прочитать файл: {e}")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="Пустой CSV")
    lower_cols = {f.lower(): f for f in reader.fieldnames if f}
    if "email" not in lower_cols:
        raise HTTPException(status_code=400, detail="CSV должен содержать колонку email")

    created: List[dict] = []
    skipped: List[dict] = []

    for row in reader:
        rl = {(k or "").lower(): (v or "").strip() for k, v in row.items()}
        email = rl.get("email", "").lower()
        name = rl.get("name", "") or (email.split("@")[0] if email else "")
        group = rl.get("group", "")

        if not email or "@" not in email:
            skipped.append({"email": email, "reason": "invalid_email"})
            continue

        existing = db.query(User).filter(User.email == email).first()
        if existing:
            skipped.append({"email": email, "reason": "already_exists"})
            continue

        password_plain = secrets.token_urlsafe(10)
        uid = f"user_{datetime.utcnow().timestamp()}_{secrets.token_hex(3)}"
        user = User(
            id=uid,
            email=email,
            password_hash=_hash_password(password_plain),
            name=name,
            role="student",
        )
        db.add(user)
        created.append(
            {
                "id": uid,
                "email": email,
                "name": name,
                "group": group or None,
                "temporary_password": password_plain,
            }
        )

    db.commit()
    logger.info("import_students_csv created=%s skipped=%s", len(created), len(skipped))
    return {
        "created": created,
        "skipped": skipped,
        "warning": "Сохраните выданные пароли: повторно они не отображаются.",
    }
