"""The user's language: profile, self-service change and registration."""

import pytest
from fastapi.testclient import TestClient

import main
from jarit.api.v1.endpoints.users import admin_user_required
from jarit.db.models.users import User

ME = "/api/v1/users/me"
REGISTER = "/api/v1/auth/register"


def stored_language(db, user_id: int) -> str:
    db.expire_all()
    return db.get(User, user_id).language


def test_new_user_has_english(client):
    assert client.get(ME).json()["language"] == "en"


def test_change_own_language(client, db, user):
    response = client.patch(ME, json={"language": "de"})

    assert response.status_code == 200
    assert response.json()["language"] == "de"
    assert response.json()["username"] == user.username
    assert stored_language(db, user.id) == "de"
    assert client.get(ME).json()["language"] == "de"


@pytest.mark.parametrize(
    "payload", [{"language": "pt"}, {"language": "german"}, {"language": ""}, {}]
)
def test_unsupported_language_is_rejected(client, db, user, payload):
    client.patch(ME, json={"language": "fr"})

    assert client.patch(ME, json=payload).status_code == 422
    assert stored_language(db, user.id) == "fr"


def test_change_affects_only_the_caller(client, db, other_user):
    client.patch(ME, json={"language": "it"})
    assert stored_language(db, other_user.id) == "en"


def test_admin_user_list_includes_language(client, admin_user):
    main.app.dependency_overrides[admin_user_required] = lambda: admin_user
    users = client.get("/api/v1/admin/users").json()
    assert {u["username"]: u["language"] for u in users}["admin"] == "en"


# --- US3: language at registration ------------------------------------------


@pytest.fixture
def anonymous(user, monkeypatch):
    """A client without a logged-in user; registration is open."""
    monkeypatch.setattr("jarit.auth.service.ALLOW_REGISTRATION", "true")
    main.app.dependency_overrides.clear()
    return TestClient(main.app)


def register(client, name, **extra):
    return client.post(
        REGISTER,
        json={
            "email": f"{name}@example.com",
            "username": name,
            "password": "secret123",
            **extra,
        },
    )


def test_register_with_language(anonymous, db):
    response = register(anonymous, "germanuser", language="de")

    assert response.status_code == 201
    assert response.json()["language"] == "de"
    assert stored_language(db, response.json()["id"]) == "de"


def test_register_defaults_to_english(anonymous, db):
    response = register(anonymous, "plainuser")

    assert response.status_code == 201
    assert stored_language(db, response.json()["id"]) == "en"


def test_register_with_unsupported_language_creates_no_user(anonymous, db):
    assert register(anonymous, "ptuser", language="pt").status_code == 422
    assert db.query(User).filter(User.username == "ptuser").count() == 0
