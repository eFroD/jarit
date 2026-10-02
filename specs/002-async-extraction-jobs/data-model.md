# Data Model: Extraction Jobs

Phase 1 of [plan.md](./plan.md). Introduced by Alembic revision `0002_extraction_jobs`; `started_at` is added by `0003_job_started_at` ([research.md R15](./research.md#r15--running-time-after-a-retry-fr-009c-fr-013-fr-004)). Revision `0001_baseline` only formalizes the existing `users` and `api_keys` tables and changes nothing in them.

## Table `extraction_jobs`

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `UUID` | no | app-side `uuid4()` | Primary key. Non-guessable, exposed in URLs. |
| `user_id` | `INTEGER` | no | — | FK → `users.id` `ON DELETE CASCADE`. Owner (FR-003). |
| `video_url` | `TEXT` | no | — | As submitted, after `HttpUrl` validation. |
| `target_language` | `VARCHAR(64)` | no | — | As submitted (today free text, default `"english"`). |
| `status` | `VARCHAR(32)` | no | `'QUEUED'` | `CHECK` in the `JobStatus` set below. |
| `failure_reason` | `VARCHAR(32)` | yes | `NULL` | `CHECK` in the `FailureReason` set below. Set if and only if `status = 'FAILED'`. |
| `title` | `TEXT` | yes | `NULL` | `result.recipe.name`, kept in sync on completion and on every edit. History shows `video_url` if `NULL`. |
| `result` | `JSONB` | yes | `NULL` | Serialized `RecipeResponse` (`recipe`, `suggested_version`, `error_info`). Set if and only if `status = 'COMPLETED'`. |
| `uploaded_to_mealie_at` | `TIMESTAMPTZ` | yes | `NULL` | Last successful Mealie upload (FR-024). |
| `created_at` | `TIMESTAMPTZ` | no | `now()` | Submission time; history sort key. Never changes. |
| `started_at` | `TIMESTAMPTZ` | no | `now()` | Start of the current run: submission, or the last retry. The progress page measures "Running for" from here (FR-009c). Backfilled from `created_at` by `0003`. |
| `updated_at` | `TIMESTAMPTZ` | no | `now()` | Last change of any kind; set explicitly on every update. |

Indexes:

- `ix_extraction_jobs_user_created` on `(user_id, created_at DESC)`. Used by the history list and the ownership lookup.
- `ix_extraction_jobs_active` partial index on `(status) WHERE status IN ('QUEUED','FETCHING_DESCRIPTION','TRANSCRIBING','EXTRACTING')`. Used by the startup cleanup; small by construction.

Constraints:

- `ck_extraction_jobs_status`, `ck_extraction_jobs_failure_reason`: value sets.
- `ck_extraction_jobs_failure_consistency`: `(status = 'FAILED') = (failure_reason IS NOT NULL)`.

Plain `VARCHAR` + `CHECK` instead of a PostgreSQL `ENUM`, so a new stage or reason later only needs a constraint swap and no `ALTER TYPE` (which cannot run inside a transaction on older Postgres versions).

ORM model: `jarit/db/models/extraction_jobs.py`, class `ExtractionJob`. No back-reference on `User`; deletion relies on the DB cascade, so `db.delete(user)` in the admin endpoint keeps working without loading jobs.

## Enumerations (`jarit/jobs/models.py`)

### `JobStatus`

| Value | Spec stage | Kind |
|---|---|---|
| `QUEUED` | wartend | waiting |
| `FETCHING_DESCRIPTION` | Videobeschreibung wird geladen | active |
| `TRANSCRIBING` | Audio wird transkribiert | active |
| `EXTRACTING` | Rezept wird extrahiert | active |
| `COMPLETED` | abgeschlossen | terminal |
| `FAILED` | fehlgeschlagen | terminal |

### `FailureReason`

| Value | Spec wording | UI label (English UI) | Source |
|---|---|---|---|
| `VIDEO_UNREACHABLE` | Video nicht erreichbar | Video unreachable | description tool |
| `NO_RECIPE_FOUND` | Kein Rezept im Video gefunden | No recipe found in this video | `output.recipe is None` |
| `TRANSCRIPTION_FAILED` | Transkription fehlgeschlagen | Transcription failed | transcript tool |
| `LLM_ERROR` | Fehler beim Sprachmodell | Language model error | model/provider errors |
| `TIMEOUT` | Zeitüberschreitung | Timed out | 600-s job timeout |
| `RESTARTED` | Abgebrochen durch Neustart der Anwendung | Interrupted by an application restart | startup cleanup |
| `UNKNOWN` | Unbekannter Fehler, bitte erneut versuchen | Unknown error, please try again | everything else |

The mapping from exceptions is in [research.md R4](./research.md#r4--mapping-failures-to-user-facing-reasons-fr-010-fr-011).

## State transitions

```text
 submit ──▶ QUEUED ──▶ FETCHING_DESCRIPTION ──┬──────────────────────▶ EXTRACTING ──▶ COMPLETED
              ▲                               │                           ▲
              │                               └──▶ TRANSCRIBING ──────────┘
              │                                    (only if needed)
              │
              │   QUEUED or any active stage ──(error · no recipe · timeout · restart)──▶ FAILED
              │                                                                            │
              └──────────────────────────────── retry ─────────────────────────────────────┘
```

`COMPLETED` is final: it is never re-extracted, only edited, uploaded or deleted.

| From | To | Trigger | Guard (conditional `UPDATE … WHERE status IN …`) |
|---|---|---|---|
| — | `QUEUED` | `POST /extraction-jobs` | — (insert) |
| `QUEUED` | `FETCHING_DESCRIPTION` | worker starts the job | `status = 'QUEUED'` |
| `FETCHING_DESCRIPTION`/`EXTRACTING` | `TRANSCRIBING` | transcript tool starts | `status IN (FETCHING_DESCRIPTION, EXTRACTING)` |
| `FETCHING_DESCRIPTION`/`TRANSCRIBING` | `EXTRACTING` | a tool returned | `status IN (FETCHING_DESCRIPTION, TRANSCRIBING)` |
| active | `COMPLETED` | run returns a recipe | `status IN active` |
| `QUEUED`/active | `FAILED` | error, timeout, no recipe | `status IN (QUEUED, active)` |
| `QUEUED`/active | `FAILED` (`RESTARTED`) | startup cleanup | same |
| `FAILED` | `QUEUED` | `POST …/retry` | `status = 'FAILED'`; clears `failure_reason`, `result`, `title`; sets `started_at = now()` |
| `COMPLETED`/`FAILED` | (deleted) | `DELETE …` | `status IN terminal` |
| `COMPLETED` | `COMPLETED` | `PUT …/recipe`, upload success | `status = 'COMPLETED'` |

A worker write that matches 0 rows (job deleted or already failed) is dropped without error.

## Validation rules

- `video_url`: `pydantic.HttpUrl` (same as today's `VideoRequest`). Invalid → 422, no row (spec edge case).
- `target_language`: non-empty after `strip()`, at most 64 characters. Invalid → 422.
- Edited recipe (`PUT …/recipe`): must validate as `jarit.models.output_models.recipe.Recipe`. Invalid → 422, stored version unchanged.

## Relationship to existing entities

- `users` 1 — n `extraction_jobs` (cascade delete).
- `api_keys` is unchanged. It is only read through `get_mealie_credentials` during an upload.
