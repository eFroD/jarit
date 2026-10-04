"""Runs extraction jobs in the background, inside the backend process.

A fixed number of worker tasks pull job ids from one FIFO queue, which enforces
the concurrency limit and the "longest waiting first" order. Jobs are persisted,
the queue is not: jobs left over from a previous process are failed at startup
(repository.fail_orphaned_jobs).
"""

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from jarit.jobs.errors import classify, describe_rejected_request
from jarit.jobs.models import FailureReason, JobStatus
from jarit.models.output_models.recipe import RecipeResponse

logger = logging.getLogger(__name__)

EXTRACTION_TIMEOUT_SECONDS = 600

Report = Callable[[JobStatus], Awaitable[None]]
Extract = Callable[[str, str, Report], Awaitable[RecipeResponse]]


@dataclass(frozen=True)
class JobInput:
    video_url: str
    target_language: str


class JobStore(Protocol):
    async def load(self, job_id: UUID) -> JobInput | None: ...
    async def start(self, job_id: UUID) -> bool: ...
    async def advance(self, job_id: UUID, stage: JobStatus) -> bool: ...
    async def complete(self, job_id: UUID, response: RecipeResponse) -> bool: ...
    async def fail(self, job_id: UUID, reason: FailureReason) -> bool: ...


class DbJobStore:
    """JobStore on the database; each call uses its own short session in a thread.

    The database modules are imported here, not at module level, so the runner
    stays importable (and unit-testable) without a configured database.
    """

    def __init__(self):
        from jarit.db.database import SessionLocal
        from jarit.jobs import repository

        self._session = SessionLocal
        self._repo = repository

    async def _run(self, fn, *args):
        def call():
            with self._session() as db:
                return fn(db, *args)

        return await asyncio.to_thread(call)

    async def load(self, job_id: UUID) -> JobInput | None:
        def read(db, job_id):
            job = self._repo.get_job(db, job_id)
            return job and JobInput(job.video_url, job.target_language)

        return await self._run(read, job_id)

    async def start(self, job_id: UUID) -> bool:
        return await self._run(self._repo.start_job, job_id)

    async def advance(self, job_id: UUID, stage: JobStatus) -> bool:
        return await self._run(self._repo.advance_stage, job_id, stage)

    async def complete(self, job_id: UUID, response: RecipeResponse) -> bool:
        return await self._run(self._repo.complete_job, job_id, response)

    async def fail(self, job_id: UUID, reason: FailureReason) -> bool:
        return await self._run(self._repo.fail_job, job_id, reason)


class ExtractionRunner:
    def __init__(
        self,
        limit: int,
        extract: Extract,
        store: JobStore,
        timeout: float = EXTRACTION_TIMEOUT_SECONDS,
    ):
        self.limit = limit
        self._extract = extract
        self._store = store
        self._timeout = timeout
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.Queue[UUID] | None = None
        self._workers: list[asyncio.Task] = []

    def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()
        self._workers = [
            asyncio.create_task(self._work(), name=f"extraction-worker-{i}")
            for i in range(self.limit)
        ]

    async def stop(self) -> None:
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers = []

    def submit(self, job_id: UUID) -> None:
        """Queue a job. Safe to call from request handler threads."""
        if self._loop is None or self._queue is None:
            raise RuntimeError("ExtractionRunner is not started")
        self._loop.call_soon_threadsafe(self._queue.put_nowait, job_id)

    async def _work(self) -> None:
        while True:
            job_id = await self._queue.get()
            try:
                await self._run_job(job_id)
            except Exception:
                # Never let one job kill the worker (e.g. the database is down).
                logger.exception(
                    "Extraction worker error (job %s)",
                    job_id,
                    extra={"job_id": str(job_id)},
                )
            finally:
                self._queue.task_done()

    async def _run_job(self, job_id: UUID) -> None:
        job = await self._store.load(job_id)
        if job is None or not await self._store.start(job_id):
            return  # deleted or no longer waiting

        async def report(stage: JobStatus) -> None:
            await self._store.advance(job_id, stage)

        try:
            # Threads started by the tools (yt-dlp, Whisper) cannot be cancelled.
            # After a timeout they finish in the background; the guarded update
            # in the store drops anything they would still report.
            async with asyncio.timeout(self._timeout):
                response = await self._extract(
                    job.video_url, job.target_language, report
                )
        except Exception as exc:
            if detail := describe_rejected_request(exc):
                provider = os.getenv("LLM_PROVIDER", "google").lower()
                logger.error(
                    "LLM provider rejected the request (check the model configuration): provider=%s %s",
                    provider,
                    detail,
                    extra={
                        "job_id": str(job_id),
                        "provider": provider,
                        "model": getattr(exc, "model_name", None),
                        "status": getattr(exc, "status_code", None),
                    },
                )
            reason = classify(exc)
            logger.exception(
                "Extraction job %s failed: %s",
                job_id,
                reason.value,
                extra={"job_id": str(job_id), "reason": reason.value},
            )
            await self._store.fail(job_id, reason)
            return

        if response.recipe is None:
            logger.info(
                "Extraction job %s found no recipe",
                job_id,
                extra={"job_id": str(job_id)},
            )
            await self._store.fail(job_id, FailureReason.NO_RECIPE_FOUND)
            return

        await self._store.complete(job_id, response)
