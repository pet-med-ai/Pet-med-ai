# backend/db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1) 读取数据库连接串
# Render: 在环境变量里配置 DATABASE_URL=postgresql://user:pass@host:5432/dbname
# 本地: 不配置则回退到 SQLite 文件 ./app.db
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db").strip()

# 2) 创建 Engine（区分 SQLite / 其他数据库）
is_sqlite = DATABASE_URL.startswith("sqlite")
engine_kwargs = {}

if not is_sqlite:
    # 云端数据库常见连接池参数（可按需调整）
    # - pool_pre_ping: 检查连接是否可用，避免 "server closed the connection unexpectedly"
    # - pool_recycle: 连接回收（秒），防止长期空闲被防火墙/代理断开
    engine_kwargs.update(dict(pool_pre_ping=True, pool_recycle=1800))

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if is_sqlite else {},
    **engine_kwargs,
)

# 3) Session & Base
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 4) FastAPI 依赖，在路由里这样用:
#    db: Session = Depends(get_db)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
