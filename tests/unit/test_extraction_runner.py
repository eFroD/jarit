"""ExtractionRunner with an in-memory store and fake extractors (no DB, no LLM)."""

import asyncio
import logging
import uuid

import pytest
from pydantic_ai.exceptions import ModelHTTPError

from jarit.jobs.errors import TranscriptionFailedError, VideoUnreachableError
from jarit.jobs.models import (
    NON_TERMINAL_STATUSES,
    STAGE_TRANSITIONS,
    FailureReason,
    JobStatus,
)
from jarit.jobs.runner import ExtractionRunner, JobInput
from tests.factories import empty_response, make_response

pytestmark = pytest.mark.asyncio


class FakeStore:
    """Mimics the guarded transitions of jarit.jobs.repository in memory."""

    def __init__(self):
        self.jobs: dict[uuid.UUID, dict] = {}
        self.started: list[uuid.UUID] = []

    def add(self, url="https://example.com/v", language="english"):
        job_id = uuid.uuid4()
        self.jobs[job_id] = {
            "input": JobInput(url, language),
            "status": JobStatus.QUEUED,
            "stages": [],
            "reason": None,
            "response": None,
        }
        return job_id

    async def load(self, job_id):
        job = self.jobs.get(job_id)
        return job and job["input"]

    async def start(self, job_id):
        job = self.jobs.get(job_id)
        if not job or job["status"] != JobStatus.QUEUED:
            return False
        job["status"] = JobStatus.FETCHING_DESCRIPTION
        self.started.append(job_id)
        return True

    async def advance(self, job_id, stage):
        job = self.jobs.get(job_id)
        if not job or job["status"] not in STAGE_TRANSITIONS.get(stage, ()):
            return False
        job["status"] = stage
        job["stages"].append(stage)
        return True

    async def complete(self, job_id, response):
        job = self.jobs[job_id]
        job["status"] = JobStatus.COMPLETED
        job["response"] = response
        return True

    async def fail(self, job_id, reason):
        job = self.jobs.get(job_id)
        if not job or job["status"] not in NON_TERMINAL_STATUSES:
            return False
        job["status"] = JobStatus.FAILED
        job["reason"] = reason
        return True

    def requeue(self, job_id):
        self.jobs[job_id]["status"] = JobStatus.QUEUED


async def wait_until(predicate, timeout=2.0):
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.005)


def finished(store, *job_ids):
    return lambda: all(
        store.jobs[j]["status"] in (JobStatus.COMPLETED, JobStatus.FAILED)
        for j in job_ids
    )


async def running(store, extract, limit=2, **kwargs):
    runner = ExtractionRunner(limit=limit, extract=extract, store=store, **kwargs)
    runner.start()
    return runner


# --- US1 --------------------------------------------------------------------


async def test_job_is_extracted_and_completed():
    store = FakeStore()
    calls = []

    async def extract(url, language, report):
        calls.append((url, language))
        return make_response("Soup")

    runner = await running(store, extract)
    job_id = store.add("https://example.com/soup", "german")
    runner.submit(job_id)
    await wait_until(finished(store, job_id))
    await runner.stop()

    assert calls == [("https://example.com/soup", "german")]
    assert store.jobs[job_id]["status"] == JobStatus.COMPLETED
    assert store.jobs[job_id]["response"].recipe.name == "Soup"


async def test_no_recipe_fails_with_reason():
    store = FakeStore()

    async def extract(url, language, report):
        return empty_response()

    runner = await running(store, extract)
    job_id = store.add()
    runner.submit(job_id)
    await wait_until(finished(store, job_id))
    await runner.stop()

    assert store.jobs[job_id]["reason"] == FailureReason.NO_RECIPE_FOUND


async def test_deleted_job_is_skipped():
    store = FakeStore()
    called = False

    async def extract(url, language, report):
        nonlocal called
        called = True
        return make_response()

    runner = await running(store, extract)
    job_id = store.add()
    del store.jobs[job_id]
    runner.submit(job_id)
    await asyncio.sleep(0.05)
    await runner.stop()
    assert not called


async def test_submit_from_another_thread():
    store = FakeStore()

    async def extract(url, language, report):
        return make_response()

    runner = await running(store, extract)
    job_id = store.add()
    await asyncio.to_thread(runner.submit, job_id)
    await wait_until(finished(store, job_id))
    await runner.stop()
    assert store.jobs[job_id]["status"] == JobStatus.COMPLETED


async def test_submit_before_start_is_an_error():
    runner = ExtractionRunner(limit=1, extract=None, store=FakeStore())
    with pytest.raises(RuntimeError):
        runner.submit(uuid.uuid4())


async def test_stop_cancels_idle_workers():
    runner = await running(FakeStore(), None, limit=3)
    workers = list(runner._workers)
    await runner.stop()
    assert all(w.done() for w in workers)


async def test_store_error_does_not_kill_the_worker(caplog):
    store = FakeStore()

    async def broken_load(job_id):
        raise ConnectionError("database down")

    async def extract(url, language, report):
        return make_response()

    runner = await running(store, extract, limit=1)
    original_load = store.load
    store.load = broken_load
    first = store.add()
    runner.submit(first)
    await asyncio.sleep(0.05)
    store.load = original_load
    second = store.add()
    runner.submit(second)
    await wait_until(finished(store, second))
    await runner.stop()

    assert store.jobs[second]["status"] == JobStatus.COMPLETED
    assert f"Extraction worker error (job {first})" in caplog.text


# --- US2 --------------------------------------------------------------------


async def test_reported_stages_reach_the_store():
    store = FakeStore()

    async def extract(url, language, report):
        await report(JobStatus.EXTRACTING)
        await report(JobStatus.TRANSCRIBING)
        await report(JobStatus.EXTRACTING)
        await report(JobStatus.FETCHING_DESCRIPTION)  # ignored by the guard
        return make_response()

    runner = await running(store, extract)
    job_id = store.add()
    runner.submit(job_id)
    await wait_until(finished(store, job_id))
    await runner.stop()

    assert store.jobs[job_id]["stages"] == [
        JobStatus.EXTRACTING,
        JobStatus.TRANSCRIBING,
        JobStatus.EXTRACTING,
    ]


# --- US3 --------------------------------------------------------------------


@pytest.mark.parametrize(
    "exc, reason",
    [
        (VideoUnreachableError(), FailureReason.VIDEO_UNREACHABLE),
        (TranscriptionFailedError(), FailureReason.TRANSCRIPTION_FAILED),
        (ModelHTTPError(500, "gemini"), FailureReason.LLM_ERROR),
        (ValueError("boom"), FailureReason.UNKNOWN),
    ],
)
async def test_exceptions_map_to_reasons_and_are_logged(exc, reason, caplog):
    store = FakeStore()

    async def extract(url, language, report):
        raise exc

    caplog.set_level(logging.ERROR)
    runner = await running(store, extract)
    job_id = store.add()
    runner.submit(job_id)
    await wait_until(finished(store, job_id))
    await runner.stop()

    assert store.jobs[job_id]["reason"] == reason
    record = next(
        r for r in caplog.records if r.msg.startswith("Extraction job %s failed")
    )
    assert str(job_id) in record.getMessage()
    assert record.job_id == str(job_id)
    assert record.reason == reason.value


async def test_timeout_fails_job_and_frees_the_slot():
    store = FakeStore()
    never = asyncio.Event()

    async def extract(url, language, report):
        if url.endswith("slow"):
            await never.wait()
        return make_response()

    runner = await running(store, extract, limit=1, timeout=0.05)
    slow = store.add("https://example.com/slow")
    fast = store.add("https://example.com/fast")
    runner.submit(slow)
    runner.submit(fast)
    await wait_until(finished(store, slow, fast))
    await runner.stop()

    assert store.jobs[slow]["reason"] == FailureReason.TIMEOUT
    assert store.jobs[fast]["status"] == JobStatus.COMPLETED


# --- US4 --------------------------------------------------------------------


async def test_concurrency_never_exceeds_the_limit():
    store = FakeStore()
    active = 0
    peak = 0
    release = asyncio.Event()

    async def extract(url, language, report):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await release.wait()
        active -= 1
        return make_response()

    runner = await running(store, extract, limit=2)
    jobs = [store.add() for _ in range(6)]
    for job_id in jobs:
        runner.submit(job_id)

    await wait_until(lambda: active == 2)
    await asyncio.sleep(0.05)  # give extra workers a chance to misbehave
    assert peak == 2
    assert sum(store.jobs[j]["status"] == JobStatus.QUEUED for j in jobs) == 4

    release.set()
    await wait_until(finished(store, *jobs))
    await runner.stop()
    assert peak == 2
    assert all(store.jobs[j]["status"] == JobStatus.COMPLETED for j in jobs)


async def test_jobs_start_in_submission_order_including_retries():
    store = FakeStore()
    gate = asyncio.Event()

    async def extract(url, language, report):
        await gate.wait()
        if url.endswith("fail"):
            raise VideoUnreachableError()
        return make_response()

    runner = await running(store, extract, limit=1)
    flaky = store.add("https://example.com/fail")
    a, b = store.add(), store.add()
    for job_id in (flaky, a, b):
        runner.submit(job_id)
    gate.set()
    await wait_until(finished(store, flaky))

    # Retry: back to waiting, queued behind the jobs that are already waiting.
    store.requeue(flaky)
    store.jobs[flaky]["input"] = JobInput("https://example.com/ok", "english")
    runner.submit(flaky)
    await wait_until(finished(store, a, b, flaky))
    await runner.stop()

    assert store.started == [flaky, a, b, flaky]


@pytest.mark.parametrize("status, logged", [(400, True), (429, False)])
async def test_rejected_configuration_gets_one_clear_log_line(
    status, logged, caplog, monkeypatch
):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    store = FakeStore()

    async def extract(url, language, report):
        raise ModelHTTPError(
            status, "gpt-6-luna", {"message": "reasoning_effort not supported"}
        )

    caplog.set_level(logging.ERROR)
    runner = await running(store, extract)
    job_id = store.add()
    runner.submit(job_id)
    await wait_until(finished(store, job_id))
    await runner.stop()

    assert store.jobs[job_id]["reason"] == FailureReason.LLM_ERROR
    rejected = [
        r
        for r in caplog.records
        if r.name == "jarit.jobs.runner"
        and r.getMessage().startswith("LLM provider rejected the request")
    ]
    if not logged:
        assert rejected == []
        return
    assert len(rejected) == 1
    message = rejected[0].getMessage()
    assert "provider=openai" in message
    assert "model=gpt-6-luna" in message
    assert "reasoning_effort not supported" in message
    assert rejected[0].job_id == str(job_id)
    assert rejected[0].status == 400
