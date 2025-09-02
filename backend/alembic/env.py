from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# 导入你自己的 Base 和 engine
import sys
import os

# 确保 alembic 能找到 backend 里的文件
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from db import Base  # 假设 db.py 里定义了 Base = declarative_base()
from models import *  # 导入所有模型，确保 Alembic 能发现表

# Alembic 配置对象，可以访问 alembic.ini 里的配置
config = context.config

# 如果 alembic.ini 里配置了 sqlalchemy.url，可以通过这个访问
# 或者你也可以从环境变量里读取 DATABASE_URL 来覆盖
if os.getenv("DATABASE_URL"):
    config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

# 设置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 这里告诉 Alembic 使用我们自己的模型元数据
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """在离线模式下运行迁移（生成 SQL 脚本，而不是连数据库）"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在在线模式下运行迁移（直接连接数据库）"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
