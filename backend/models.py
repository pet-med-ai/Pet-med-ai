# backend/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from .db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cases: Mapped[list["Case"]] = relationship(back_populates="owner", cascade="all, delete")

class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    patient_name: Mapped[str] = mapped_column(String(255), index=True)
    species: Mapped[str] = mapped_column(String(50))   # dog/cat/other
    sex: Mapped[str | None] = mapped_column(String(10))
    age_info: Mapped[str | None] = mapped_column(String(50)) # e.g., "4y", "6m"
    chief_complaint: Mapped[str] = mapped_column(Text)       # 主诉
    history: Mapped[str | None] = mapped_column(Text)        # 既往史/病程
    exam_findings: Mapped[str | None] = mapped_column(Text)  # 体检/化验摘要
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 简易存储分析结果（也可单独表）
    analysis: Mapped[str | None] = mapped_column(Text)
    treatment: Mapped[str | None] = mapped_column(Text)
    prognosis: Mapped[str | None] = mapped_column(Text)

    owner: Mapped["User"] = relationship(back_populates="cases")
