import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Подтягиваем все модели, чтобы alembic видел метаданные
from app.database import Base
import app.models  # noqa: F401

target_metadata = Base.metadata


def get_url() -> str:
    url = os.getenv(
        "DATABASE_URL",
        "postgresql://mkk_user:mkk_password@localhost:5432/mkk",
    )
    # Alembic uses a sync engine, so strip async driver suffix if present
    return url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+aiopg://", "postgresql://"
    )


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
