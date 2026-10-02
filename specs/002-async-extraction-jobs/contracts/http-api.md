# Contract: HTTP API

Base path `/api/v1`. Every endpoint requires a bearer token (`Depends(get_current_user)` on the router, as for `/recipes` today). The frontend is the only client (spec assumption), so removed endpoints have no deprecation phase.

## Removed

| Endpoint | Replacement |
|---|---|
| `POST /recipes/extract-recipe` | `POST /extraction-jobs` + polling (FR-026) |
| `POST /integrations/upload-mealie` | `POST /extraction-jobs/{id}/upload-mealie` ([research R10](../research.md#r10--mealie-upload-from-a-job-fr-022-fr-024)) |

`GET /integrations/verify-mealie-user` stays unchanged.

## Shared shapes

```jsonc
// JobStatus
"QUEUED" | "FETCHING_DESCRIPTION" | "TRANSCRIBING" | "EXTRACTING" | "COMPLETED" | "FAILED"

// FailureReason
"VIDEO_UNREACHABLE" | "NO_RECIPE_FOUND" | "TRANSCRIPTION_FAILED" | "LLM_ERROR"
| "TIMEOUT" | "RESTARTED" | "UNKNOWN"

// ExtractionJobSummary (list item)
{
  "id": "6f1c…-uuid",
  "video_url": "https://www.instagram.com/reel/…",
  "target_language": "german",
  "title": "Shakshuka" | null,          // null until COMPLETED
  "status": "COMPLETED",
  "failure_reason": null,               // set iff status == FAILED
  "created_at": "2026-10-02T10:15:00Z",
  "updated_at": "2026-10-02T10:15:41Z",
  "uploaded_to_mealie_at": "2026-10-02T10:20:03Z" | null
}

// ExtractionJob (detail) = ExtractionJobSummary + 
{
  "result": {                           // null unless COMPLETED
    "recipe": Recipe,                   // latest saved version
    "suggested_version": Recipe | null,
    "error_info": { "error": "", "missing_fields": [] }
  } | null
}
```

`Recipe` is the existing schema.org model (`jarit/models/output_models/recipe.py`), serialized with aliases (`@context`, `@type`), the same as the old extract response.

**Never in a response**: stack traces, third-party error text, file paths, credentials (FR-011).

## Endpoints

### `POST /extraction-jobs` — submit (FR-001)

Request: `{ "url": "https://…", "target_language": "english" }` (same body as the old `VideoRequest`; `target_language` defaults to `"english"`).

| Status | When | Body |
|---|---|---|
| `202` | job created and queued | `ExtractionJob` (status `QUEUED`) |
| `422` | invalid URL, empty or too long `target_language` | FastAPI validation error; no job created |

The response returns before any extraction work starts (SC-001: < 2 s).

### `GET /extraction-jobs` — history (FR-021)

All jobs of the current user, `created_at` descending. No pagination (spec assumption).

| Status | Body |
|---|---|
| `200` | `ExtractionJobSummary[]` (may be empty) |

### `GET /extraction-jobs/{id}` — status and result (FR-004, FR-005)

| Status | When | Body |
|---|---|---|
| `200` | own job | `ExtractionJob` |
| `404` | unknown id, malformed id, or another user's job | `{"detail": "Extraction job not found"}` |

This endpoint is what the frontend polls every 2 s.

### `PUT /extraction-jobs/{id}/recipe` — save an edit (FR-023)

Request: a `Recipe`.

| Status | When | Body |
|---|---|---|
| `200` | own job, status `COMPLETED` | `ExtractionJob` with the new `result.recipe` and `title` |
| `404` | as above | as above |
| `409` | job is not `COMPLETED` | `{"detail": "Only completed extractions can be edited"}` |
| `422` | body is not a valid `Recipe` | validation error; stored version unchanged |

### `POST /extraction-jobs/{id}/upload-mealie` — upload stored recipe (FR-022, FR-024)

No body. Uploads `result.recipe` as stored.

| Status | When | Body |
|---|---|---|
| `200` | Mealie accepted it | `{"message": "Recipe pushed to Mealie successfully.", "uploaded_to_mealie_at": "<ts>"}` |
| `404` | job not found / foreign; **or** no Mealie credentials (unchanged message from `get_mealie_credentials`) | `{"detail": …}` |
| `409` | job not `COMPLETED`; **or** credentials unreadable (unchanged from feature 001) | `{"detail": …}` |
| `400` | Mealie base URL missing (unchanged) | `{"detail": …}` |
| Mealie's status | Mealie returned an HTTP error (unchanged passthrough) | `{"detail": "Mealie error: …"}` |

`uploaded_to_mealie_at` is set only on `200`. A failed upload leaves it unchanged. Re-uploading is allowed; the UI shows a warning first (FR-024).

### `POST /extraction-jobs/{id}/retry` — restart a failed job (FR-013, FR-014)

No body.

| Status | When | Body |
|---|---|---|
| `202` | own job was `FAILED` | `ExtractionJob` (status `QUEUED`, `failure_reason`/`result`/`title` cleared) |
| `404` | as above | as above |
| `409` | job is not `FAILED` (including a second click) | `{"detail": "Only failed extractions can be retried"}` |

### `DELETE /extraction-jobs/{id}` — remove from history (FR-025)

| Status | When | Body |
|---|---|---|
| `204` | own job in `COMPLETED` or `FAILED`, now deleted | — |
| `404` | as above | as above |
| `409` | job is `QUEUED` or active | `{"detail": "Wait until the extraction has finished before deleting it"}` |

Deleting does not touch Mealie.

## Router wiring

`jarit/api/v1/endpoints/extraction_jobs.py`, mounted in `jarit/api/router.py` with `prefix="/extraction-jobs"`, `tags=["extraction-jobs"]`, `dependencies=[Depends(get_current_user)]`. The `recipes` router and its module are removed.
