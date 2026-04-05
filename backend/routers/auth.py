import logging
from datetime import datetime, timedelta
from typing import Optional, Generator
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models.user_db import User

logger = logging.getLogger("exam_system.auth")
router = APIRouter()
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Недействительный токен")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Недействительный токен")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user


def require_teacher(user: User = Depends(get_current_user)) -> User:
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Доступ только для преподавателей")
    return user


def require_staff(user: User = Depends(get_current_user)) -> User:
    """Преподаватель или администратор."""
    if user.role not in ("teacher", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Доступ только для преподавателей и администраторов",
        )
    return user

BCRYPT_MAX_PASSWORD_BYTES = 72


def _password_bytes(password: str) -> bytes:
    b = password.encode("utf-8")
    return b[:BCRYPT_MAX_PASSWORD_BYTES] if len(b) > BCRYPT_MAX_PASSWORD_BYTES else b


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(_password_bytes(password), password_hash.encode("utf-8"))


class UserRegister(BaseModel):
    email: str
    password: str
    name: str
    role: str = "student"


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=7))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")


def verify_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError:
        return None


def _user_to_dict(u: User) -> dict:
    return {"id": u.id, "email": u.email, "name": u.name, "role": u.role}


@router.post("/register", response_model=TokenResponse)
async def register(data: UserRegister, db: Session = Depends(get_db)):
    logger.info("register attempt email=%s role=%s", data.email, data.role)
    if data.role not in ("student", "teacher", "admin"):
        logger.warning("register rejected: invalid role=%s", data.role)
        raise HTTPException(status_code=400, detail="Роль должна быть student, teacher или admin")
    if db.query(User).filter(User.email == data.email).first():
        logger.warning("register rejected: email already exists email=%s", data.email)
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

    user = User(
        id=f"user_{datetime.utcnow().timestamp()}",
        email=data.email,
        password_hash=_hash_password(data.password),
        name=data.name,
        role=data.role,
    )
    db.add(user)
    db.flush()
    logger.info("register success user_id=%s email=%s", user.id, user.email)

    token_data = {"sub": user.id, "email": user.email, "role": user.role}
    access_token = create_access_token(token_data)
    return TokenResponse(access_token=access_token, user=_user_to_dict(user))


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: Session = Depends(get_db)):
    logger.info("login attempt email=%s", data.email)
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        logger.warning("login failed: user not found email=%s", data.email)
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    if not _verify_password(data.password, user.password_hash):
        logger.warning("login failed: invalid password email=%s", data.email)
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    logger.info("login success user_id=%s email=%s", user.id, user.email)
    token_data = {"sub": user.id, "email": user.email, "role": user.role}
    access_token = create_access_token(token_data)
    return TokenResponse(access_token=access_token, user=_user_to_dict(user))
