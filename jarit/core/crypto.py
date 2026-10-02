"""Symmetric encryption for secrets stored at rest (e.g. integration API keys).

The key is provided only via the JARIT_ENCRYPTION_KEY environment variable.
Neither the key nor any plaintext secret may ever be logged or returned.
"""

import binascii
import os
import sys
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

ENV_VAR = "JARIT_ENCRYPTION_KEY"
PREFIX = "enc:v1:"


class EncryptionKeyError(Exception):
    """The encryption key is missing or has an invalid format."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"{ENV_VAR} is {reason}")


class SecretDecryptionError(Exception):
    """A stored secret could not be decrypted with the current key."""


class SecretCipher:
    """Encrypts and decrypts secrets with a single Fernet key."""

    def __init__(self, key: str):
        try:
            self._fernet = Fernet(key)
        except (ValueError, binascii.Error, TypeError):
            raise EncryptionKeyError("invalid") from None

    def encrypt(self, plaintext: str) -> str:
        return PREFIX + self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, stored: str) -> str:
        if not self.is_encrypted(stored):
            raise ValueError("Value is not an encrypted secret")
        try:
            return self._fernet.decrypt(stored[len(PREFIX) :]).decode()
        except InvalidToken:
            raise SecretDecryptionError(
                "Stored secret cannot be decrypted with the current key"
            ) from None

    @staticmethod
    def is_encrypted(stored: str) -> bool:
        return stored.startswith(PREFIX)

    def __repr__(self) -> str:
        return "SecretCipher(<redacted>)"


def load_cipher_from_env() -> SecretCipher:
    key = os.getenv(ENV_VAR, "").strip()
    if not key:
        raise EncryptionKeyError("missing")
    return SecretCipher(key)


@lru_cache(maxsize=1)
def get_cipher() -> SecretCipher:
    return load_cipher_from_env()


def format_startup_failure(reason: str, suggested_key: str) -> str:
    if reason == "invalid":
        cause = f"{ENV_VAR} is invalid (expected a 44-character Fernet key)."
    else:
        cause = f"{ENV_VAR} is missing."
    rule = "=" * 64
    return (
        f"{rule}\n"
        f"JarIt cannot start: {cause}\n"
        "\n"
        "Add this line to your .env file and restart:\n"
        "\n"
        f"{ENV_VAR}={suggested_key}\n"
        "\n"
        "Keep this key safe and back it up. If it is lost or changed, all\n"
        "stored integration credentials (e.g. Mealie API keys) become\n"
        "unreadable and every user has to enter them again.\n"
        f"{rule}\n"
    )


def require_encryption_key() -> None:
    """Abort startup with a helpful message if the key is missing or invalid."""
    try:
        get_cipher()
    except EncryptionKeyError as e:
        suggested_key = Fernet.generate_key().decode()
        sys.stderr.write(format_startup_failure(e.reason, suggested_key))
        sys.stderr.flush()
        sys.exit(1)
