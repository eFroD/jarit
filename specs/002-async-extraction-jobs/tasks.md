---

description: "Task list for asynchronous recipe extraction jobs with progress and history"
---

# Tasks: Asynchrone Rezept-Extraktion mit Statusfeedback und Historie

**Input**: Design documents from `specs/002-async-extraction-jobs/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Included. The spec requires tests for background processing, state transitions, the concurrency limit, restart cleanup and access control, all running without a real LLM, Whisper or network (FR-028, FR-029). CI must enforce ≥ 80 % coverage (FR-027).

**Organization**: Tasks are grouped by user story (US1–US7 from spec.md), so each story can be implemented and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on unfinished tasks)
- **[Story]**: The user story the task belongs to

## Path Conventions

Web app with the backend at the repo root (`main.py`, `jarit/`, `tests/`) and the frontend in `frontend/`. Shared names used throughout:

- Table / ORM: `extraction_jobs` / `jarit.db.models.extraction_jobs.ExtractionJob`
- Enums: `JobStatus`, `FailureReason` in `jarit/jobs/models.py` (values in [data-model.md](./data-model.md))
- Env var: `JARIT_MAX_CONCURRENT_EXTRACTIONS` (default 2)
- Job timeout: `EXTRACTION_TIMEOUT_SECONDS = 600` in `jarit/jobs/runner.py`
- API base: `/api/v1/extraction-jobs` ([contracts/http-api.md](./contracts/http-api.md))
- 404 body for missing **and** foreign jobs: `{"detail": "Extraction job not found"}`
- Run tests: `DATABASE_URL=postgresql://…/jarit_test uv run pytest` (see [quickstart.md](./quickstart.md) §1); unit tests run without it.
- Do **not** commit `.specify/`, `.claude/` or the root `spec.md`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Alembic and test safety nets.

- [X] T001 Add `alembic` as a runtime dependency with `uv add alembic` (updates `pyproject.toml` and `uv.lock`)
- [X] T002 [P] Create `alembic.ini` at the repo root: `script_location = jarit/db/migrations`, no `sqlalchemy.url` (the URL comes from `DATABASE_URL` in `env.py`), standard logger sections
- [X] T003 [P] Create `jarit/db/migrations/env.py` and `jarit/db/migrations/script.py.mako` (plus an empty `jarit/db/migrations/versions/`). `env.py`: import `jarit.db.models` (so every model is registered), set `target_metadata = Base.metadata`. In online mode use `config.attributes.get("connection")` if present, otherwise create an engine from `os.environ["DATABASE_URL"]`. Support offline mode with the same URL.
- [X] T004 [P] Make `jarit/db/models/__init__.py` import `users` and `api_keys` (and later `extraction_jobs`), so `Base.metadata` is complete wherever `jarit.db.models` is imported
- [X] T005 [P] In `tests/conftest.py`, set `pydantic_ai.models.ALLOW_MODEL_REQUESTS = False` at import time so no test can reach a real model provider

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Migrations replace `create_all`, the jobs table exists, repository and CI gate are in place.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T006 Create `jarit/db/migrations/versions/0001_baseline.py` (`revision = "0001_baseline"`, `down_revision = None`). Create `users` and `api_keys` exactly as `jarit/db/models/users.py` and `jarit/db/models/api_keys.py` define them: the PG enum `user_role_enum` (`ADMIN`, `USER`), the unique indexes on `email` and `username`, the index on `users.id`, the `api_keys.user_id` FK with `ON DELETE CASCADE`, and the server defaults `TRUE` / `now()`. `downgrade()` drops both tables and the enum. Check it by comparing `pg_dump --schema-only` of a DB built by `alembic upgrade 0001_baseline` with one built by `Base.metadata.create_all`.
- [X] T007 Create `jarit/db/migrate.py` with `run_migrations(engine) -> None`. Build `alembic.config.Config()` in code with `script_location` set to `Path(__file__).parent / "migrations"`. Inside `with engine.begin() as conn`, set `cfg.attributes["connection"] = conn`. If `inspect(conn)` shows no `alembic_version` table but a `users` table: log INFO `Existing database without migration history, stamping baseline` and call `command.stamp(cfg, "0001_baseline")`. Then call `command.upgrade(cfg, "head")` and log INFO `Database schema at revision <rev>`. Exceptions propagate, so startup aborts.
- [X] T008 In `main.py`, replace `Base.metadata.create_all(bind=engine)` with `run_migrations(engine)` (same position: after `require_encryption_key()`, before `migrate_plaintext_secrets()`) and drop the now-unused `Base` import
- [X] T009 In `tests/db/conftest.py`, make the session-scoped `schema` fixture call `run_migrations(engine)` instead of `Base.metadata.create_all`
- [X] T010 [P] Create `jarit/jobs/__init__.py` and `jarit/jobs/models.py`:
  - `JobStatus` and `FailureReason` as `str` enums with the values from data-model.md
  - `ACTIVE_STATUSES = {FETCHING_DESCRIPTION, TRANSCRIBING, EXTRACTING}`, `NON_TERMINAL_STATUSES = ACTIVE_STATUSES | {QUEUED}`, `TERMINAL_STATUSES = {COMPLETED, FAILED}`
  - `STAGE_TRANSITIONS: dict[JobStatus, set[JobStatus]]` = allowed previous statuses per stage: `FETCHING_DESCRIPTION ← {QUEUED}`, `TRANSCRIBING ← {FETCHING_DESCRIPTION, EXTRACTING}`, `EXTRACTING ← {FETCHING_DESCRIPTION, TRANSCRIBING}` (research R3)
  - Pydantic schemas: `ExtractionJobCreate` (`url: HttpUrl`, `target_language: str = "english"`, stripped, non-empty, `max_length=64`), `ExtractionJobSummary` (fields per contracts/http-api.md, `from_attributes=True`) and `ExtractionJobDetail(ExtractionJobSummary)` with `result: RecipeResponse | None`
- [X] T011 Create `jarit/db/models/extraction_jobs.py` with the `ExtractionJob` ORM model per data-model.md:
  - `UUID(as_uuid=True)` primary key with default `uuid4`
  - `user_id` FK with `ondelete="CASCADE"`; no relationship on `User`
  - `JSONB` result and `TIMESTAMPTZ` columns
  - check constraints `ck_extraction_jobs_status`, `ck_extraction_jobs_failure_reason`, `ck_extraction_jobs_failure_consistency`
  - indexes `ix_extraction_jobs_user_created` (`user_id`, `created_at DESC`) and the partial `ix_extraction_jobs_active`

  Register the model in `jarit/db/models/__init__.py`.
- [X] T012 Create `jarit/db/migrations/versions/0002_extraction_jobs.py` (`down_revision = "0001_baseline"`), creating the table, constraints and indexes from T011 (`downgrade()` drops them). Add `extraction_jobs` to the `TRUNCATE` in `tests/db/conftest.py::truncate_tables`.
- [X] T013 Create `jarit/jobs/repository.py`. Every function takes a `Session` and commits itself.
  - `create_job(db, user_id, video_url, target_language) -> ExtractionJob` (status `QUEUED`)
  - `get_owned_job(db, user_id, job_id) -> ExtractionJob | None`: `None` for a missing job **and** for a foreign one
  - `list_owned_jobs(db, user_id)`: `created_at` descending
  - `_transition(db, job_id, from_statuses, **values) -> bool`: a single `UPDATE … WHERE id = :id AND status IN (:from)` that also sets `updated_at = now()` and returns `rowcount == 1`
  - Built on `_transition`:
    - `start_job` (`QUEUED` → `FETCHING_DESCRIPTION`)
    - `advance_stage(db, job_id, stage)`: allowed only from `STAGE_TRANSITIONS[stage]`; anything else is a no-op returning `False`
    - `complete_job(db, job_id, response: RecipeResponse)`: from active statuses; stores `result = response.model_dump(mode="json", by_alias=True)` and `title = response.recipe.name`
    - `fail_job(db, job_id, reason)`: from non-terminal statuses
    - `mark_uploaded(db, job_id)`: `COMPLETED` only; sets `uploaded_to_mealie_at = now()`
- [X] T014 [P] Create `tests/db/test_migrations.py`. Each test runs in its own Postgres schema: `CREATE SCHEMA`, an engine with `connect_args={"options": "-csearch_path=<schema>"}`, `DROP SCHEMA … CASCADE` in `finally`.
  - (a) Empty schema → `run_migrations` → `users`, `api_keys` and `extraction_jobs` exist and `alembic_version` is at head.
  - (b) Legacy schema built with `Base.metadata.create_all(tables=[User.__table__, APIKey.__table__])`, with one user and one api_key row → `run_migrations` → the rows are unchanged and the version is at head.
  - (c) A second `run_migrations` is a no-op.
- [X] T015 [P] Create `tests/db/test_job_repository.py`:
  - create/get/list, including `get_owned_job` returning `None` for another user's job and `list_owned_jobs` ordering
  - every guard in `_transition`: `complete_job` on a deleted or `FAILED` job returns `False`; `advance_stage` refuses transitions outside `STAGE_TRANSITIONS`
  - `fail_job` sets `failure_reason`
  - inserting `FAILED` without a reason violates `ck_extraction_jobs_failure_consistency`
  - `mark_uploaded` only works on `COMPLETED`
- [X] T016 In `.github/workflows/ci.yml`, change the backend **Tests** step to `uv run pytest -q --cov=jarit --cov=main --cov-report=term-missing --cov-fail-under=80` ([contracts/ci-checks.md](./contracts/ci-checks.md))

**Checkpoint**: `pytest` (with Postgres) is green, the app starts against an old `create_all` database and against an empty one, and coverage is ≥ 80 %.

---

## Phase 3: User Story 1 – Extraktion einreichen und sofort weiterarbeiten (Priority: P1) 🎯 MVP

**Goal**: Submitting returns a job at once; extraction runs in the background; the result is stored, opens in the editor and can be uploaded to Mealie.

**Independent Test**: Submit a URL → `202` in < 2 s with status `QUEUED`. Poll `GET /extraction-jobs/{id}` until `COMPLETED`. The result has the same shape as the old extract response, and the upload to Mealie works.

### Tests for User Story 1

- [X] T017 [P] [US1] Create `tests/unit/test_extraction_runner.py`, using an in-memory `FakeJobStore` (records calls, returns `True`) and fake `extract` coroutines:
  - a submitted job is started, `extract` is called with its URL and language, and `complete` gets the `RecipeResponse`
  - `extract` returning `recipe=None` → `fail(NO_RECIPE_FOUND)`
  - `start` returning `False` (job deleted) → `extract` is never called
  - `submit()` called from another thread via `asyncio.to_thread` still runs the job
  - `stop()` cancels idle workers
- [X] T018 [P] [US1] Create `tests/db/test_extraction_jobs_endpoints.py`. Add a `FakeRunner` fixture to `tests/db/conftest.py` that records submitted ids and is injected by overriding the `get_runner` dependency. Cover:
  - `POST /api/v1/extraction-jobs` → `202`, status `QUEUED`, row exists, id submitted to the runner
  - an invalid URL or blank `target_language` → `422` and no row
  - `GET /{id}` of your own job → `200`; for a job completed via `repository.complete_job`, `result.recipe` is present
  - an unknown or malformed id → `404` with the standard body
  - `POST /{id}/upload-mealie`, with `push_recipe_to_mealie` monkeypatched and Mealie credentials stored via `set_secret`:
    - success → `200` and `uploaded_to_mealie_at` set
    - `httpx.HTTPStatusError` → status passed through, flag stays `null`
    - a non-`COMPLETED` job → `409`
  - `POST /api/v1/recipes/extract-recipe` and `POST /api/v1/integrations/upload-mealie` → `404`/`405`

### Implementation for User Story 1

- [X] T019 [P] [US1] Create `jarit/agents/deps.py` with `@dataclass class ExtractionDeps: report: Callable[[JobStatus], Awaitable[None]]`. In `jarit/agents/video_agent.py`, set `deps_type=ExtractionDeps` on the agent. The tools stay as they are for now.
- [X] T020 [US1] Create `jarit/jobs/pipeline.py` with `async def extract(url: str, target_language: str, report) -> RecipeResponse`. It runs `video_agent.run(<the same prompt as jarit/core/recipe_service.py>, deps=ExtractionDeps(report=report))` and returns `RecipeResponse.model_validate(result.output)`. Delete `jarit/core/recipe_service.py`.
- [X] T021 [US1] Create `jarit/jobs/runner.py`:
  - a `JobStore` protocol (`load`, `start`, `advance`, `complete`, `fail`, all async)
  - `DbJobStore`, which implements it with `jarit/jobs/repository.py` through `asyncio.to_thread` and a fresh `SessionLocal()` per call
  - `ExtractionRunner(limit: int, extract, store)`:
    - `start()` captures the running loop, creates the `asyncio.Queue` and `limit` worker tasks
    - `stop()` cancels the workers and awaits them
    - `submit(job_id)` is thread-safe via `loop.call_soon_threadsafe(queue.put_nowait, job_id)`
  - Worker loop: `start` (skip on `False`) → `extract(url, lang, report)` → `complete`, or `fail(NO_RECIPE_FOUND)` when `recipe is None`. Any exception → `fail(UNKNOWN)` plus `logger.exception("Extraction job failed", extra={"job_id": str(job_id)})`; the exception text is never stored. `report` is wired to `store.advance`.
- [X] T022 [US1] Add a FastAPI `lifespan` in `main.py`. It builds `ExtractionRunner(limit=2, extract=pipeline.extract, store=DbJobStore())`, stores it as `app.state.extraction_runner`, starts it, and stops it on shutdown. Pass it via `FastAPI(..., lifespan=lifespan)`.
- [X] T023 [US1] Create `jarit/api/v1/endpoints/extraction_jobs.py`:
  - `get_runner(request)` returns `request.app.state.extraction_runner`
  - `get_owned_job_or_404(job_id: str, current_user, db)` turns a non-UUID or `None` from `get_owned_job` into `404 "Extraction job not found"`
  - `POST ""` (`status_code=202`, `def` handler): `create_job` + `runner.submit`, returns `ExtractionJobDetail`
  - `GET "/{job_id}"` returns `ExtractionJobDetail`
  - `POST "/{job_id}/upload-mealie"` (`async`, reuses `get_mealie_credentials` from `jarit/api/v1/endpoints/integrations.py`):
    - `409 "Only completed extractions can be uploaded"` unless the job is `COMPLETED`
    - `push_recipe_to_mealie(Recipe.model_validate(result["recipe"]).model_dump(by_alias=True, mode="json"), …)`
    - `mark_uploaded` on success, then `{"message", "uploaded_to_mealie_at"}`
    - `httpx.HTTPStatusError` maps to `HTTPException(e.response.status_code, f"Mealie error: {e.response.text}")` as before
    - DB calls in this async handler go through `run_in_threadpool`
- [X] T024 [US1] Remove the old endpoints and fix their callers:
  - In `jarit/api/router.py`, mount `extraction_jobs.router` (`prefix="/extraction-jobs"`, `tags=["extraction-jobs"]`, `dependencies=[Depends(get_current_user)]`) and remove the `recipes` router.
  - Delete `jarit/api/v1/endpoints/recipes.py`.
  - Remove `POST /upload-mealie` from `jarit/api/v1/endpoints/integrations.py`; keep `get_mealie_credentials` and `verify-mealie-user`.
  - Move the 409 unreadable-credentials upload assertion in `tests/db/test_api_keys_endpoints.py` to `POST /extraction-jobs/{id}/upload-mealie` on a completed job.
  - Update `tests/integration/test_api.py` to submit a job and poll instead of calling `recipes/extract-recipe`.
- [X] T025 [P] [US1] Frontend client code:
  - In `frontend/src/lib/types.ts`, add `JobStatus`, `FailureReason`, `ExtractionJobSummary` and `ExtractionJob` (`result: ExtractRecipeResponse | null`).
  - In `frontend/src/lib/api.ts`, add `createExtractionJob(url, targetLanguage)`, `getExtractionJob(id)` and `uploadJobToMealie(id)`; remove `extractRecipe` and `uploadToMealie`.
  - Create `frontend/src/lib/jobs.ts` with `STATUS_LABELS`, `FAILURE_REASON_LABELS` (English labels from data-model.md), `isTerminal(status)` and `pollJob(id, onUpdate, intervalMs = 2000)`, which returns a stop function.
  - In `frontend/src/lib/store.ts`, add a `currentJobId` writable and clear it in `logout()`.
- [X] T026 [US1] In `frontend/src/lib/components/RecipeExtractor.svelte`, call `api.createExtractionJob` on submit and `goto(resolve('/jobs/[id]', { id }))`. Remove the synchronous result handling.
- [X] T027 [US1] Create `frontend/src/routes/(app)/jobs/[id]/+page.svelte` and `frontend/src/lib/components/JobProgress.svelte`:
  - load and poll with `pollJob`; stop in `onDestroy` and on terminal status
  - show the status label and the URL
  - on `COMPLETED`, set `extractedRecipe`, `suggestedRecipe` and `currentJobId`, then `goto('/jobs/<id>/recipe')`
  - on `FAILED`, show `FAILURE_REASON_LABELS[reason]`
  - on `404`, show "This extraction does not exist." with a link to `/history`
- [X] T028 [US1] Move the editor route to `frontend/src/routes/(app)/jobs/[id]/recipe/+page.svelte` (+ `+page.ts` returning `params.id`; the `svelte/no-navigation-without-resolve` lint rule rejects query strings appended to `resolve()`) and make `frontend/src/lib/components/RecipePreview.svelte` job-aware:
  - take the job id from the route
  - if the stores are empty or `currentJobId` differs, load the job; if it is not `COMPLETED`, redirect to `/jobs/<id>`
  - upload via `api.uploadJobToMealie(jobId)`
  - **Discard** navigates back without deleting anything

**Checkpoint**: The end-to-end flow works asynchronously. Reloading `/jobs/<id>` or `/jobs/<id>/recipe` keeps the state (US1 scenario 4).

---

## Phase 4: User Story 2 – Fortschritt nachvollziehen (Priority: P1)

**Goal**: The job moves through the real stages; the UI shows them within 5 s and offers a way back to running jobs.

**Independent Test**: A video whose description is not enough shows "Fetching description → Transcribing → Extracting → Completed". A video with the recipe in the description skips "Transcribing".

### Tests for User Story 2

- [X] T029 [P] [US2] Create `tests/unit/test_extraction_pipeline.py`. Use `video_agent.override(model=FunctionModel(fn))`, where `fn` scripts the tool calls (`ToolCallPart("get_description", {"input": {"url": …}})`, optionally `get_transcript`, then a `ToolCallPart` for `info.output_tools[0].name` with a minimal valid `RecipeResponse`). Monkeypatch `jarit.tools.video_loader.get_description`/`get_transcript` to return canned responses. Assert the reported stage sequence: `[FETCHING_DESCRIPTION, EXTRACTING]` without transcription, and `[FETCHING_DESCRIPTION, EXTRACTING, TRANSCRIBING, EXTRACTING]` with it.
- [X] T030 [P] [US2] Extend `tests/db/test_job_repository.py`: starting at `FETCHING_DESCRIPTION`, the sequence `EXTRACTING` → `TRANSCRIBING` → `EXTRACTING` is applied step by step, and a later `advance_stage(FETCHING_DESCRIPTION)` returns `False` and leaves the job at `EXTRACTING`. Extend `tests/db/test_extraction_jobs_endpoints.py`: `GET /api/v1/extraction-jobs` returns only your own jobs, newest first, as `ExtractionJobSummary` (no `result`).

### Implementation for User Story 2

- [X] T031 [US2] In `jarit/agents/video_agent.py`, replace the plain tools with async wrappers. They keep the names `get_description(ctx: RunContext[ExtractionDeps], input: VideoUrl)` and `get_transcript(...)`:
  - `get_description`: `await ctx.deps.report(FETCHING_DESCRIPTION)`, then `await asyncio.to_thread(video_loader.get_description, input)`, then `await ctx.deps.report(EXTRACTING)`, then return the result
  - `get_transcript`: the same, with `TRANSCRIBING`

  Keep the docstrings (the model sees them) and `video_loader.py` unchanged.
- [X] T032 [US2] In `jarit/jobs/runner.py`, the runner's `report` callback calls `store.advance(job_id, stage)`. `DbJobStore.advance` uses `advance_stage` (transition table).
- [X] T033 [US2] Add `GET ""` (list) to `jarit/api/v1/endpoints/extraction_jobs.py`, returning `list[ExtractionJobSummary]` from `list_owned_jobs`. Add `listExtractionJobs()` to `frontend/src/lib/api.ts`.
- [X] T034 [US2] Extend `frontend/src/lib/components/JobProgress.svelte` with a step list:
  - steps: Waiting → Fetching video description → Transcribing audio → Extracting recipe; current step highlighted, earlier steps checked
  - "Transcribing audio" marked as skipped only once the job is `COMPLETED` without `TRANSCRIBING` having been seen while polling (it can follow `EXTRACTING`, research R3)
  - elapsed time since `created_at`
  - on a network error, a "Connection problem, retrying…" hint while polling continues
- [X] T035 [US2] Create `frontend/src/lib/components/ActiveJobs.svelte`. It lists your non-terminal jobs from `listExtractionJobs()` with a "View progress" link to `/jobs/<id>`, refreshes every 5 s while any are listed, and renders nothing if there are none. Add it to `frontend/src/routes/(app)/dashboard/+page.svelte` above `RecipeExtractor`.

**Checkpoint**: The stages are visible live, and leaving and returning via the dashboard leads back to a running job.

---

## Phase 5: User Story 3 – Verständliche Fehler und erneuter Versuch (Priority: P2)

**Goal**: Failures carry a fixed, understandable reason, technical details stay in the log, and failed jobs can be retried.

**Independent Test**: An unreachable video → `FAILED`/`VIDEO_UNREACHABLE`, and the response has no technical text. **Try again** sends it back to `QUEUED`.

### Tests for User Story 3

- [X] T036 [P] [US3] Create `tests/unit/test_job_errors.py` for `classify(exc)`, covering every row of research R4: `VideoUnreachableError`, `TranscriptionFailedError`, `TimeoutError`, `pydantic_ai.exceptions.ModelHTTPError`/`UnexpectedModelBehavior`, `openai.APIConnectionError`, `google.genai.errors.APIError`, `httpx.ConnectError` → `LLM_ERROR`, and `ValueError` → `UNKNOWN`.
- [X] T037 [P] [US3] Extend `tests/unit/test_extraction_pipeline.py`: `get_description` raising `yt_dlp.utils.DownloadError` makes `extract` raise `VideoUnreachableError`, and an exception in `get_transcript` makes it raise `TranscriptionFailedError`. Extend `tests/unit/test_extraction_runner.py`: with `timeout=0.05` and a fake `extract` awaiting an unset event → `fail(TIMEOUT)`, and the slot is free again (a second job completes). Each exception class leads to the reason that `classify` gives.
- [X] T038 [P] [US3] Extend `tests/db/test_extraction_jobs_endpoints.py`:
  - `POST /{id}/retry` on a `FAILED` job → `202`, status `QUEUED`, `failure_reason`/`result`/`title` cleared, id resubmitted
  - on `QUEUED`/active/`COMPLETED`, and on a second retry → `409 "Only failed extractions can be retried"`
  - no leak: run the real `ExtractionRunner` with `DbJobStore` and a fake `extract` raising `RuntimeError("SENTINEL-trace /srv/secret")`; after it finishes, `GET /{id}` shows `failure_reason == "UNKNOWN"` and the body has no `SENTINEL`, while `caplog` contains the job id

### Implementation for User Story 3

- [X] T039 [P] [US3] Create `jarit/jobs/errors.py` with `VideoUnreachableError`, `TranscriptionFailedError` and `classify(exc) -> FailureReason` per research R4
- [X] T040 [US3] In the wrappers in `jarit/agents/video_agent.py`, wrap the threaded calls: any exception in `get_description` → `raise VideoUnreachableError() from e`; in `get_transcript` → `raise TranscriptionFailedError() from e`
- [X] T041 [US3] In `jarit/jobs/runner.py`:
  - add `EXTRACTION_TIMEOUT_SECONDS = 600` and a `timeout` constructor parameter that defaults to it
  - wrap each job in `asyncio.timeout(timeout)`
  - map exceptions via `classify` and log with `logger.exception("Extraction job failed", extra={"job_id": …, "reason": …})`
  - add a comment that threads started by the tools cannot be cancelled and that their late result is dropped by the guarded update
- [X] T042 [US3] Add `retry_job(db, job_id)` to `jarit/jobs/repository.py` (`FAILED` → `QUEUED`, clearing `failure_reason`, `result`, `title`). In `jarit/api/v1/endpoints/extraction_jobs.py`, add `POST "/{job_id}/retry"` (`202`, `409` on `False`, then `runner.submit`). Add `retryExtractionJob(id)` to `frontend/src/lib/api.ts`.
- [X] T043 [US3] In `frontend/src/lib/components/JobProgress.svelte`, on `FAILED` show the reason label and a **Try again** button (disabled while the request is in flight). On success, polling resumes on the same page.

**Checkpoint**: Every failure path ends in a labelled `FAILED` state that can be retried.

---

## Phase 6: User Story 4 – Der Host begrenzt die Last (Priority: P2)

**Goal**: At most `N` extractions run at once (default 2), in FIFO order. An invalid value falls back to the default.

**Independent Test**: With `N=1`, three jobs → never more than one active, and they start in submission order. `abc` → a warning, and the limit is 2.

### Tests for User Story 4

- [X] T044 [P] [US4] Create `tests/unit/test_job_settings.py`: unset → 2; `"3"` → 3; `"0"`, `"-1"`, `"abc"`, `"1.5"`, `""` → 2 with a WARNING containing the variable name (`caplog`)
- [X] T045 [P] [US4] Extend `tests/unit/test_extraction_runner.py`:
  - with `limit=2` and 6 jobs whose fake `extract` waits on per-job events, the observed maximum concurrency is exactly 2 and all 6 complete
  - with `limit=1`, the start order equals the submission order, and a job resubmitted later (retry) runs after the jobs already waiting

### Implementation for User Story 4

- [X] T046 [US4] Create `jarit/jobs/settings.py` with `max_concurrent_extractions() -> int`, reading `JARIT_MAX_CONCURRENT_EXTRACTIONS` with the fallback and warning from contracts/operator-config.md. In the `main.py` lifespan, pass its value as `limit` (replacing the hard-coded 2) and log INFO `Extraction concurrency limit: <n>`.
- [X] T047 [P] [US4] Add `JARIT_MAX_CONCURRENT_EXTRACTIONS` with an explanatory comment and the value `2` to `.env_example`. Add `- JARIT_MAX_CONCURRENT_EXTRACTIONS=${JARIT_MAX_CONCURRENT_EXTRACTIONS:-2}` to the backend `environment` in `docker-compose.yml` and `docker-compose.dev.yml`.

**Checkpoint**: The concurrency limit is configurable and enforced.

---

## Phase 7: User Story 5 – Neustart hinterlässt keine hängenden Jobs (Priority: P2)

**Goal**: After a restart, no job remains waiting or active.

**Independent Test**: Insert `QUEUED`/active rows, start the app → they are `FAILED`/`RESTARTED`; completed and failed rows are unchanged.

### Tests for User Story 5

- [X] T048 [P] [US5] Extend `tests/db/test_job_repository.py`: `fail_orphaned_jobs` sets `QUEUED` and all active rows to `FAILED`/`RESTARTED`, returns their count and leaves `COMPLETED`/`FAILED` rows untouched. Add `tests/db/test_startup.py`: insert an active job, enter `with TestClient(main.app):` (runs the lifespan), and the job is `FAILED`/`RESTARTED` before the first request.

### Implementation for User Story 5

- [X] T049 [US5] Add `fail_orphaned_jobs(db) -> int` to `jarit/jobs/repository.py` (one `UPDATE` per research R7). In the `main.py` lifespan, call it via `SessionLocal()` **before** `runner.start()`, and log INFO `Marked <n> interrupted extraction jobs as failed (restart)` when `n > 0`.

**Checkpoint**: Restarts leave a clean state, and the affected jobs can be retried (US3).

---

## Phase 8: User Story 6 – Persönliche Extraktions-Historie (Priority: P2)

**Goal**: Each user sees only their own jobs, with title/URL, time, status and the Mealie flag.

**Independent Test**: User A (3 jobs) and admin B (1 job) each see only their own. Every access to a foreign job by id → 404.

### Tests for User Story 6

- [X] T050 [P] [US6] Add `other_user` and `admin_user` fixtures to `tests/db/conftest.py`, plus a way to switch the `get_current_user` override. In `tests/db/test_extraction_jobs_endpoints.py`, check that for a job owned by `user`, both `other_user` and `admin_user` get the standard 404 on `GET /{id}`, `PUT /{id}/recipe`, `POST /{id}/upload-mealie`, `POST /{id}/retry` and `DELETE /{id}`, and that their `GET ""` does not include it (SC-008).

### Implementation for User Story 6

- [X] T051 [US6] Create `frontend/src/routes/(app)/history/+page.svelte` and `frontend/src/lib/components/JobHistory.svelte`, per contracts/ui-flow.md:
  - rows: title or truncated URL; relative time with the absolute time as a tooltip; status badge; "In Mealie · <date>" badge when `uploaded_to_mealie_at` is set
  - actions: **Open** (`COMPLETED`), **View progress** (non-terminal), reason + **Try again** (`FAILED`)
  - empty state
  - refresh every 5 s while any job is non-terminal
- [X] T052 [P] [US6] Add a "History" link to `/history` in `frontend/src/lib/components/Navigation.svelte`, in both the desktop and the mobile menu

**Checkpoint**: The history is visible and strictly per user.

---

## Phase 9: User Story 7 – Früheres Rezept bearbeiten, hochladen und Einträge löschen (Priority: P2)

**Goal**: Edits are saved to the job, the upload uses the saved version and sets the flag, and finished entries can be deleted.

**Independent Test**: Edit the title, save, reload → the change is still there. The upload sends the edited title and the history shows the badge. Delete → gone, and its id returns 404. Deleting a running job is refused.

### Tests for User Story 7

- [X] T053 [P] [US7] Extend `tests/db/test_extraction_jobs_endpoints.py` and `tests/db/test_job_repository.py`:
  - `PUT /{id}/recipe` → `200`, with `result.recipe` and `title` updated and `suggested_version` unchanged
  - an invalid body → `422` and the stored recipe unchanged
  - a non-`COMPLETED` job → `409`
  - an upload after an edit sends the edited `name` (monkeypatched `push_recipe_to_mealie` captures its argument)
  - `DELETE` on `COMPLETED` and on `FAILED` → `204`, then `GET` → `404`
  - `DELETE` on `QUEUED`/active → `409`
  - `complete_job` after a delete returns `False` without error

### Implementation for User Story 7

- [X] T054 [US7] Add to `jarit/jobs/repository.py`:
  - `save_recipe(db, job_id, recipe: Recipe) -> bool` (`COMPLETED` only; replaces `result["recipe"]`, assigning a new dict so the JSONB change is detected; sets `title`)
  - `delete_finished_job(db, job_id) -> bool` (`DELETE … WHERE status IN terminal`)

  Add to `jarit/api/v1/endpoints/extraction_jobs.py`:
  - `PUT "/{job_id}/recipe"` (body `Recipe`; `409 "Only completed extractions can be edited"`)
  - `DELETE "/{job_id}"` (`204`; `409 "Wait until the extraction has finished before deleting it"`)

  Add `saveJobRecipe(id, recipe)` and `deleteExtractionJob(id)` to `frontend/src/lib/api.ts`.
- [X] T055 [US7] In `frontend/src/lib/components/RecipePreview.svelte`:
  - a **Save** button and a "Saved" / "Unsaved changes" indicator (dirty flag set by the existing edit handlers)
  - **Upload to Mealie** saves first if dirty
  - if `uploaded_to_mealie_at` is set, a confirmation appears before uploading: "This recipe was already uploaded on {date}. Upload again? This creates another copy in Mealie."
  - after a successful upload, update the local job's `uploaded_to_mealie_at`
- [X] T056 [US7] In `frontend/src/lib/components/JobHistory.svelte`, add **Delete** (with confirmation) for `COMPLETED`/`FAILED` rows only. It removes the row on `204` and shows the server message on `409`.

**Checkpoint**: All seven stories work together.

---

## Phase 10: Polish & Cross-Cutting Concerns

- [X] T057 [P] Update `README.md`:
  - extraction is now asynchronous, with progress and history
  - `JARIT_MAX_CONCURRENT_EXTRACTIONS`
  - the backend must run as a single uvicorn worker, and a restart fails running and waiting jobs (they can be retried)
  - migrations run automatically at startup; back up the database before upgrading
  - developer Alembic commands (`uv run alembic upgrade head`, `uv run alembic revision --autogenerate -m "…"`)
- [X] T058 Run the full checks from [quickstart.md](./quickstart.md) §1 and fix any findings:
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - the full test run with coverage (Postgres) — must be ≥ 80 %
  - in `frontend/`: `npm run lint`, `npm run check` and `npm run build`
- [ ] T059 Validate manually with [quickstart.md](./quickstart.md) §2–§7: legacy upgrade, happy path, failure/retry/restart, concurrency, history/edit/upload/delete, isolation
  - *Done on 2026-10-02 against a live backend (uvicorn + Postgres, dummy LLM keys):* submit → `202` in 19 ms; job ran in the background and failed with `LLM_ERROR` without technical details in the response, while the log has the job id; retry `202`, second retry `409`; a foreign user gets `404` and an empty list; old endpoint `404`; restart marked a seeded `QUEUED` and a `TRANSCRIBING` job as `RESTARTED`; `JARIT_MAX_CONCURRENT_EXTRACTIONS=abc` → warning, limit 2. The legacy upgrade is covered by `tests/db/test_migrations.py`.
  - *Open:* a happy path with real LLM/Whisper keys and Mealie, and clicking through the UI in a browser (§3, §6).

---

## Phase 11: Review Follow-ups (spec iteration 4: FR-009c, FR-023a, FR-023b)

**Purpose**: Fix the three code-review findings that were added to the spec as US3 scenario 6 and US7 scenarios 9–10. Design: [research.md R15/R16](./research.md#r15--running-time-after-a-retry-fr-009c-fr-013-fr-004), [data-model.md](./data-model.md), [contracts/http-api.md](./contracts/http-api.md), [contracts/ui-flow.md](./contracts/ui-flow.md).

**Independent Test**: [quickstart.md](./quickstart.md) §8. Backend: the tests below pass, and coverage stays ≥ 80 %.

### Tests for the follow-ups (US3: running time after retry)

- [X] T060 [P] [US3] In `tests/db/test_job_repository.py`:
  - extend `test_retry_only_from_failed_and_clears_state`: before `retry_job`, set the job's `created_at` and `started_at` to one hour ago with a plain `UPDATE`. After the retry, `started_at` is later than the old value and `created_at` is unchanged.
  - new `test_new_job_has_started_at`: `create_job` returns a job whose `started_at` equals `created_at`.
- [X] T061 [P] [US3] In `tests/db/test_extraction_jobs_endpoints.py`:
  - `test_retry_failed_job` also asserts that the response contains `started_at`, that it is later than the backdated value (backdate as in T060), and that `created_at` is unchanged.
  - `GET /extraction-jobs` and `GET /extraction-jobs/{id}` include `started_at`.
- [X] T062 [P] [US3] In `tests/db/test_migrations.py`, add `test_upgrade_from_0002_backfills_started_at(schema_engine)`:
  - `command.upgrade(cfg, "0002_extraction_jobs")`
  - insert a user and a job with a fixed `created_at`
  - run `run_migrations`
  - the job's `started_at` equals its `created_at`, the column is `NOT NULL`, and the revision is `0003_job_started_at`

  Extend `test_downgrade_to_base_and_back` if it asserts the head revision by name.

### Implementation for the follow-ups (US3: running time after retry)

- [X] T063 [US3] Create `jarit/db/migrations/versions/0003_job_started_at.py` (`down_revision = "0002_extraction_jobs"`):
  - upgrade:
    - `op.add_column("extraction_jobs", sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True))`
    - `UPDATE extraction_jobs SET started_at = created_at`
    - `op.alter_column(..., nullable=False, server_default=sa.text("now()"))`
  - downgrade: `op.drop_column("extraction_jobs", "started_at")`
- [X] T064 [US3] Add `started_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))` to `jarit/db/models/extraction_jobs.py`, after `created_at`.
- [X] T065 [US3] Add `started_at: datetime` to `ExtractionJobSummary` in `jarit/jobs/models.py` (inherited by `ExtractionJobDetail`). In `jarit/jobs/repository.py`, `retry_job` additionally sets `started_at=func.now()`; nothing else changes `started_at`.
- [X] T066 [P] [US3] Frontend:
  - `frontend/src/lib/types.ts`: add `started_at: string` to `ExtractionJobSummary`.
  - `frontend/src/lib/components/JobProgress.svelte`: compute "Running for" with `elapsed(job.started_at, now)` instead of `job.created_at`. `JobHistory.svelte` keeps `created_at`.

### Implementation for the follow-ups (US7: editor state per job)

No frontend test runner exists; these tasks are verified by `npm run check` and quickstart §8.

- [X] T067 [US7] Derived unsaved state in `frontend/src/lib/components/RecipePreview.svelte` (FR-023a, R16):
  - remove the `dirty` variable
  - add `$: savedJson = job?.result?.recipe ? JSON.stringify(job.result.recipe) : null` and `$: unsaved = !!recipe && savedJson !== null && JSON.stringify(recipe) !== savedJson`
  - edit handlers keep calling `extractedRecipe.set(...)`. They must trigger reactivity, so call `extractedRecipe.set({ ...updated })` (a new object) in `changed()`.
  - `save()` sets `job` from the `PUT` response, which makes `unsaved` false
  - `handleUpload`: `if (unsaved && !(await save())) return;`
  - indicator and Save button use `unsaved` instead of `dirty`
- [X] T068 [US7] Editor bound only to the URL's job in `frontend/src/lib/components/RecipePreview.svelte` (FR-023b, R16). Same file as T067, so do it after T067.
  - replace `$: recipe = $extractedRecipe` with `$: recipe = job?.id === jobId && $currentJobId === jobId ? $extractedRecipe : null`
  - add `let loadError = ''`. In `onMount`'s `catch`, set it to the error message (`ApiError` 404 → "This extraction does not exist.")
  - template:
    - `{#if recipe}` … editor …
    - `{:else if loadError}` an error box with a link to `resolve('/history')`
    - `{:else}` "Loading…"
  - `save()` and `handleUpload()` return early unless `job?.id === jobId`
  - keep the existing rule in `onMount`: replace the stores only if `$currentJobId !== jobId || !$extractedRecipe`; otherwise keep the edits, which T067 now shows as unsaved

### Checks

- [ ] T069 Run the checks from [quickstart.md](./quickstart.md) §1 again: `uv run ruff check .`, `uv run ruff format --check .`, the full test run with coverage ≥ 80 %, and in `frontend/` `npm run lint`, `npm run check` and `npm run build`. Then validate [quickstart.md](./quickstart.md) §8 manually in a browser.
  - *Done on 2026-10-02:* ruff check and format clean; 138 tests passed, coverage 89.5 %; `npm run lint` clean, `npm run check` 0 errors (the same 15 warnings as before), `npm run build` ok.
  - *Open:* quickstart §8 manually in a browser.

**Checkpoint**: All three review findings are fixed. US3 scenario 6 and US7 scenarios 9–10 pass.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Phase 1 and blocks all user stories. Order inside: T006 → T007 → T008/T009; T010 → T011 → T012 → T013. T014/T015 follow their subjects. T016 can go anywhere in the phase.
- **US1 (Phase 3)**: depends on Phase 2. It is the MVP and the base for the UI the other stories extend.
- **US2–US7**: depend on Phase 2 and US1 (they extend the runner, the endpoint module and the components US1 creates). Among themselves:
  - US2 → US3, because both edit the tool wrappers in `video_agent.py` and `JobProgress.svelte`; do them in this order.
  - US4 and US5 are independent of each other and of US2/US3, apart from the shared `main.py` lifespan and `runner.py` (sequential edits).
  - US6 needs the list endpoint from US2 (T033).
  - US7 needs `JobHistory.svelte` from US6 (T051) for T056; its backend tasks are independent of US6.
- **Polish (Phase 10)**: after all stories.
- **Review follow-ups (Phase 11)**: after Phase 10, because it changes code from US3 and US7. Inside: T060–T062 (tests, parallel) → T063 → T064 → T065; T066 after T065 (API shape); T067 → T068 (same file), independent of the backend chain; T069 last.

### Within Each User Story

Tests first (they should fail), then repository/runner, then endpoints, then frontend.

### Parallel Opportunities

- Phase 1: T002, T003, T004, T005 in parallel after T001.
- Phase 2: T010 in parallel with T006/T007. T014 and T015 in parallel once their subjects exist. T016 any time.
- US1: T017, T018, T019 and T025 in parallel; the backend chain T020 → T021 → T022 → T023 → T024 alongside the frontend chain T026 → T027 → T028.
- US2: T029 and T030 in parallel; T034/T035 (frontend) in parallel with T031/T032 (backend).
- US3: T036, T037, T038 and T039 in parallel.
- US4 and US5 can be done in parallel with each other (T044, T045, T047, T048 are separate files).
- US6: T050 and T052 in parallel with T051.
- US7: T053 in parallel with the start of T054.
- Phase 11: T060, T061 and T062 in parallel; the backend chain T063 → T064 → T065 in parallel with the frontend chain T067 → T068; T066 once T065 is done.

---

## Parallel Example: User Story 1

```bash
# Tests and independent groundwork together:
Task: "Runner unit tests in tests/unit/test_extraction_runner.py"           # T017
Task: "Endpoint tests in tests/db/test_extraction_jobs_endpoints.py"        # T018
Task: "ExtractionDeps in jarit/agents/deps.py + deps_type on video_agent"   # T019
Task: "Frontend types/api/jobs helpers/store"                               # T025

# Then two chains side by side:
Backend:  T020 → T021 → T022 → T023 → T024
Frontend: T026 → T027 → T028
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 + Phase 2. Migrations are the riskiest part; validate T014 against a copy of a real legacy DB if one is available.
2. Phase 3 (US1). The asynchronous flow then replaces the synchronous one end to end.
3. **Stop and validate** with quickstart §1–§3. Because US1 removes the old endpoints, frontend and backend of US1 must ship together.

### Incremental Delivery

1. US1 → US2 (P1, completes the "nicht hängen lassen" goal).
2. US3 → US4 → US5 (robustness).
3. US6 → US7 (history).
4. Polish. One PR against `dev` for the whole feature, or a PR per checkpoint, as long as each one passes CI with coverage ≥ 80 %.

---

## Notes

- `[P]` = different files, no dependency on unfinished tasks.
- Commit after each task or logical group; never commit `.specify/`, `.claude/` or the root `spec.md`.
- Never store exception text in the DB or return it in a response; log it with the job id.
- All state changes go through the guarded `_transition` helpers in `jarit/jobs/repository.py`; no direct status assignments elsewhere.
