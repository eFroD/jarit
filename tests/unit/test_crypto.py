"""Unit tests for secret encryption at rest."""

import pytest
from cryptography.fernet import Fernet

from jarit.core.crypto import (
    PREFIX,
    EncryptionKeyError,
    SecretCipher,
    SecretDecryptionError,
)


@pytest.fixture
def cipher():
    return SecretCipher(Fernet.generate_key().decode())


def test_round_trip(cipher):
    assert cipher.decrypt(cipher.encrypt("my-secret")) == "my-secret"


def test_ciphertext_is_prefixed_and_hides_plaintext(cipher):
    stored = cipher.encrypt("my-secret")
    assert stored.startswith(PREFIX)
    assert "my-secret" not in stored


def test_same_plaintext_encrypts_differently(cipher):
    assert cipher.encrypt("my-secret") != cipher.encrypt("my-secret")


def test_is_encrypted_distinguishes_legacy_plaintext(cipher):
    assert SecretCipher.is_encrypted(cipher.encrypt("x"))
    assert not SecretCipher.is_encrypted("eyJhbGciOiJIUzI1NiJ9.legacy.token")


def test_decrypt_with_other_key_fails(cipher):
    other = SecretCipher(Fernet.generate_key().decode())
    with pytest.raises(SecretDecryptionError):
        other.decrypt(cipher.encrypt("my-secret"))


def test_decrypt_rejects_unprefixed_value(cipher):
    with pytest.raises(ValueError):
        cipher.decrypt("legacy-plain")


def test_invalid_key_error_does_not_echo_value():
    with pytest.raises(EncryptionKeyError) as exc_info:
        SecretCipher("CHANGEME")
    assert exc_info.value.reason == "invalid"
    assert "CHANGEME" not in str(exc_info.value)


def test_repr_contains_no_key_material():
    key = Fernet.generate_key().decode()
    assert key not in repr(SecretCipher(key))
