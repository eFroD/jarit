"""Database access for extraction jobs.

Every status change is a conditional UPDATE that only applies if the job is still
in an expected state. That makes double clicks, several tabs and the background
worker racing a delete safe without locks. Functions return False when the guard
did not match (job gone, foreign or in the wrong state).
"""

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from jarit.db.models.extraction_jobs import ExtractionJob
from jarit.jobs.models import (
    ACTIVE_STATUSES,
    NON_TERMINAL_STATUSES,
    STAGE_TRANSITIONS,
    TERMINAL_STATUSES,
    FailureReason,
    JobStatus,
)
from jarit.models.output_models.recipe import Recipe, RecipeResponse


def _values(statuses: Iterable[JobStatus]) -> list[str]:
    return [s.value for s in statuses]


def create_job(
    db: Session, user_id: int, video_url: str, target_language: str
) -> ExtractionJob:
    job = ExtractionJob(
        user_id=user_id,
        video_url=video_url,
        target_language=target_language,
        status=JobStatus.QUEUED.value,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: UUID) -> ExtractionJob | None:
    return db.get(ExtractionJob, job_id)


def get_owned_job(db: Session, user_id: int, job_id: UUID) -> ExtractionJob | None:
    """Return the job only if it belongs to the user; foreign jobs look missing."""
    return db.scalar(
        select(ExtractionJob).where(
            ExtractionJob.id == job_id, ExtractionJob.user_id == user_id
        )
    )


def list_owned_jobs(db: Session, user_id: int) -> list[ExtractionJob]:
    return list(
        db.scalars(
            select(ExtractionJob)
            .where(ExtractionJob.user_id == user_id)
            .order_by(ExtractionJob.created_at.desc(), ExtractionJob.id)
        )
    )


def _transition(
    db: Session, job_id: UUID, from_statuses: Iterable[JobStatus], **values
) -> bool:
    result = db.execute(
        update(ExtractionJob)
        .where(
            ExtractionJob.id == job_id,
            ExtractionJob.status.in_(_values(from_statuses)),
        )
        .values(updated_at=func.now(), **values)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return result.rowcount == 1


def start_job(db: Session, job_id: UUID) -> bool:
    return _transition(
        db,
        job_id,
        [JobStatus.QUEUED],
        status=JobStatus.FETCHING_DESCRIPTION.value,
    )


def advance_stage(db: Session, job_id: UUID, stage: JobStatus) -> bool:
    allowed = STAGE_TRANSITIONS.get(stage)
    if not allowed:
        return False
    return _transition(db, job_id, allowed, status=stage.value)


def complete_job(db: Session, job_id: UUID, response: RecipeResponse) -> bool:
    return _transition(
        db,
        job_id,
        ACTIVE_STATUSES,
        status=JobStatus.COMPLETED.value,
        result=response.model_dump(mode="json", by_alias=True),
        title=response.recipe.name if response.recipe else None,
    )


def fail_job(db: Session, job_id: UUID, reason: FailureReason) -> bool:
    return _transition(
        db,
        job_id,
        NON_TERMINAL_STATUSES,
        status=JobStatus.FAILED.value,
        failure_reason=reason.value,
    )


def retry_job(db: Session, job_id: UUID) -> bool:
    return _transition(
        db,
        job_id,
        [JobStatus.FAILED],
        status=JobStatus.QUEUED.value,
        failure_reason=None,
        result=None,
        title=None,
        started_at=func.now(),
    )


def mark_uploaded(db: Session, job_id: UUID) -> bool:
    return _transition(
        db, job_id, [JobStatus.COMPLETED], uploaded_to_mealie_at=func.now()
    )


def save_recipe(db: Session, job_id: UUID, recipe: Recipe) -> bool:
    job = get_job(db, job_id)
    if job is None or job.result is None:
        return False
    # A new dict, so the JSONB change is written as a whole.
    result = {**job.result, "recipe": recipe.model_dump(mode="json", by_alias=True)}
    return _transition(
        db, job_id, [JobStatus.COMPLETED], result=result, title=recipe.name
    )


def delete_finished_job(db: Session, job_id: UUID) -> bool:
    result = db.execute(
        delete(ExtractionJob)
        .where(
            ExtractionJob.id == job_id,
            ExtractionJob.status.in_(_values(TERMINAL_STATUSES)),
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return result.rowcount == 1


def fail_orphaned_jobs(db: Session) -> int:
    """Fail all waiting or running jobs; called at startup, when none can be alive."""
    result = db.execute(
        update(ExtractionJob)
        .where(ExtractionJob.status.in_(_values(NON_TERMINAL_STATUSES)))
        .values(
            status=JobStatus.FAILED.value,
            failure_reason=FailureReason.RESTARTED.value,
            updated_at=func.now(),
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return result.rowcount
