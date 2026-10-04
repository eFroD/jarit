"""SC-005: a known secret never shows up in API responses or logs."""

import logging
from unittest.mock import AsyncMock, patch

from cryptography.fernet import Fernet
from sqlalchemy import text

from jarit.core.crypto import SecretCipher

API = "/api/v1"
SENTINEL = "LEAK-SENTINEL-7f3a"


def set_raw(db, value):
    db.execute(text("UPDATE api_keys SET api_key = :v"), {"v": value})
    db.commit()


def test_secret_never_leaks(client, db, caplog):
    caplog.set_level(logging.DEBUG)
    responses = []
    verify = patch(
        "jarit.api.v1.endpoints.integrations.verify_mealie_user",
        new_callable=AsyncMock,
        return_value=True,
    )

    responses.append(
        client.post(
            f"{API}/users/me/api-keys",
            json={
                "service_name": "mealie",
                "api_key": SENTINEL,
                "base_url": "https://m",
            },
        )
    )
    responses.append(client.get(f"{API}/users/me/api-keys"))
    responses.append(client.get(f"{API}/users/me/api-keys/mealie"))
    with verify:
        responses.append(client.get(f"{API}/integrations/verify-mealie-user"))

        # Legacy plaintext row, migrated lazily on access.
        set_raw(db, SENTINEL)
        responses.append(client.get(f"{API}/integrations/verify-mealie-user"))

    # Row encrypted with a different key: unreadable path.
    set_raw(db, SecretCipher(Fernet.generate_key().decode()).encrypt(SENTINEL))
    responses.append(client.get(f"{API}/integrations/verify-mealie-user"))
    responses.append(client.delete(f"{API}/users/me/api-keys/mealie"))

    assert [r.status_code for r in responses] == [201, 200, 200, 200, 200, 409, 204]
    for response in responses:
        assert SENTINEL not in response.text
        assert "enc:v1:" not in response.text
    assert SENTINEL not in caplog.text
    assert "enc:v1:" not in caplog.text
