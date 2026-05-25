# backend/models.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # 删除用户时，级联删除其病例（与你原来保持一致）
    cases: Mapped[List["Case"]] = relationship(
        back_populates="owner",
        cascade="all, delete",
        passive_deletes=True,
    )


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    patient_name: Mapped[str] = mapped_column(String(255), index=True)
    species: Mapped[str] = mapped_column(String(50), default="dog")   # dog/cat/other
    sex: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    age_info: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g., "4y", "6m"
    breed: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    weight: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    coat_color: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    owner_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    owner_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # 主诉/病史/检查
    chief_complaint: Mapped[str] = mapped_column(Text)
    history: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    exam_findings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 结果/计划
    analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    treatment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prognosis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # （可选）附件，与你前端 /api/files 返回的结构兼容：[{id,url,name,type,size}, ...]
    attachments: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True
    )

    # ⭐ 软删除标记（前端“撤销”用）
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    owner: Mapped["User"] = relationship(back_populates="cases")

    # 可选：组合索引，常见查询更快
    __table_args__ = (
        Index("ix_cases_patient_species", "patient_name", "species"),
    )

class ConsultSession(Base):
    """
    动态问诊会话 V1：
    - 保存初始主诉、追问回答数组、最近一次 AI 返回结果。
    - 可绑定 owner_id 做用户隔离，可绑定 case_id 追溯已保存病例。
    - session_uid 给前端持有，避免暴露自增 ID。
    """
    __tablename__ = "consult_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_uid: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    owner_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    case_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    text: Mapped[str] = mapped_column(Text, nullable=False)
    answers: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True
    )

    __table_args__ = (
        Index("ix_consult_sessions_created_at", "created_at"),
    )

