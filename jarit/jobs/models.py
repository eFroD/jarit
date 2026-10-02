"""Job states, failure reasons and the API schemas of extraction jobs."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, HttpUrl

from jarit.languages import Language

from jarit.models.output_models.recipe import RecipeResponse


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    FETCHING_DESCRIPTION = "FETCHING_DESCRIPTION"
    TRANSCRIBING = "TRANSCRIBING"
    EXTRACTING = "EXTRACTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FailureReason(str, Enum):
    VIDEO_UNREACHABLE = "VIDEO_UNREACHABLE"
    NO_RECIPE_FOUND = "NO_RECIPE_FOUND"
    TRANSCRIPTION_FAILED = "TRANSCRIPTION_FAILED"
    LLM_ERROR = "LLM_ERROR"
    TIMEOUT = "TIMEOUT"
    RESTARTED = "RESTARTED"
    UNKNOWN = "UNKNOWN"


ACTIVE_STATUSES = frozenset(
    {JobStatus.FETCHING_DESCRIPTION, JobStatus.TRANSCRIBING, JobStatus.EXTRACTING}
)
NON_TERMINAL_STATUSES = ACTIVE_STATUSES | {JobStatus.QUEUED}
TERMINAL_STATUSES = frozenset({JobStatus.COMPLETED, JobStatus.FAILED})

# Allowed previous statuses per stage. Not strictly forward: the model may read
# the description, start extracting and only then decide it needs the transcript.
STAGE_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.FETCHING_DESCRIPTION: frozenset({JobStatus.QUEUED}),
    JobStatus.TRANSCRIBING: frozenset(
        {JobStatus.FETCHING_DESCRIPTION, JobStatus.EXTRACTING}
    ),
    JobStatus.EXTRACTING: frozenset(
        {JobStatus.FETCHING_DESCRIPTION, JobStatus.TRANSCRIBING}
    ),
}


class ExtractionJobCreate(BaseModel):
    url: HttpUrl
    # None means the submitting user's language.
    target_language: Language | None = None


class ExtractionJobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    video_url: str
    target_language: str
    title: str | None
    status: JobStatus
    failure_reason: FailureReason | None
    created_at: datetime
    started_at: datetime
    updated_at: datetime
    uploaded_to_mealie_at: datetime | None


class ExtractionJobDetail(ExtractionJobSummary):
    result: RecipeResponse | None
