"""Language per user; job target languages become language codes.

Revision ID: 0004_user_language
Revises: 0003_job_started_at
Create Date: 2026-10-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_user_language"
down_revision: Union[str, Sequence[str], None] = "0003_job_started_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Spelled out on purpose: a migration must not change when jarit.languages changes.
LANGUAGE_VALUES = "'en','de','es','fr','it'"
LEGACY_NAMES = {
    "english": "en",
    "german": "de",
    "spanish": "es",
    "french": "fr",
    "italian": "it",
}


def _rewrite_job_languages(mapping: dict[str, str], column: str) -> None:
    cases = " ".join(f"WHEN '{old}' THEN '{new}'" for old, new in mapping.items())
    op.execute(
        "UPDATE extraction_jobs SET target_language = "
        f"CASE {column} {cases} ELSE target_language END"
    )


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("language", sa.String(8), nullable=False, server_default="en"),
    )
    op.create_check_constraint(
        "ck_users_language", "users", f"language IN ({LANGUAGE_VALUES})"
    )
    _rewrite_job_languages(LEGACY_NAMES, "lower(target_language)")


def downgrade() -> None:
    _rewrite_job_languages(
        {code: name for name, code in LEGACY_NAMES.items()}, "target_language"
    )
    op.drop_constraint("ck_users_language", "users", type_="check")
    op.drop_column("users", "language")
