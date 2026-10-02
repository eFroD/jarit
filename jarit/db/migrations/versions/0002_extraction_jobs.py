"""Extraction jobs (asynchronous extraction and per-user history).

Revision ID: 0002_extraction_jobs
Revises: 0001_baseline
Create Date: 2026-10-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_extraction_jobs"
down_revision: Union[str, Sequence[str], None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Values are spelled out here on purpose: a migration must not change when the
# application enums change later.
STATUS_VALUES = (
    "'QUEUED','FETCHING_DESCRIPTION','TRANSCRIBING','EXTRACTING','COMPLETED','FAILED'"
)
FAILURE_REASON_VALUES = (
    "'VIDEO_UNREACHABLE','NO_RECIPE_FOUND','TRANSCRIPTION_FAILED','LLM_ERROR',"
    "'TIMEOUT','RESTARTED','UNKNOWN'"
)
NON_TERMINAL_VALUES = "'QUEUED','FETCHING_DESCRIPTION','TRANSCRIBING','EXTRACTING'"


def upgrade() -> None:
    op.create_table(
        "extraction_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("video_url", sa.Text(), nullable=False),
        sa.Column("target_language", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), server_default="QUEUED", nullable=False),
        sa.Column("failure_reason", sa.String(32), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("uploaded_to_mealie_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"status IN ({STATUS_VALUES})", name="ck_extraction_jobs_status"
        ),
        sa.CheckConstraint(
            f"failure_reason IS NULL OR failure_reason IN ({FAILURE_REASON_VALUES})",
            name="ck_extraction_jobs_failure_reason",
        ),
        sa.CheckConstraint(
            "(status = 'FAILED') = (failure_reason IS NOT NULL)",
            name="ck_extraction_jobs_failure_consistency",
        ),
    )
    op.create_index(
        "ix_extraction_jobs_user_created",
        "extraction_jobs",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_extraction_jobs_active",
        "extraction_jobs",
        ["status"],
        postgresql_where=sa.text(f"status IN ({NON_TERMINAL_VALUES})"),
    )


def downgrade() -> None:
    op.drop_index("ix_extraction_jobs_active", table_name="extraction_jobs")
    op.drop_index("ix_extraction_jobs_user_created", table_name="extraction_jobs")
    op.drop_table("extraction_jobs")
