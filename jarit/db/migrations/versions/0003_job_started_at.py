"""Start time of the current extraction attempt (reset on retry).

Revision ID: 0003_job_started_at
Revises: 0002_extraction_jobs
Create Date: 2026-10-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_job_started_at"
down_revision: Union[str, Sequence[str], None] = "0002_extraction_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "extraction_jobs",
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    # Existing jobs were never retried with a start time, so their attempt
    # started when they were created.
    op.execute("UPDATE extraction_jobs SET started_at = created_at")
    op.alter_column(
        "extraction_jobs",
        "started_at",
        nullable=False,
        server_default=sa.text("now()"),
    )


def downgrade() -> None:
    op.drop_column("extraction_jobs", "started_at")
