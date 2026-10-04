"""Asynchronous recipe extraction jobs and the per-user extraction history.

Every endpoint only sees the current user's jobs; a foreign job answers exactly
like a missing one (404), for admins too.
"""

from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from jarit.api.errors import AppError, ErrorCode
from jarit.api.v1.endpoints.integrations import get_mealie_credentials
from jarit.api.v1.endpoints.users import get_current_user
from jarit.db.database import get_db
from jarit.db.models.extraction_jobs import ExtractionJob
from jarit.db.models.users import User
from jarit.integrations.mealie_integration import push_recipe_to_mealie
from jarit.jobs import repository
from jarit.jobs.models import (
    ExtractionJobCreate,
    ExtractionJobDetail,
    ExtractionJobSummary,
    JobStatus,
)
from jarit.jobs.runner import ExtractionRunner
from jarit.models.output_models.recipe import Recipe

router = APIRouter()

JOB_NOT_FOUND = "Extraction job not found"


def get_runner(request: Request) -> ExtractionRunner:
    return request.app.state.extraction_runner


def get_owned_job_or_404(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExtractionJob:
    try:
        parsed = UUID(job_id)
    except ValueError:
        raise AppError(404, ErrorCode.JOB_NOT_FOUND, JOB_NOT_FOUND) from None
    job = repository.get_owned_job(db, current_user.id, parsed)
    if job is None:
        raise AppError(404, ErrorCode.JOB_NOT_FOUND, JOB_NOT_FOUND)
    return job


def _reload(db: Session, job: ExtractionJob) -> ExtractionJob:
    db.refresh(job)
    return job


@router.post(
    "", status_code=status.HTTP_202_ACCEPTED, response_model=ExtractionJobDetail
)
def submit_extraction(
    request: ExtractionJobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    runner: ExtractionRunner = Depends(get_runner),
):
    language = request.target_language or current_user.language
    job = repository.create_job(db, current_user.id, str(request.url), language)
    runner.submit(job.id)
    return job


@router.get("", response_model=list[ExtractionJobSummary])
def list_extractions(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return repository.list_owned_jobs(db, current_user.id)


@router.get("/{job_id}", response_model=ExtractionJobDetail)
def get_extraction(job: ExtractionJob = Depends(get_owned_job_or_404)):
    return job


@router.put("/{job_id}/recipe", response_model=ExtractionJobDetail)
def save_recipe(
    recipe: Recipe,
    job: ExtractionJob = Depends(get_owned_job_or_404),
    db: Session = Depends(get_db),
):
    if not repository.save_recipe(db, job.id, recipe):
        raise AppError(
            409, ErrorCode.JOB_NOT_EDITABLE, "Only completed extractions can be edited"
        )
    return _reload(db, job)


@router.post("/{job_id}/upload-mealie")
async def upload_to_mealie(
    job: ExtractionJob = Depends(get_owned_job_or_404),
    mealie_creds: dict = Depends(get_mealie_credentials),
    db: Session = Depends(get_db),
):
    if job.status != JobStatus.COMPLETED.value or not job.result:
        raise AppError(
            409,
            ErrorCode.JOB_NOT_UPLOADABLE,
            "Only completed extractions can be uploaded",
        )
    recipe = Recipe.model_validate(job.result["recipe"])
    try:
        response = await push_recipe_to_mealie(
            recipe.model_dump(by_alias=True, mode="json"),
            mealie_creds["endpoint"],
            mealie_creds["api_key"],
        )
    except httpx.HTTPStatusError as e:
        raise AppError(
            e.response.status_code,
            ErrorCode.MEALIE_ERROR,
            f"Mealie error: {e.response.text}",
        )

    await run_in_threadpool(repository.mark_uploaded, db, job.id)
    job = await run_in_threadpool(_reload, db, job)
    return {"message": response, "uploaded_to_mealie_at": job.uploaded_to_mealie_at}


@router.post(
    "/{job_id}/retry",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ExtractionJobDetail,
)
def retry_extraction(
    job: ExtractionJob = Depends(get_owned_job_or_404),
    db: Session = Depends(get_db),
    runner: ExtractionRunner = Depends(get_runner),
):
    if not repository.retry_job(db, job.id):
        raise AppError(
            409, ErrorCode.JOB_NOT_RETRYABLE, "Only failed extractions can be retried"
        )
    runner.submit(job.id)
    return _reload(db, job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_extraction(
    job: ExtractionJob = Depends(get_owned_job_or_404),
    db: Session = Depends(get_db),
):
    if not repository.delete_finished_job(db, job.id):
        raise AppError(
            409,
            ErrorCode.JOB_NOT_DELETABLE,
            "Wait until the extraction has finished before deleting it",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
