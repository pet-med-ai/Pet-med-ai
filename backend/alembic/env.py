# backend/alembic/env.py
from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context

# 让 alembic 能 import 到 backend 下的模块（env.py 位于 backend/alembic/）
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from db import Base, engine  # 你项目里的 SQLAlchemy Base 和 Engine
import models  # 确保加载所有 ORM 模型（非常关键）

# 读取 alembic.ini 的配置对象
config = context.config

# 如果设置了日志配置文件，加载之（可选）
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 交给 Alembic 的元数据（自动生成迁移时使用）
target_metadata = Base.metadata

# 统一决定 URL：优先用环境变量 DATABASE_URL，否则用项目 engine.url
db_url = os.getenv("DATABASE_URL")
if not db_url:
    try:
        db_url = str(engine.url)
    except Exception:
        db_url = None

if db_url:
    config.set_main_option("sqlalchemy.url", db_url)


def _is_sqlite_url(url: str | None) -> bool:
    return bool(url) and url.startswith("sqlite")


def run_migrations_offline() -> None:
    """离线模式：不连库，直接输出 SQL。"""
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError(
            "No sqlalchemy.url configured for offline migrations. "
            "Set DATABASE_URL or ensure db.engine.url is available."
        )

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=_is_sqlite_url(url),  # SQLite 需要 batch 模式
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：直接连接数据库并执行迁移。"""
    # 复用应用的 engine，保持与运行时一致的参数/连接池
    connectable = engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=_is_sqlite_url(str(connectable.url)),
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
