# backend/schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

# ===== 用户 =====
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    class Config:
        from_attributes = True

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ===== 病例 =====
class CaseBase(BaseModel):
    patient_name: str
    species: str
    sex: Optional[str] = None
    age_info: Optional[str] = None
    chief_complaint: str
    history: Optional[str] = None
    exam_findings: Optional[str] = None

class CaseCreate(CaseBase):
    pass

class CaseOut(CaseBase):
    id: int
    analysis: Optional[str] = None
    treatment: Optional[str] = None
    prognosis: Optional[str] = None
    class Config:
        from_attributes = True

class AnalyzeIn(BaseModel):
    chief_complaint: str = Field(..., description="主诉/症状")
    history: Optional[str] = None
    exam_findings: Optional[str] = None
    species: Optional[str] = "dog"
    age_info: Optional[str] = None

class AnalyzeOut(BaseModel):
    analysis: str
    treatment: str
    prognosis: str
