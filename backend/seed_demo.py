# backend/seed_demo.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from models import User, Case  # 确保 models.py 里有 User 和 Case 类
from db import Base

# 读取 DATABASE_URL，默认为 SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def main():
    db = SessionLocal()

    # 插入一个 demo 用户
    demo_user = User(
        email="demo@example.com",
        hashed_password="fakehashed123",
        full_name="Demo Doctor",
        created_at=datetime.utcnow(),
    )
    db.add(demo_user)
    db.commit()
    db.refresh(demo_user)

    print(f"✅ 插入用户 id={demo_user.id}, email={demo_user.email}")

    # 插入一个 demo 病例
    demo_case = Case(
        owner_id=demo_user.id,
        patient_name="Lucky",
        species="dog",
        sex="M",
        age_info="4y",
        chief_complaint="呕吐 2 天",
        history="主人说昨天开始不吃饭",
        exam_findings="体温 39.5℃, 精神沉郁",
        analysis="怀疑胃肠炎",
        treatment="输液 + 止吐药",
        prognosis="预后良好",
        attachments=[{"file": "xray.jpg", "note": "胸片"}],
        created_at=datetime.utcnow(),
    )
    db.add(demo_case)
    db.commit()
    db.refresh(demo_case)

    print(f"✅ 插入病例 id={demo_case.id}, patient={demo_case.patient_name}")

    db.close()


if __name__ == "__main__":
    main()
