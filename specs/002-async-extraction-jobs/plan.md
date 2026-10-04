# Implementation Plan: Asynchrone Rezept-Extraktion mit Statusfeedback und Historie

**Branch**: `feature/002-async-extraction-jobs` (from `dev` at `4773479`) | **Date**: 2026-10-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-async-extraction-jobs/spec.md`

## Summary

Recipe extraction becomes a persisted job. `POST /extraction-jobs` stores a row in a new `extraction_jobs` table and returns `202` with the job at once. An in-process `ExtractionRunner` (FastAPI lifespan, one `asyncio.Queue`, `N` worker tasks, `N = JARIT_MAX_CONCURRENT_EXTRACTIONS`, default 2) runs the existing Pydantic AI agent in the background.

The agent's two tools report their stage through agent deps, so the job moves through `QUEUED → FETCHING_DESCRIPTION → (TRANSCRIBING) → EXTRACTING → COMPLETED/FAILED`. Failures are typed at the source and stored as a fixed reason code; technical details only go to the log. A 600-s timeout, a startup cleanup of orphaned jobs and conditional `UPDATE`s for every transition keep states consistent.

The same table is the user's history: list, open, edit (saved to the job), upload to Mealie from the job (sets `uploaded_to_mealie_at`), retry and delete. Every access is scoped to the owner, and foreign jobs return 404.

Schema changes move from `create_all` to Alembic, run automatically at startup. Existing installations are stamped with a baseline first. CI gains `--cov-fail-under=80`. The current baseline is 81 %.

The frontend polls every 2 s on a new `/jobs/[id]` page, opens the editor on completion as before, and gets a `/history` page. Details: [research.md](./research.md).

**Review follow-ups (spec iteration 4: FR-009c, FR-023a, FR-023b)**:
- A new column `started_at`, added by revision `0003_job_started_at` and reset by retry, drives the "Running for" time on the progress page ([R15](./research.md#r15--running-time-after-a-retry-fr-009c-fr-013-fr-004)).
- The editor derives "unsaved changes" by comparing with the last server version instead of a per-instance flag, so Upload always sends what is shown ([R16](./research.md#r16--editor-state-per-job-fr-023a-fr-023b)).
- The editor renders a form only for the job in the URL, so a previous job's recipe can no longer be shown or saved under another job.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript / Svelte 5 with SvelteKit static adapter (frontend), Node 24

**Primary Dependencies**: FastAPI 0.118, SQLAlchemy 2.0 (sync engine, psycopg2), Pydantic AI 1.0 (`deps_type`, `RunContext`, `FunctionModel` for tests), yt-dlp, OpenAI Whisper API. **New**: `alembic` (runtime dependency).

**Storage**: PostgreSQL. New table `extraction_jobs` (JSONB result) via Alembic revisions `0001_baseline`, `0002_extraction_jobs` and `0003_job_started_at` ([data-model.md](./data-model.md)).

**Testing**: pytest + pytest-asyncio + pytest-cov. Unit tests with fake extractors and `FunctionModel`; DB tests in `tests/db/` against the Postgres service container. `ALLOW_MODEL_REQUESTS = False` globally.

**Target Platform**: Linux containers (Docker Compose), single uvicorn worker; GitHub-hosted runners for CI

**Project Type**: Web application (FastAPI backend in `jarit/` + `main.py`, SvelteKit frontend in `frontend/`)

**Performance Goals**: Submit responds in < 2 s, p95 (SC-001), in practice one INSERT. Stage changes are visible within 5 s (SC-002) via 2-s polling. Polling costs one indexed primary-key SELECT per open progress page every 2 s.

**Constraints**:
- No extra infrastructure: no Redis, broker or worker container (FR-002).
- Exactly one backend process.
- No technical details in API responses (FR-011).
- Tests run without LLM, Whisper or network (FR-029).
- Coverage ≥ 80 % in CI (FR-027).
- Existing data survives the switch to migrations (SC-007).

**Scale/Scope**: A self-hosted instance with a handful of users, tens to a few thousand jobs in total, and at most `N` (default 2) extractions running at once.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, so there are no ratified principles to check. **PASS (vacuous).** Run `/speckit-constitution` to define project principles.

The plan follows the conventions established in feature 001:
- flat `jarit/` package
- FastAPI dependencies for auth
- DB tests in `tests/db/`
- no secrets in logs or responses
- CI without repository secrets

*Post-design re-check (after Phase 1, incl. review follow-ups):* still no constitution. The design adds one runtime dependency (Alembic, which the spec requires), no new service, and one nullable-then-backfilled column. **PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/002-async-extraction-jobs/
├── spec.md
├── plan.md              # this file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── http-api.md
│   ├── ui-flow.md
│   ├── operator-config.md
│   └── ci-checks.md
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
main.py                                   # MODIFY: run_migrations() replaces create_all; lifespan (orphan cleanup, runner start/stop)
alembic.ini                               # NEW: CLI config; script_location = jarit/db/migrations
jarit/
├── db/
│   ├── migrate.py                        # NEW: run_migrations(engine): stamp baseline for legacy DBs, upgrade head
│   ├── migrations/
│   │   ├── env.py                        # NEW: DATABASE_URL, Base.metadata, shared connection via cfg.attributes
│   │   ├── script.py.mako                # NEW
│   │   └── versions/
│   │       ├── 0001_baseline.py          # NEW: users (+ user_role_enum), api_keys as today
│   │       ├── 0002_extraction_jobs.py   # NEW: extraction_jobs + indexes + check constraints
│   │       └── 0003_job_started_at.py    # NEW (review follow-up): started_at, backfilled from created_at
│   └── models/
│       ├── __init__.py                   # MODIFY: import all models so Base.metadata is complete
│       └── extraction_jobs.py            # NEW: ExtractionJob ORM model (+ started_at)
├── jobs/                                 # NEW package
│   ├── __init__.py
│   ├── models.py                         # JobStatus, FailureReason, ACTIVE/TERMINAL sets, API schemas (Summary/Detail/Create; + started_at)
│   ├── errors.py                         # VideoUnreachableError, TranscriptionFailedError, classify(exc) -> FailureReason
│   ├── repository.py                     # create, get_owned, list_owned, conditional transitions, fail_orphaned_jobs; retry_job resets started_at
│   ├── runner.py                         # ExtractionRunner: queue, workers, timeout, submit() thread-safe
│   ├── pipeline.py                       # extract(job, report): runs video_agent with ExtractionDeps
│   └── settings.py                       # max_concurrent_extractions() with fallback + warning
├── agents/video_agent.py                 # MODIFY: deps_type=ExtractionDeps; async tool wrappers with stage reporting + error typing
├── tools/video_loader.py                 # unchanged (wrapped, called via asyncio.to_thread)
├── core/recipe_service.py                # DELETE (replaced by jobs/pipeline.py)
├── api/
│   ├── router.py                         # MODIFY: mount extraction_jobs, drop recipes
│   └── v1/endpoints/
│       ├── extraction_jobs.py            # NEW: endpoints per contracts/http-api.md
│       ├── recipes.py                    # DELETE
│       └── integrations.py               # MODIFY: drop POST /upload-mealie; keep get_mealie_credentials + verify
└── models/input_models/video.py          # MODIFY: target_language length/blank validation

tests/
├── conftest.py                           # MODIFY: ALLOW_MODEL_REQUESTS = False
├── unit/
│   ├── test_extraction_runner.py         # NEW
│   ├── test_extraction_pipeline.py       # NEW (FunctionModel)
│   └── test_job_settings.py              # NEW
└── db/
    ├── conftest.py                       # MODIFY: run_migrations instead of create_all; truncate extraction_jobs; second_user/admin fixtures; runner fake
    ├── test_job_repository.py            # NEW
    ├── test_extraction_jobs_endpoints.py # NEW
    ├── test_migrations.py                # NEW (separate schema, see Risks)
    └── test_api_keys_endpoints.py        # MODIFY: upload tests move to job endpoint

.github/workflows/ci.yml                  # MODIFY: coverage gate (contracts/ci-checks.md)
pyproject.toml / uv.lock                  # MODIFY: + alembic
docker-compose.yml, docker-compose.dev.yml# MODIFY: JARIT_MAX_CONCURRENT_EXTRACTIONS
.env_example                              # MODIFY: new variable with comment
README.md                                 # MODIFY: async jobs, history, concurrency var, single worker, automatic migrations, dev Alembic commands

frontend/src/
├── lib/
│   ├── types.ts                          # MODIFY: job types (+ started_at)
│   ├── api.ts                            # MODIFY: job client functions; remove extractRecipe/uploadToMealie
│   ├── jobs.ts                           # NEW: labels, isTerminal, pollJob
│   ├── store.ts                          # MODIFY: currentJobId
│   └── components/
│       ├── RecipeExtractor.svelte        # MODIFY: submit job → /jobs/{id}
│       ├── RecipePreview.svelte          # MODIFY: load by job, save, upload via job, re-upload confirm; derived unsaved state, render only for the URL's job (R16)
│       ├── JobProgress.svelte            # NEW; running time from started_at (R15)
│       ├── JobHistory.svelte             # NEW
│       ├── ActiveJobs.svelte             # NEW (dashboard)
│       └── Navigation.svelte             # MODIFY: History link
└── routes/
    ├── (app)/dashboard/+page.svelte      # MODIFY: ActiveJobs
    ├── (app)/jobs/[id]/+page.svelte      # NEW
    ├── (app)/history/+page.svelte        # NEW
    ├── (app)/jobs/[id]/recipe/+page.svelte # MOVED from recipe-preview/: editor for one job (load from params)
    └── recipe-preview/                   # REMOVED
```

**Structure Decision**: Keep the single-backend layout. Job logic gets its own `jarit/jobs/` package: models, repository, runner and pipeline. That keeps the HTTP layer thin and makes the runner testable without FastAPI. Migrations live inside the package (`jarit/db/migrations/`), so `run_migrations` finds them in the container and in tests without depending on the working directory. The frontend follows the existing component and route pattern.

## Implementation Order

1. **Migrations first**: add Alembic, `0001_baseline`, `run_migrations` with the legacy stamp, and switch `main.py` and `tests/db/conftest.py` over. Prove it with `test_migrations.py` before anything else depends on it.
2. **Data layer**: `0002_extraction_jobs`, ORM model, `jobs/models.py`, `repository.py` with conditional transitions and `fail_orphaned_jobs` + tests.
3. **Runner**: `settings.py`, `runner.py` with an injected extractor, lifespan wiring, and unit tests (limit, FIFO, timeout, mapping).
4. **Pipeline**: agent deps, tool wrappers, `errors.py`, `pipeline.py`, plus `FunctionModel` tests. Delete `recipe_service.py`.
5. **API**: `extraction_jobs.py`; remove `recipes.py` and `POST /integrations/upload-mealie`; endpoint tests including isolation and the no-leak check.
6. **CI gate**: coverage flag in `ci.yml` (from here on every push is gated).
7. **Frontend**: types/api/jobs helpers, `RecipeExtractor` → `/jobs/[id]` + `JobProgress`, editor changes, `/history`, `ActiveJobs`, navigation.
8. **Docs/config**: `.env_example`, compose files, README.
9. **Review follow-ups** (spec iteration 4):
   - Backend: `0003_job_started_at`, the ORM column, `started_at` in the schemas, and `retry_job` resetting it. Tests in `test_job_repository.py`, `test_extraction_jobs_endpoints.py` and `test_migrations.py` (upgrade from `0002` backfills the column).
   - Frontend: `types.ts`, `JobProgress` (elapsed from `started_at`), and `RecipePreview` (derived unsaved state, editor bound only to the URL's job, guarded save/upload). There is no frontend test runner, so these are checked with `npm run check` and quickstart §8.

Steps 1 to 6 are backend-only and can be merged behind the old UI only if the old endpoints stay. Because they are removed in step 5, steps 5 and 7 must land in the same PR.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Legacy DB drifted from current models, so the baseline stamp hides the difference | Same behavior as today's `create_all`. Documented in research R6. Backup advice in the README. |
| A thread (yt-dlp/Whisper) keeps running after the timeout | Slot is freed anyway; the result is dropped by the conditional update. Documented in code (R5). |
| `tests/db` truncation vs. migrations | Run migrations once per session; truncate `users, api_keys, extraction_jobs`. `test_migrations.py` uses its own Postgres schema (`SET search_path`), created and dropped in the test, so it never touches the shared one. |
| Someone runs uvicorn with `--workers > 1` | README warning. The startup cleanup in a second worker would fail the other worker's jobs, so this is called out explicitly. |
| `0002` already applied on development databases of this branch | `started_at` goes into a new revision `0003` instead of editing `0002`, which Alembic would skip there (R15). |
| Comparing recipes via `JSON.stringify` reports a false "unsaved" if key order differs | Both sides come from the same server JSON and are edited in place, so key order is preserved. A false positive only causes an extra, harmless save before upload. |
| Coverage drops below 80 % with large new modules | The test inventory in contracts/ci-checks.md is part of the definition of done. Frontend code is not counted (backend-only gate). |

## Complexity Tracking

No constitution violations to justify.
