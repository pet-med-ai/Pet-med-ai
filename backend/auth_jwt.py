# backend/auth_jwt.py
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from passlib.hash import bcrypt
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from db import SessionLocal
from sqlalchemy import select, String, Integer, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ------- 配置 -------
SECRET_KEY = "CHANGE_ME_IN_ENV"  # 会被环境变量覆盖
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# ------- DB / Model （最小用户表）-------
class Base(DeclarativeBase): pass  # 仅给 Alembic 识别，不影响你现有 Base

from sqlalchemy import create_engine  # 仅为了避免编辑器告警，实际不使用

# 和你现有的 Base/engine 不冲突：用 run-time 依赖获取 session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# ------- Schemas -------
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    class Config: from_attributes = True

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ------- Utils -------
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.scalar(select(User).where(User.email == email))

def create_user(db: Session, data: UserCreate) -> User:
    user = User(
        email=data.email,
        hashed_password=bcrypt.hash(data.password),
        full_name=data.full_name,
    )
    db.add(user); db.commit(); db.refresh(user)
    return user

def verify_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if user and bcrypt.verify(password, user.hashed_password):
        return user
    return None

def create_access_token(sub: str, minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    to_encode = {"sub": sub, "exp": datetime.utcnow() + timedelta(minutes=minutes)}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email: raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = get_user_by_email(db, email)
    if not user: raise HTTPException(status_code=401, detail="User not found")
    return user

# ------- Router -------
router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=UserOut)
def signup(data: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_email(db, data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return create_user(db, data)

@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = verify_user(db, form.username, form.password)
    if not user: raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token(user.email)
    return TokenOut(access_token=token)
