"""Guarded state transitions of extraction jobs."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from jarit.jobs import repository as repo
from jarit.jobs.models import FailureReason, JobStatus
from tests.factories import make_recipe, make_response


def new_job(db, user, url="https://example.com/v/1"):
    return repo.create_job(db, user.id, url, "english")


def status(db, job):
    db.expire_all()
    return repo.get_job(db, job.id).status


def test_create_and_read_own_jobs_only(db, user, other_user):
    first = new_job(db, user, "https://example.com/1")
    second = new_job(db, user, "https://example.com/2")
    foreign = new_job(db, other_user)

    assert first.status == JobStatus.QUEUED.value
    assert repo.get_owned_job(db, user.id, first.id).id == first.id
    assert repo.get_owned_job(db, user.id, foreign.id) is None
    assert [j.id for j in repo.list_owned_jobs(db, user.id)] == [second.id, first.id]


def backdate(db, job):
    """Moves created_at and started_at one hour back and returns the old values."""
    db.execute(
        text(
            "UPDATE extraction_jobs SET created_at = now() - interval '1 hour', "
            "started_at = now() - interval '1 hour' WHERE id = :id"
        ),
        {"id": job.id},
    )
    db.commit()
    db.expire_all()
    stored = repo.get_job(db, job.id)
    return stored.created_at, stored.started_at


def test_new_job_has_started_at(db, user):
    job = new_job(db, user)
    assert job.started_at is not None
    assert job.started_at == job.created_at


def test_happy_path_transitions(db, user):
    job = new_job(db, user)
    assert repo.start_job(db, job.id)
    assert repo.advance_stage(db, job.id, JobStatus.EXTRACTING)
    assert repo.complete_job(db, job.id, make_response("Soup"))

    db.expire_all()
    stored = repo.get_job(db, job.id)
    assert stored.status == JobStatus.COMPLETED.value
    assert stored.title == "Soup"
    assert stored.result["recipe"]["name"] == "Soup"
    assert stored.result["recipe"]["@type"] == "Recipe"


def test_start_only_from_queued(db, user):
    job = new_job(db, user)
    assert repo.start_job(db, job.id)
    assert not repo.start_job(db, job.id)


def test_stage_transition_table(db, user):
    job = new_job(db, user)
    repo.start_job(db, job.id)
    # The model may decide to transcribe after it started extracting.
    assert repo.advance_stage(db, job.id, JobStatus.EXTRACTING)
    assert repo.advance_stage(db, job.id, JobStatus.TRANSCRIBING)
    assert repo.advance_stage(db, job.id, JobStatus.EXTRACTING)
    # A late second description call does not move the display back.
    assert not repo.advance_stage(db, job.id, JobStatus.FETCHING_DESCRIPTION)
    assert not repo.advance_stage(db, job.id, JobStatus.COMPLETED)
    assert status(db, job) == JobStatus.EXTRACTING.value


def test_complete_requires_active_job(db, user):
    queued = new_job(db, user)
    assert not repo.complete_job(db, queued.id, make_response())

    failed = new_job(db, user)
    repo.fail_job(db, failed.id, FailureReason.UNKNOWN)
    repo.start_job(db, failed.id)
    assert not repo.complete_job(db, failed.id, make_response())


def test_complete_after_delete_is_dropped(db, user):
    job_id = new_job(db, user).id
    repo.fail_job(db, job_id, FailureReason.UNKNOWN)
    assert repo.delete_finished_job(db, job_id)
    assert not repo.complete_job(db, job_id, make_response())
    assert not repo.fail_job(db, job_id, FailureReason.TIMEOUT)


def test_fail_sets_reason_and_is_final(db, user):
    job = new_job(db, user)
    assert repo.fail_job(db, job.id, FailureReason.VIDEO_UNREACHABLE)
    assert not repo.fail_job(db, job.id, FailureReason.TIMEOUT)
    db.expire_all()
    stored = repo.get_job(db, job.id)
    assert stored.failure_reason == FailureReason.VIDEO_UNREACHABLE.value


def test_failed_without_reason_violates_constraint(db, user):
    with pytest.raises(IntegrityError):
        db.execute(
            text(
                "INSERT INTO extraction_jobs (id, user_id, video_url, target_language, status) "
                "VALUES (gen_random_uuid(), :u, 'https://x', 'english', 'FAILED')"
            ),
            {"u": user.id},
        )
        db.commit()
    db.rollback()


def test_retry_only_from_failed_and_clears_state(db, user):
    job = new_job(db, user)
    assert not repo.retry_job(db, job.id)
    repo.fail_job(db, job.id, FailureReason.LLM_ERROR)
    created_at, started_at = backdate(db, job)
    assert repo.retry_job(db, job.id)
    assert not repo.retry_job(db, job.id)
    db.expire_all()
    stored = repo.get_job(db, job.id)
    assert stored.status == JobStatus.QUEUED.value
    assert stored.failure_reason is None
    assert stored.result is None and stored.title is None
    assert stored.started_at > started_at
    assert stored.created_at == created_at


def completed_job(db, user, name="Soup"):
    job = new_job(db, user)
    repo.start_job(db, job.id)
    repo.complete_job(db, job.id, make_response(name, suggested="Soup v2"))
    return job


def test_mark_uploaded_only_when_completed(db, user):
    queued = new_job(db, user)
    assert not repo.mark_uploaded(db, queued.id)
    done = completed_job(db, user)
    assert repo.mark_uploaded(db, done.id)
    db.expire_all()
    assert repo.get_job(db, done.id).uploaded_to_mealie_at is not None


def test_save_recipe_replaces_recipe_and_title_only(db, user):
    job = completed_job(db, user)
    assert repo.save_recipe(db, job.id, make_recipe("Better soup"))
    db.expire_all()
    stored = repo.get_job(db, job.id)
    assert stored.title == "Better soup"
    assert stored.result["recipe"]["name"] == "Better soup"
    assert stored.result["suggested_version"]["name"] == "Soup v2"


def test_save_recipe_requires_completed(db, user):
    job = new_job(db, user)
    assert not repo.save_recipe(db, job.id, make_recipe())


def test_delete_only_finished_jobs(db, user):
    queued = new_job(db, user)
    assert not repo.delete_finished_job(db, queued.id)
    done_id = completed_job(db, user).id
    assert repo.delete_finished_job(db, done_id)
    assert repo.get_job(db, done_id) is None


def test_fail_orphaned_jobs_only_touches_non_terminal(db, user):
    queued = new_job(db, user)
    running = new_job(db, user)
    repo.start_job(db, running.id)
    repo.advance_stage(db, running.id, JobStatus.TRANSCRIBING)
    done = completed_job(db, user)
    failed = new_job(db, user)
    repo.fail_job(db, failed.id, FailureReason.TIMEOUT)

    assert repo.fail_orphaned_jobs(db) == 2

    db.expire_all()
    for job in (queued, running):
        stored = repo.get_job(db, job.id)
        assert stored.status == JobStatus.FAILED.value
        assert stored.failure_reason == FailureReason.RESTARTED.value
    assert repo.get_job(db, done.id).status == JobStatus.COMPLETED.value
    assert repo.get_job(db, failed.id).failure_reason == FailureReason.TIMEOUT.value
