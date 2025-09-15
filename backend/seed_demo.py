# backend/seed_demo.py
import os
from pathlib import Path
from sqlalchemy import create_engine, text

# 让 SQLite 路径始终指向脚本同目录下的 app.db
here = Path(__file__).resolve().parent
default_sqlite = f"sqlite:///{(here / 'app.db').as_posix()}"
DATABASE_URL = os.getenv("DATABASE_URL", default_sqlite)

engine = create_engine(
    DATABASE_URL,
    future=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

def upsert_sql(table: str, columns: list[str], values: list, conflict_col: str):
    cols = ", ".join(columns)
    placeholders = ", ".join([f":{c}" for c in columns])
    if engine.dialect.name == "sqlite":
        sql = f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({placeholders})"
    else:
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) ON CONFLICT ({conflict_col}) DO NOTHING"
    params = {c: v for c, v in zip(columns, values)}
    return sql, params

def main():
    with engine.begin() as conn:
        u_cols = ["id", "email", "hashed_password", "full_name"]
        u_vals = [1, "demo@example.com", "fakehashed123", "Demo User"]
        sql, params = upsert_sql("users", u_cols, u_vals, "email")
        conn.execute(text(sql), params)

        c_cols = [
            "id","owner_id","patient_name","species","sex","age_info",
            "chief_complaint","history","exam_findings",
            "analysis","treatment","prognosis"
        ]
        c_vals = [
            1, 1, "Lucky", "dog", "M", "3y",
            "反复呕吐 2 天", "既往胃炎史", "体检：精神沉郁，T 39.5℃",
            "考虑胃肠炎", "补液 + 止吐药", "预后良好"
        ]
        sql2, params2 = upsert_sql("cases", c_cols, c_vals, "id")
        conn.execute(text(sql2), params2)

    print(f"✅ 已连接 {engine.url} 并插入/保留 demo 数据")

if __name__ == "__main__":
    main()
