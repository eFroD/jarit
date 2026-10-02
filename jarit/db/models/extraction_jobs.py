import uuid

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from jarit.db.database import Base

STATUS_VALUES = (
    "'QUEUED','FETCHING_DESCRIPTION','TRANSCRIBING','EXTRACTING','COMPLETED','FAILED'"
)
FAILURE_REASON_VALUES = (
    "'VIDEO_UNREACHABLE','NO_RECIPE_FOUND','TRANSCRIPTION_FAILED','LLM_ERROR',"
    "'TIMEOUT','RESTARTED','UNKNOWN'"
)
NON_TERMINAL_VALUES = "'QUEUED','FETCHING_DESCRIPTION','TRANSCRIBING','EXTRACTING'"


class ExtractionJob(Base):
    """A recipe extraction requested by a user; also an entry of their history.

    Change status only through jarit.jobs.repository, which guards every transition.
    """

    __tablename__ = "extraction_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    video_url = Column(Text, nullable=False)
    target_language = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, server_default="QUEUED")
    failure_reason = Column(String(32), nullable=True)
    title = Column(Text, nullable=True)
    result = Column(JSONB, nullable=True)
    uploaded_to_mealie_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        CheckConstraint(
            f"status IN ({STATUS_VALUES})", name="ck_extraction_jobs_status"
        ),
        CheckConstraint(
            f"failure_reason IS NULL OR failure_reason IN ({FAILURE_REASON_VALUES})",
            name="ck_extraction_jobs_failure_reason",
        ),
        CheckConstraint(
            "(status = 'FAILED') = (failure_reason IS NOT NULL)",
            name="ck_extraction_jobs_failure_consistency",
        ),
        Index("ix_extraction_jobs_user_created", "user_id", text("created_at DESC")),
        Index(
            "ix_extraction_jobs_active",
            "status",
            postgresql_where=text(f"status IN ({NON_TERMINAL_VALUES})"),
        ),
    )
