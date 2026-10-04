"""Access to integration secrets (e.g. Mealie API keys) stored encrypted at rest.

All reads and writes of APIKey secrets go through this module, so every
integration gets encryption without its own code. Secrets are decrypted only
when they are about to be sent to the integration. Never log or return them.
"""

import logging

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from jarit.core.crypto import PREFIX, SecretCipher, SecretDecryptionError, get_cipher
from jarit.db.database import SessionLocal
from jarit.db.models.api_keys import APIKey

logger = logging.getLogger(__name__)


class SecretUnreadableError(Exception):
    """A stored secret cannot be decrypted with the current key."""

    def __init__(self, entry_id: int, user_id: int, service_name: str):
        self.entry_id = entry_id
        self.user_id = user_id
        self.service_name = service_name
        super().__init__(
            f"Stored {service_name} credentials of user {user_id} are unreadable"
        )


def set_secret(entry: APIKey, plaintext: str) -> None:
    entry.api_key_ciphertext = get_cipher().encrypt(plaintext)
    entry.updated_at = func.now()


def reveal_secret(db: Session, entry: APIKey) -> str:
    stored = entry.api_key_ciphertext
    if not SecretCipher.is_encrypted(stored):
        # Legacy plaintext from an older installation: use it and encrypt it.
        try:
            _migrate_row(db, entry.id, stored)
        except Exception:
            db.rollback()
            logger.warning(
                "Could not encrypt legacy credential; will retry on next access",
                extra={"entry_id": entry.id, "service_name": entry.service_name},
            )
        return stored

    try:
        return get_cipher().decrypt(stored)
    except SecretDecryptionError:
        logger.warning(
            "Stored credential unreadable with current key",
            extra={
                "entry_id": entry.id,
                "user_id": entry.user_id,
                "service_name": entry.service_name,
            },
        )
        raise SecretUnreadableError(
            entry.id, entry.user_id, entry.service_name
        ) from None


def _migrate_row(db: Session, entry_id: int, old_value: str) -> bool:
    """Encrypt one legacy row, only if it still holds old_value (compare-and-set)."""
    result = db.execute(
        update(APIKey)
        .where(APIKey.id == entry_id, APIKey.api_key_ciphertext == old_value)
        .values(
            api_key_ciphertext=get_cipher().encrypt(old_value),
            updated_at=func.now(),
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return result.rowcount == 1


def migrate_plaintext_secrets() -> tuple[int, int]:
    """Encrypt all remaining legacy plaintext rows. Returns (migrated, failed)."""
    migrated = failed = 0
    with SessionLocal() as db:
        rows = db.execute(
            select(APIKey.id, APIKey.api_key_ciphertext).where(
                APIKey.api_key_ciphertext.not_like(f"{PREFIX}%")
            )
        ).all()
        for entry_id, old_value in rows:
            try:
                if _migrate_row(db, entry_id, old_value):
                    migrated += 1
            except Exception:
                db.rollback()
                failed += 1
    if rows:
        logger.info(
            "Encrypted %d legacy plaintext integration credential(s); "
            "%d failed and will be retried.",
            migrated,
            failed,
        )
    return migrated, failed
