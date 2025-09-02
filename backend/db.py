import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 从环境变量读取数据库 URL，Render 上通常是 DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# 声明基类
Base = declarative_base()

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
