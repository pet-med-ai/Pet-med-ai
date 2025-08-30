# backend/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .db import get_session
from . import schemas, crud

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=schemas.UserOut)
def signup(data: schemas.UserCreate, db: Session = Depends(get_session)):
    exists = crud.get_user_by_email(db, data.email)
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = crud.create_user(db, data)
    return user

@router.post("/login", response_model=schemas.TokenOut)
def login(data: schemas.LoginIn, db: Session = Depends(get_session)):
    user = crud.verify_user(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    # 这里简化处理，返回一个伪 token；后续换 JWT：pyjwt + OAuth2PasswordBearer
    return schemas.TokenOut(access_token=f"fake-token-user-{user.id}")
