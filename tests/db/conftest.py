"""Fixtures for tests that need a real PostgreSQL database (DATABASE_URL).

tests/conftest.py ignores this directory when no PostgreSQL URL is set.
"""

import os

import pytest

# Dummy settings so the app can be imported; no real provider is ever called.
os.environ.setdefault("LLM_PROVIDER", "google")
os.environ.setdefault("MODEL_NAME", "gemini-2.5-flash")
os.environ.setdefault("GOOGLE_API_KEY", "test-dummy")
os.environ.setdefault("OPENAI_API_KEY", "test-dummy")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

import main  # noqa: E402
from jarit.api.v1.endpoints.extraction_jobs import get_runner  # noqa: E402
from jarit.api.v1.endpoints.users import get_current_user  # noqa: E402
from jarit.db.database import SessionLocal, engine  # noqa: E402
from jarit.db.migrate import run_migrations  # noqa: E402
from jarit.db.models.users import User, UserRole  # noqa: E402


def truncate_tables(session):
    session.execute(
        text("TRUNCATE users, api_keys, extraction_jobs RESTART IDENTITY CASCADE")
    )
    session.commit()


@pytest.fixture(scope="session", autouse=True)
def schema():
    run_migrations(engine)
    with SessionLocal() as session:
        truncate_tables(session)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        truncate_tables(session)
        session.close()


def make_user(db, name, role=UserRole.USER):
    u = User(
        email=f"{name}@example.com",
        username=name,
        hashed_password="not-used",
        role=role,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def user(db):
    return make_user(db, "tester")


@pytest.fixture
def other_user(db):
    return make_user(db, "other")


@pytest.fixture
def admin_user(db):
    return make_user(db, "admin", UserRole.ADMIN)


class FakeRunner:
    """Records submitted job ids instead of running extractions."""

    def __init__(self):
        self.submitted = []

    def submit(self, job_id):
        self.submitted.append(job_id)


@pytest.fixture
def fake_runner():
    return FakeRunner()


@pytest.fixture
def act_as():
    """Switch the authenticated user of the test client."""

    def switch(u):
        main.app.dependency_overrides[get_current_user] = lambda: u

    return switch


@pytest.fixture
def client(user, fake_runner, act_as):
    act_as(user)
    main.app.dependency_overrides[get_runner] = lambda: fake_runner
    try:
        yield TestClient(main.app)
    finally:
        main.app.dependency_overrides.clear()
