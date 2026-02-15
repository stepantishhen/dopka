from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text

from backend.database import Base


class StudentSessionAnalytics(Base):
    __tablename__ = "student_session_analytics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=False, unique=True)
    exam_id = Column(String, nullable=True, index=True)
    metrics = Column(Text, nullable=True)
    insights = Column(Text, nullable=True)
    total_score = Column(String, nullable=True)
    max_total_score = Column(String, nullable=True)
    questions_answered = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
