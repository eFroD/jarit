"""Migrations on an empty database and on one created by the former create_all."""

import uuid

import pytest
from sqlalchemy import create_engine, inspect, text

from jarit.db.database import DATABASE_URL, Base
from jarit.db.migrate import run_migrations
from jarit.db.models.api_keys import APIKey
from jarit.db.models.users import User


@pytest.fixture
def schema_engine():
    """An engine whose default schema is a throwaway schema, dropped afterwards."""
    schema = f"mig_{uuid.uuid4().hex[:8]}"
    admin = create_engine(DATABASE_URL)
    with admin.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA {schema}"))
    engine = create_engine(
        DATABASE_URL, connect_args={"options": f"-csearch_path={schema}"}
    )
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        admin.dispose()


def revision(engine) -> str:
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()


def test_empty_database_is_migrated_to_head(schema_engine):
    run_migrations(schema_engine)

    tables = set(inspect(schema_engine).get_table_names())
    assert {"users", "api_keys", "extraction_jobs", "alembic_version"} <= tables
    assert revision(schema_engine) == "0002_extraction_jobs"


def test_legacy_create_all_database_keeps_its_data(schema_engine, caplog):
    Base.metadata.create_all(schema_engine, tables=[User.__table__, APIKey.__table__])
    with schema_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (email, username, hashed_password, role, is_active) "
                "VALUES ('a@example.com', 'alice', 'x', 'USER', true)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO api_keys (user_id, service_name, api_key, base_url) "
                "VALUES (1, 'mealie', 'enc:v1:abc', 'https://m')"
            )
        )

    caplog.set_level("INFO")
    run_migrations(schema_engine)

    assert "stamping baseline" in caplog.text
    assert revision(schema_engine) == "0002_extraction_jobs"
    with schema_engine.connect() as conn:
        assert conn.execute(text("SELECT username FROM users")).scalar_one() == "alice"
        assert (
            conn.execute(text("SELECT api_key FROM api_keys")).scalar_one()
            == "enc:v1:abc"
        )
        assert (
            conn.execute(text("SELECT count(*) FROM extraction_jobs")).scalar_one() == 0
        )


def test_second_run_is_a_no_op(schema_engine):
    run_migrations(schema_engine)
    run_migrations(schema_engine)
    assert revision(schema_engine) == "0002_extraction_jobs"


def test_downgrade_to_base_and_back(schema_engine):
    from alembic import command

    from jarit.db.migrate import _config

    run_migrations(schema_engine)
    with schema_engine.begin() as conn:
        command.downgrade(_config(conn), "base")
    assert set(inspect(schema_engine).get_table_names()) == {"alembic_version"}

    run_migrations(schema_engine)
    assert revision(schema_engine) == "0002_extraction_jobs"
