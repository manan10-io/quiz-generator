"""
alembic/env.py — Migration environment configuration.

Uses the app's own async SQLAlchemy engine and settings rather than
duplicating the DATABASE_URL in alembic.ini, so migrations always target
whatever database the app itself is configured to use (dev SQLite, or
production PostgreSQL via DATABASE_URL env var).
"""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import the app's models so Base.metadata knows about every table.
# Without this import, autogenerate would see an empty metadata object
# and produce empty migrations.
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import Base
from app.config import settings
from app.models import models  # noqa: F401 — registers all ORM tables

config = context.config

# Override the URL from alembic.ini with the app's actual configured DB URL
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Generate SQL scripts without a live DB connection ('alembic upgrade --sql').
    Useful for review before applying migrations to production.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Runs migrations using the app's async engine configuration."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
