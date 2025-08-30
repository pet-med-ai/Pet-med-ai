# backend/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import select
from . import models, schemas
from passlib.hash import bcrypt

# ===== 用户 =====
def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.scalar(select(models.User).where(models.User.email == email))

def create_user(db: Session, data: schemas.UserCreate) -> models.User:
    user = models.User(
        email=data.email,
        hashed_password=bcrypt.hash(data.password),
        full_name=data.full_name or "",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def verify_user(db: Session, email: str, password: str) -> models.User | None:
    user = get_user_by_email(db, email)
    if user and bcrypt.verify(password, user.hashed_password):
        return user
    return None

# ===== 病例 =====
def create_case(db: Session, owner_id: int, data: schemas.CaseCreate) -> models.Case:
    case = models.Case(owner_id=owner_id, **data.model_dict())
    db.add(case)
    db.commit()
    db.refresh(case)
    return case

def list_cases(db: Session, owner_id: int, limit=50, offset=0):
    stmt = select(models.Case).where(models.Case.owner_id == owner_id).order_by(models.Case.id.desc()).limit(limit).offset(offset)
    return db.scalars(stmt).all()

def get_case(db: Session, case_id: int, owner_id: int) -> models.Case | None:
    stmt = select(models.Case).where(models.Case.id == case_id, models.Case.owner_id == owner_id)
    return db.scalar(stmt)

def save_analysis(db: Session, case_obj: models.Case, analysis: str, treatment: str, prognosis: str) -> models.Case:
    case_obj.analysis = analysis
    case_obj.treatment = treatment
    case_obj.prognosis = prognosis
    db.add(case_obj)
    db.commit()
    db.refresh(case_obj)
    return case_obj
