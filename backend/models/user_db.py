from datetime import datetime
from sqlalchemy import Column, String, DateTime

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="student")
    created_at = Column(DateTime, default=datetime.utcnow)
