from __future__ import annotations
import os, sys
from logging.config import fileConfig
from alembic import context

# 保证能 import backend 下的 db 和 models
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from db import Base, engine
import models

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
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=_is_sqlite(url),
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine   # ✅ 用项目的 engine，不再用 engine_from_config
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
