"""Application lifespan: restart cleanup and runner wiring."""

import logging

from fastapi.testclient import TestClient

import main
from jarit.jobs import repository
from jarit.jobs.models import FailureReason, JobStatus
from jarit.jobs.runner import ExtractionRunner


def test_restart_fails_interrupted_jobs_before_serving(db, user, caplog, monkeypatch):
    waiting = repository.create_job(db, user.id, "https://example.com/1", "english")
    running = repository.create_job(db, user.id, "https://example.com/2", "english")
    repository.start_job(db, running.id)
    monkeypatch.setenv("JARIT_MAX_CONCURRENT_EXTRACTIONS", "3")
    caplog.set_level(logging.INFO)

    with TestClient(main.app):
        db.expire_all()
        for job in (waiting, running):
            stored = repository.get_job(db, job.id)
            assert stored.status == JobStatus.FAILED.value
            assert stored.failure_reason == FailureReason.RESTARTED.value

        runner = main.app.state.extraction_runner
        assert isinstance(runner, ExtractionRunner)
        assert runner.limit == 3

    assert "Marked 2 interrupted extraction jobs as failed" in caplog.text
    assert "Extraction concurrency limit: 3" in caplog.text
