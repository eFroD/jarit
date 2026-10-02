# Research: Asynchrone Rezept-Extraktion mit Statusfeedback und Historie

Phase 0 of [plan.md](./plan.md). Each decision lists the rationale and the alternatives that were rejected. Library facts were checked against current docs (Alembic, Pydantic AI) and the locked versions in `uv.lock` (pydantic-ai-slim 1.0.11, SQLAlchemy 2.0.44, FastAPI 0.118, anyio 4.11).

## R1 – Background execution without extra infrastructure (FR-002, FR-015, FR-016)

- **Decision**: An in-process `ExtractionRunner` owned by the FastAPI lifespan. It holds one `asyncio.Queue[UUID]` and starts `N` worker tasks, where `N = JARIT_MAX_CONCURRENT_EXTRACTIONS` (default 2). Each worker loops: `job_id = await queue.get()` → run the job → `task_done()`. Submitting a job only puts its id into the queue.
- **Rationale**: `N` workers pulling from one FIFO queue enforce the limit and the "longest waiting first" order (FR-016) by construction. No locks, no polling of the DB, no extra service. Uvicorn runs a single worker process (`docker-compose.yml` has no `--workers`), which is the documented assumption.
- **Alternatives considered**:
  - `asyncio.Semaphore` + one task per job: works, but creates unbounded waiting tasks, and fairness is an implementation detail of the semaphore.
  - FastAPI `BackgroundTasks`: no concurrency limit, tied to the request lifecycle, no FIFO.
  - DB-polling worker (`SELECT … FOR UPDATE SKIP LOCKED`): would survive restarts and allow several processes, but the spec explicitly fails jobs on restart instead, and polling adds latency and load for no gain with one process.
  - Celery/RQ/arq + Redis: explicitly excluded by the spec.

## R2 – Thread safety between request handlers and the runner

- **Decision**: Job endpoints are plain `def` handlers (FastAPI runs them in its thread pool, like the sync DB access they do). `ExtractionRunner.submit(job_id)` is thread-safe: it calls `loop.call_soon_threadsafe(queue.put_nowait, job_id)` on the loop captured at startup. Workers do their DB writes via `await asyncio.to_thread(...)` with a short-lived `SessionLocal()` per write.
- **Rationale**: The existing code uses a sync SQLAlchemy engine. Running DB calls in the event loop would block the workers' progress updates and every other request for the duration of a query. `asyncio.Queue` is not thread-safe, so the handoff has to go through the loop.
- **Alternatives considered**: Switching to async SQLAlchemy (`asyncpg`). Too large a change for this feature and would touch every existing endpoint.

## R3 – Reporting stages from inside the agent run (FR-006 to FR-008)

- **Decision**: The agent gets a `deps_type=ExtractionDeps` with an async `report(stage)` callback. The two tools become async wrappers with `RunContext[ExtractionDeps]`:
  - `get_description(ctx, input)`: `await ctx.deps.report(FETCHING_DESCRIPTION)`, then `await asyncio.to_thread(video_loader.get_description, input)`, then `await ctx.deps.report(EXTRACTING)`.
  - `get_transcript(ctx, input)`: `await ctx.deps.report(TRANSCRIBING)`, then the threaded call, then `report(EXTRACTING)`.
  The tool names stay the same, so the model sees no change. The runner reports `FETCHING_DESCRIPTION` once before `agent.run` as well, so a job never sits in "wartend" while the LLM decides on its first tool call.
- **Rationale**: Only the tools know when a transcription actually happens (FR-007). Deps are the documented Pydantic AI way to pass per-run state into tools; no globals or contextvars are needed, and tests can pass a fake `report`. Stage changes follow an explicit transition table instead of a strict order: `FETCHING_DESCRIPTION` only from `QUEUED`; `TRANSCRIBING` from `FETCHING_DESCRIPTION` or `EXTRACTING` (the model reads the description, then decides it needs the transcript); `EXTRACTING` from `FETCHING_DESCRIPTION` or `TRANSCRIBING`. Anything else (e.g. a second description call later) is ignored, so the display never jumps back to the first stage. A strict forward-only order would wrongly reject `EXTRACTING → TRANSCRIBING` and hide the transcription stage.
- **Alternatives considered**: Parsing the agent's message stream (`agent.iter`) for tool-call parts. More coupling to Pydantic AI internals and it reports the call before it happens, not when work starts.

## R4 – Mapping failures to user-facing reasons (FR-010, FR-011)

- **Decision**: The tool wrappers translate failures into domain exceptions at the source, where the cause is unambiguous:
  - `yt_dlp.utils.DownloadError` (and other errors) in `get_description` → `VideoUnreachableError`.
  - Any error in `get_transcript` (yt-dlp audio download, ffmpeg, OpenAI Whisper) → `TranscriptionFailedError`.
  The runner then maps the outcome:

  | Outcome | `failure_reason` |
  |---|---|
  | `VideoUnreachableError` | `VIDEO_UNREACHABLE` |
  | `TranscriptionFailedError` | `TRANSCRIPTION_FAILED` |
  | `TimeoutError` from the job timeout | `TIMEOUT` |
  | `pydantic_ai.exceptions.AgentRunError` (incl. `ModelHTTPError`, `UnexpectedModelBehavior`, `UsageLimitExceeded`), `openai.APIError`, `google.genai.errors.APIError`, `httpx.HTTPError` | `LLM_ERROR` |
  | Run succeeds but `output.recipe is None` | `NO_RECIPE_FOUND` |
  | Anything else | `UNKNOWN` |
  | Marked at startup | `RESTARTED` |

  Every failure is logged with `logger.exception("extraction job failed", extra={"job_id", "reason"})`. The API response carries only the reason code; the frontend maps codes to texts.
- **Rationale**: Exceptions raised in Pydantic AI tools (other than `ModelRetry`) propagate out of `agent.run`, so typing them at the source keeps the classification honest. Unclassified errors stay `UNKNOWN` instead of being blamed on the LLM. Codes instead of German/English strings keep the API language-neutral; the current UI is English.
- **Alternatives considered**: Classifying by error-message text. Fragile and leaks third-party wording.

## R5 – Job timeout (FR-012)

- **Decision**: `async with asyncio.timeout(EXTRACTION_TIMEOUT_SECONDS)` (600 s, a module constant) around the whole run of one job.
- **Rationale**: Frees the worker slot and marks the job deterministically. Caveat (documented in code): a yt-dlp/Whisper call already running in a thread cannot be killed and finishes in the background; its result is discarded. With a limit of 2 and a 10-minute timeout this cannot pile up meaningfully.
- **Alternatives considered**: A periodic sweeper marking old active jobs. Needed only for multi-process setups; the in-process timeout covers the single-process case. Startup cleanup (R7) covers crashes.

## R6 – Migrations (FR-019, FR-020)

- **Decision**: Alembic, with the environment in `jarit/db/migrations/` (`env.py`, `versions/`) and an `alembic.ini` at the repo root for CLI use. `env.py` reads `DATABASE_URL` and uses `Base.metadata` as `target_metadata`. Two revisions:
  1. `0001_baseline`: `users` (with the PG enum `user_role_enum`) and `api_keys`, exactly as the current models define them.
  2. `0002_extraction_jobs`: the new table (see [data-model.md](./data-model.md)).

  At startup `main.py` calls `run_migrations(engine)` instead of `Base.metadata.create_all`:
  - If `alembic_version` does not exist but `users` does (an installation created by `create_all`), stamp `0001_baseline` first.
  - Then `command.upgrade(cfg, "head")`, sharing a connection via `cfg.attributes["connection"]` (Alembic cookbook pattern).
- **Rationale**: Alembic is the standard SQLAlchemy migration tool. Running it at startup keeps the host workflow unchanged ("pull image, restart"), which matches FR-020 ("ohne manuelle Datenbankeingriffe"). The stamp step brings existing installations under version control without touching their data. `script_location` is resolved relative to the package, so it works in the container (`COPY . .`) and in tests.
- **Alternatives considered**:
  - A separate `alembic upgrade head` command in the compose file / entrypoint: one more thing hosts must get right, and it would not run for people starting uvicorn directly.
  - Autogenerating the baseline: fine as a starting point, but the result is reviewed and hand-checked against the models (enum name, server defaults, `ondelete`).
- **Risk**: an old installation whose tables drifted from the current models (e.g. created before a column existed) is stamped as baseline anyway. `create_all` never altered tables either, so such drift would already break the app today; out of scope.

## R7 – Restart cleanup (FR-018)

- **Decision**: In the lifespan startup, before the runner starts and before requests are served: one `UPDATE extraction_jobs SET status='FAILED', failure_reason='RESTARTED', updated_at=now() WHERE status IN ('QUEUED','FETCHING_DESCRIPTION','TRANSCRIBING','EXTRACTING')`. The count is logged.
- **Rationale**: Single process, so every non-terminal row at startup is an orphan. One statement, idempotent.

## R8 – State transitions under concurrency

- **Decision**: Every transition is a conditional `UPDATE … WHERE id = :id AND status IN (:allowed)` and checks `rowcount`:
  - retry: `FAILED → QUEUED` (clears `failure_reason`, `result`, `title`); 0 rows → 409 (or 404 if the job is not the user's).
  - delete: only `COMPLETED`/`FAILED`; 0 rows → 409.
  - worker stage/result writes: only from active states; 0 rows (job deleted, or marked by timeout) → the worker drops the result silently.
  - save recipe / mark uploaded: only `COMPLETED`.
- **Rationale**: Double clicks, two tabs and the worker racing a delete are all handled by the database without locks.

## R9 – Storage format for results and edits (FR-005, FR-023)

- **Decision**: `result JSONB` holds the serialized `RecipeResponse` (`recipe`, `suggested_version`, `error_info`) exactly as the old endpoint returned it (`model_dump(mode="json", by_alias=True)`). Saving an edit validates the body as `Recipe` and replaces `result.recipe`; `title` is denormalized from `recipe.name` on completion and on every edit.
- **Rationale**: Same shape as before, so the editor needs no new model. Only the latest version is kept (spec assumption). `title` as its own column lets the history list avoid loading every JSON document.

## R10 – Mealie upload from a job (FR-022, FR-024)

- **Decision**: New `POST /extraction-jobs/{id}/upload-mealie` uploads the stored `result.recipe` using the existing `get_mealie_credentials` dependency and `push_recipe_to_mealie`, then sets `uploaded_to_mealie_at = now()` only on success. The old `POST /integrations/upload-mealie` (recipe in the body) is removed; the frontend is the only client. The editor saves before it uploads.
- **Rationale**: The upload flag can only be trusted if the server uploads the recipe it stores. Keeping the body-based endpoint would allow uploads that never set the flag. Mealie error handling (status passthrough, 409 for unreadable credentials) stays as in feature 001.

## R11 – Job identifiers and access control (FR-003)

- **Decision**: `id UUID` (random, `uuid4`). Every query filters by `user_id = current_user.id`. A missing or foreign job gives the same `404 {"detail": "Extraction job not found"}`. Admins get no extra access.
- **Rationale**: Non-guessable ids plus owner filtering; identical 404s prevent probing for foreign jobs.

## R12 – Frontend progress and navigation (FR-009, FR-009a, FR-009b)

- **Decision**:
  - Submit → `POST /extraction-jobs` → navigate to `/jobs/[id]`.
  - `/jobs/[id]` polls `GET /extraction-jobs/{id}` every 2 s while the job is non-terminal and stops polling when the component is destroyed. On `COMPLETED` it loads the result into the existing stores (`extractedRecipe`, `suggestedRecipe`, plus a new `currentJobId`) and goes to `/jobs/<id>/recipe`. On `FAILED` it shows the reason text and a "Try again" button.
  - `/jobs/<id>/recipe` loads the job if the store is empty (reload, deep link), saves edits via `PUT …/recipe` (explicit "Save" and implicitly before upload), and uploads via the job endpoint.
  - New `/history` page lists jobs; navigation gets a "History" link.
  - The dashboard shows a small "in progress" list of the user's non-terminal jobs (from the history endpoint), so returning after leaving the page leads back to the progress view.
- **Rationale**: A 2-s interval meets the 5-s requirement with headroom, and the requests are cheap. Dynamic routes work with `adapter-static` because the app is built with `fallback: 'index.html'` and nginx already does `try_files … /index.html`. The URL holds the job id, so reloads and returning keep working without `localStorage`.
- **Alternatives considered**: SSE/WebSocket push. Explicitly ruled out by the spec ("regelmäßiges Abfragen") and harder to put behind nginx.

## R13 – Tests without LLM, Whisper or network (FR-028, FR-029)

- **Decision**:
  - `tests/conftest.py` sets `pydantic_ai.models.ALLOW_MODEL_REQUESTS = False`.
  - The runner takes an injectable `extract(job, report)` coroutine. Runner tests (queue, limit, FIFO, timeout, failure mapping, restart cleanup) use fakes driven by `asyncio.Event`s, with the timeout shortened via a parameter.
  - Agent-level tests use `video_agent.override(model=FunctionModel(...))` with `video_loader.get_description` / `get_transcript` monkeypatched, to check the stage sequence with and without transcription, and the exception translation.
  - API tests (`tests/db/`) use the existing `client` fixture with a second user, and a runner fake that completes jobs synchronously.
  - Mealie upload is tested with `push_recipe_to_mealie` monkeypatched.
  - Migration tests run `run_migrations` against an empty schema and against a schema created by the old `create_all` path with rows in it.
- **Rationale**: These are the patterns recommended by the Pydantic AI testing docs. Everything runs inside the existing CI job (Postgres service container, no secrets).

## R14 – Coverage gate (FR-027)

- **Decision**: The CI test step becomes `uv run pytest -q --cov=jarit --cov=main --cov-report=term-missing --cov-fail-under=80`.
- **Finding**: Measured on `dev` at `4773479` with a Postgres test DB: **81 % (622 statements, 116 missed), 55 tests passed**. Without Postgres the number is 32 %, so the gate only makes sense where `tests/db` runs, which CI does.
- **Rationale**: `pytest-cov` is already a dev dependency. Local runs without Postgres stay ungated because the flag only lives in the workflow.

## R15 – Running time after a retry (FR-009c, FR-013, FR-004)

- **Decision**:
  - New column `extraction_jobs.started_at TIMESTAMPTZ NOT NULL DEFAULT now()`. It is set on insert and reset to `now()` by `retry_job`, in the same conditional `UPDATE` that clears `failure_reason`, `result` and `title`. `created_at` stays the submission time and remains the history sort key.
  - It is added by a new Alembic revision `0003_job_started_at`: add the column as nullable, backfill `started_at = created_at`, then set `NOT NULL` and `server_default now()`.
  - `ExtractionJobSummary`/`ExtractionJob` expose `started_at`. The progress page computes "Running for" from `started_at`; the history keeps showing `created_at`.
- **Rationale**: The progress page cannot derive the restart time from `updated_at`, because every stage change moves `updated_at`. A separate column keeps both meanings ("submitted" vs. "this run started") explicit. A new revision instead of editing `0002` is needed because development databases on this branch are already at `0002`. Alembic would skip a changed `0002` there, and the column would be missing.
- **Alternatives considered**:
  - Reset `created_at` on retry. Rejected: the history would reorder the job and lose the original submission time (spec edge case "Laufzeitanzeige nach erneutem Start").
  - Track the restart time only in the browser. Rejected: it is lost on reload and in a second tab, and wrong when the retry came from the history page.
  - Measure from the time the worker actually starts the job (leaving `QUEUED`). Rejected for now: the spec counts from submit or retry, and time spent waiting for a free slot is part of what the user waits for.

## R16 – Editor state per job (FR-023a, FR-023b)

- **Decision**:
  - **Unsaved state is derived, not a flag.** `RecipePreview` keeps the job as last returned by the server (`job`, from `GET` on mount or the response of `PUT …/recipe`). "Unsaved changes" is `serialize(recipe) !== serialize(job.result.recipe)`, where `serialize` is `JSON.stringify` over the same object shape. Edits that are kept in the `extractedRecipe` store across navigation therefore still count as unsaved when the job is reopened. The local `dirty` boolean is removed.
  - **Upload uploads what is shown.** `handleUpload` saves first whenever the derived state is "unsaved". If the save fails, it stops and shows the error, so the upload does not run. This is already the order today; only the condition changes.
  - **Only the opened job's recipe is editable.** The editor renders the form only when `job?.id === jobId` and `$currentJobId === jobId`. The store's recipe is bound to the editor only under the same condition. Until then it shows "Loading…"; if the `GET` fails (network, 404) it shows an error with a link to `/history` and no form. `save()` and `handleUpload()` return early unless `job?.id === jobId`.
  - On a successful load with `$currentJobId !== jobId` (or an empty store), the stores are replaced with the server version as today. On a load with `$currentJobId === jobId`, the store keeps the edits, and the derived state shows them as unsaved if they differ.
- **Rationale**: The bug came from two separate sources of truth: the store kept the edits, but the "dirty" flag was per component instance. Deriving the state from the data removes that class of error. The ownership guard closes the window in which another job's recipe was editable under this job's id.
- **Alternatives considered**:
  - Persist `dirty` in a store next to `currentJobId`. Rejected: it can still drift from the data, for example after a save in another tab.
  - Drop the kept edits on every reopen. Rejected: losing unsaved edits on back navigation is a worse experience than showing them as unsaved.
  - Put a draft of the edits in `localStorage`. Out of scope; the spec only asks that unsaved changes are labelled correctly and never uploaded by mistake.
