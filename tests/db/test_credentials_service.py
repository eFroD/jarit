"""Tests for encrypted storage of integration credentials."""

import re

import pytest
from sqlalchemy import text

from jarit.db.models.api_keys import APIKey
from jarit.integrations import credentials

ENCRYPTED = re.compile(r"^enc:v1:")


def make_entry(db, user, service_name="mealie", plaintext="secret-123"):
    entry = APIKey(user_id=user.id, service_name=service_name, base_url="https://m")
    credentials.set_secret(entry, plaintext)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def raw_value(db, entry_id):
    return db.execute(
        text("SELECT api_key FROM api_keys WHERE id = :id"), {"id": entry_id}
    ).scalar_one()


def insert_raw(db, user, value, service_name="mealie"):
    entry_id = db.execute(
        text(
            "INSERT INTO api_keys (user_id, service_name, api_key, base_url) "
            "VALUES (:u, :s, :v, 'https://m') RETURNING id"
        ),
        {"u": user.id, "s": service_name, "v": value},
    ).scalar_one()
    db.commit()
    return entry_id


# --- US1: encrypted storage -------------------------------------------------


def test_set_secret_stores_only_ciphertext(db, user):
    entry = make_entry(db, user, plaintext="secret-123")
    stored = raw_value(db, entry.id)
    assert ENCRYPTED.match(stored)
    assert "secret-123" not in stored


def test_reveal_secret_returns_plaintext(db, user):
    entry = make_entry(db, user, plaintext="secret-123")
    assert credentials.reveal_secret(db, entry) == "secret-123"


def test_replacing_secret_stores_new_ciphertext(db, user):
    entry = make_entry(db, user, plaintext="old")
    old_stored = raw_value(db, entry.id)
    credentials.set_secret(entry, "new")
    db.commit()
    new_stored = raw_value(db, entry.id)
    assert new_stored != old_stored and ENCRYPTED.match(new_stored)
    assert credentials.reveal_secret(db, entry) == "new"


def test_any_integration_is_encrypted(db, user):
    entry = make_entry(db, user, service_name="other-service", plaintext="xyz")
    assert ENCRYPTED.match(raw_value(db, entry.id))
    assert credentials.reveal_secret(db, entry) == "xyz"


# --- US3: migration of legacy plaintext -------------------------------------


def test_lazy_migration_on_access(db, user):
    entry_id = insert_raw(db, user, "legacy-plain")
    entry = db.get(APIKey, entry_id)
    assert credentials.reveal_secret(db, entry) == "legacy-plain"
    stored = raw_value(db, entry_id)
    assert ENCRYPTED.match(stored)
    assert credentials.reveal_secret(db, db.get(APIKey, entry_id)) == "legacy-plain"


def test_startup_migration_encrypts_all_legacy_rows(db, user):
    legacy_ids = [
        insert_raw(db, user, f"legacy-{i}", service_name=f"svc-{i}") for i in range(3)
    ]
    encrypted = make_entry(db, user, service_name="already", plaintext="done")
    before = raw_value(db, encrypted.id)

    assert credentials.migrate_plaintext_secrets() == (3, 0)

    for i, entry_id in enumerate(legacy_ids):
        db.expire_all()
        assert ENCRYPTED.match(raw_value(db, entry_id))
        assert credentials.reveal_secret(db, db.get(APIKey, entry_id)) == f"legacy-{i}"
    assert raw_value(db, encrypted.id) == before


def test_migration_is_compare_and_set(db, user):
    entry_id = insert_raw(db, user, "legacy-plain")
    assert credentials._migrate_row(db, entry_id, "legacy-plain") is True
    assert credentials._migrate_row(db, entry_id, "legacy-plain") is False
    db.expire_all()
    assert credentials.reveal_secret(db, db.get(APIKey, entry_id)) == "legacy-plain"


def test_startup_migration_isolates_failures(db, user, monkeypatch):
    first = insert_raw(db, user, "legacy-a", service_name="a")
    insert_raw(db, user, "legacy-b", service_name="b")
    real = credentials._migrate_row

    def flaky(session, entry_id, old_value):
        if entry_id == first:
            raise RuntimeError("boom")
        return real(session, entry_id, old_value)

    monkeypatch.setattr(credentials, "_migrate_row", flaky)
    assert credentials.migrate_plaintext_secrets() == (1, 1)
    assert raw_value(db, first) == "legacy-a"


# --- US4: unreadable entries ------------------------------------------------


def test_unreadable_entry_raises_without_secret(db, user, caplog):
    from cryptography.fernet import Fernet

    from jarit.core.crypto import SecretCipher

    foreign = SecretCipher(Fernet.generate_key().decode()).encrypt("lost-secret")
    entry_id = insert_raw(db, user, foreign)
    with pytest.raises(credentials.SecretUnreadableError) as exc_info:
        credentials.reveal_secret(db, db.get(APIKey, entry_id))
    assert exc_info.value.service_name == "mealie"
    assert "lost-secret" not in str(exc_info.value)
    assert foreign not in caplog.text
