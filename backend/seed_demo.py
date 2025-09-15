# backend/seed_demo.py
import os
from sqlalchemy import create_engine, text

# 从环境变量或 fallback SQLite 读取数据库 URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

engine = create_engine(DATABASE_URL, future=True)

def seed():
    with engine.begin() as conn:
        # 插入一个用户
        conn.execute(text("""
            INSERT INTO users (id, email, hashed_password, full_name, created_at)
            VALUES (1, 'demo@example.com', 'hashed_demo_pw', 'Demo User', CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO NOTHING
        """))

        # 插入一个病例，关联到用户
        conn.execute(text("""
            INSERT INTO cases (id, owner_id, patient_name, species, sex, age_info,
                               chief_complaint, history, exam_findings,
                               analysis, treatment, prognosis,
                               created_at, updated_at)
            VALUES (1, 1, 'Lucky', 'dog', 'M', '3y',
                    '反复呕吐', '曾经有胃炎史', '体检正常',
                    '怀疑胃肠炎', '对症治疗', '预后良好',
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO NOTHING
        """))

    print("✅ Demo 数据已插入成功")

if __name__ == "__main__":
    seed()
