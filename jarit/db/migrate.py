"""Applies database migrations at startup."""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Engine, inspect

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
BASELINE_REVISION = "0001_baseline"


def _config(connection) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.attributes["connection"] = connection
    return cfg


def run_migrations(engine: Engine) -> None:
    """Bring the schema to the latest revision.

    Databases created by the former Base.metadata.create_all have tables but no
    alembic_version; they are stamped at the baseline before upgrading.
    """
    with engine.begin() as connection:
        cfg = _config(connection)
        tables = inspect(connection).get_table_names()
        if "alembic_version" not in tables and "users" in tables:
            logger.info(
                "Existing database without migration history, stamping baseline"
            )
            command.stamp(cfg, BASELINE_REVISION)

        before = MigrationContext.configure(connection).get_current_revision()
        command.upgrade(cfg, "head")
        after = MigrationContext.configure(connection).get_current_revision()

    if before != after:
        logger.info("Upgraded database schema from %s to %s", before, after)
    logger.info("Database schema at revision %s", after)
