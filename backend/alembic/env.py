cd ~/Desktop/pet-ai-diagnosis-v1/backend/alembic

# 1) 先备份（可回退）

cp env.py env.py.bak

# 2) 用 here-doc 方式一次性写入最终版 env.py
cat > env.py <<'PY'
from __future__ import annotations
import os, sys
from logging.config import fileConfig
from alembic import context

# 把 backend 加进 sys.path（本文件位于 backend/alembic/）
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from db import Base, engine            # 复用项目的 Engine（不要 engine_from_config）
import models                          # 确保加载 ORM 模型

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# 优先 DATABASE_URL，否则退回 engine.url
db_url = os.getenv("DATABASE_URL") or str(engine.url)
config.set_main_option("sqlalchemy.url", db_url)

def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError("No sqlalchemy.url configured")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=_is_sqlite(url),   # SQLite 需要 batch 模式
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine   # ✅ 关键：直接使用项目 engine
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=_is_sqlite(str(connectable.url)),
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
PY

