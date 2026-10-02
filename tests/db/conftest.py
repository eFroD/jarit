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
from jarit.api.v1.endpoints.users import get_current_user  # noqa: E402
from jarit.db.database import Base, SessionLocal, engine  # noqa: E402
from jarit.db.models.users import User, UserRole  # noqa: E402


def truncate_tables(session):
    session.execute(text("TRUNCATE users, api_keys RESTART IDENTITY CASCADE"))
    session.commit()


@pytest.fixture(scope="session", autouse=True)
def schema():
    Base.metadata.create_all(bind=engine)
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


@pytest.fixture
def user(db):
    u = User(
        email="tester@example.com",
        username="tester",
        hashed_password="not-used",
        role=UserRole.USER,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def client(user):
    main.app.dependency_overrides[get_current_user] = lambda: user
    try:
        yield TestClient(main.app)
    finally:
        main.app.dependency_overrides.clear()
