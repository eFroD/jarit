"""Endpoint tests for storing and using integration credentials."""

import logging
from unittest.mock import AsyncMock, patch

from cryptography.fernet import Fernet
from sqlalchemy import text

from jarit.core.crypto import SecretCipher
from jarit.jobs import repository
from tests.factories import make_response

API = "/api/v1"
MEALIE = {"service_name": "mealie", "api_key": "plain-key-123", "base_url": "https://m"}


def completed_job(db, user):
    job = repository.create_job(db, user.id, "https://example.com/v", "english")
    repository.start_job(db, job.id)
    repository.complete_job(db, job.id, make_response())
    return job


def stored_value(db):
    return db.execute(text("SELECT api_key FROM api_keys")).scalar_one()


def store_foreign_ciphertext(db, user, secret="lost-key"):
    value = SecretCipher(Fernet.generate_key().decode()).encrypt(secret)
    db.execute(
        text(
            "INSERT INTO api_keys (user_id, service_name, api_key, base_url) "
            "VALUES (:u, 'mealie', :v, 'https://m')"
        ),
        {"u": user.id, "v": value},
    )
    db.commit()
    return value


# --- US1 --------------------------------------------------------------------


def test_post_stores_ciphertext(client, db):
    assert client.post(f"{API}/users/me/api-keys", json=MEALIE).status_code == 201
    stored = stored_value(db)
    assert stored.startswith("enc:v1:")
    assert "plain-key-123" not in stored


def test_get_endpoints_never_return_secret(client, db):
    client.post(f"{API}/users/me/api-keys", json=MEALIE)
    stored = stored_value(db)
    for path in ("/users/me/api-keys", "/users/me/api-keys/mealie"):
        response = client.get(f"{API}{path}")
        assert response.status_code == 200
        assert "plain-key-123" not in response.text
        assert stored not in response.text
        assert "api_key" not in response.text


def test_blank_secret_is_rejected(client, db):
    response = client.post(
        f"{API}/users/me/api-keys", json={**MEALIE, "api_key": "   "}
    )
    assert response.status_code == 422
    assert db.execute(text("SELECT count(*) FROM api_keys")).scalar_one() == 0


def test_integration_receives_decrypted_secret(client):
    client.post(f"{API}/users/me/api-keys", json=MEALIE)
    with patch(
        "jarit.api.v1.endpoints.integrations.verify_mealie_user",
        new_callable=AsyncMock,
        return_value=True,
    ) as verify:
        response = client.get(f"{API}/integrations/verify-mealie-user")
    assert response.status_code == 200
    verify.assert_awaited_once_with("https://m", "plain-key-123")


# --- US4 --------------------------------------------------------------------


def test_unreadable_secret_returns_409_and_app_keeps_working(client, db, user, caplog):
    foreign = store_foreign_ciphertext(db, user)
    caplog.set_level(logging.WARNING)

    job = completed_job(db, user)
    upload = client.post(f"{API}/extraction-jobs/{job.id}/upload-mealie")
    assert upload.status_code == 409
    assert "enter your Mealie API key again" in upload.json()["detail"]
    assert "enc:v1:" not in upload.text

    assert client.get(f"{API}/integrations/verify-mealie-user").status_code == 409
    assert client.get(f"{API}/users/me/api-keys").status_code == 200

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 2  # one per failed access
    assert all(r.service_name == "mealie" and r.user_id == user.id for r in warnings)
    assert foreign not in caplog.text


def test_unreadable_secret_can_be_replaced(client, db, user):
    store_foreign_ciphertext(db, user)
    assert client.post(f"{API}/users/me/api-keys", json=MEALIE).status_code == 201
    with patch(
        "jarit.api.v1.endpoints.integrations.verify_mealie_user",
        new_callable=AsyncMock,
        return_value=True,
    ):
        assert client.get(f"{API}/integrations/verify-mealie-user").status_code == 200


def test_unreadable_secret_can_be_deleted(client, db, user):
    store_foreign_ciphertext(db, user)
    assert client.delete(f"{API}/users/me/api-keys/mealie").status_code == 204
