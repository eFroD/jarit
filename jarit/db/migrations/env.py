"""Alembic environment.

Used both by the CLI (alembic.ini) and by jarit.db.migrate.run_migrations,
which passes an open connection via config.attributes["connection"].
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import jarit.db.models  # noqa: F401  (registers all models on Base.metadata)
from jarit.db.database import Base

config = context.config

# Only the CLI has an ini file; programmatic runs keep the app's logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=os.environ["DATABASE_URL"],
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_with_connection(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        _run_with_connection(connection)
        return

    engine = create_engine(os.environ["DATABASE_URL"], poolclass=pool.NullPool)
    with engine.connect() as connection:
        _run_with_connection(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
