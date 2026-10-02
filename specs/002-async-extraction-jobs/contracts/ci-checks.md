# Contract: CI checks (delta to feature 001)

Workflow: `.github/workflows/ci.yml`, trigger unchanged (pull requests against `dev` and `main`).

## Changed step

`backend` → **Tests**:

```yaml
- name: Tests
  run: uv run pytest -q --cov=jarit --cov=main --cov-report=term-missing --cov-fail-under=80
```

- The job fails if total backend line coverage is below 80 % (FR-027). The coverage table shows in the job log.
- Baseline before this feature: 81 % ([research R14](../research.md#r14--coverage-gate-fr-027)). New code must bring its own tests so the total does not drop.

## Unchanged guarantees

- No repository secrets, no real credentials (feature 001, FR-022).
- `tests/integration` and `tests/model_eval` stay excluded (`tests/conftest.py`).
- All new tests run without a real LLM, without Whisper and without outbound network (FR-029). `pydantic_ai.models.ALLOW_MODEL_REQUESTS = False` makes an accidental real model call fail the test instead of reaching a provider.
- The frontend job (lint, `svelte-check`, build) covers the new routes and components.

## Test inventory required by FR-028

| Area | Location |
|---|---|
| Runner: queue, concurrency limit, FIFO, timeout, failure mapping | `tests/unit/test_extraction_runner.py` |
| Stage reporting with and without transcription; tool exception translation | `tests/unit/test_extraction_pipeline.py` (`FunctionModel`) |
| Concurrency setting parsing | `tests/unit/test_job_settings.py` |
| Restart cleanup, conditional transitions | `tests/db/test_job_repository.py` |
| Endpoints: submit, get, list, edit, upload flag, retry (resets `started_at`, keeps `created_at`), delete, foreign/admin access → 404 | `tests/db/test_extraction_jobs_endpoints.py` |
| Migrations: empty DB and legacy `create_all` DB with data; upgrade from `0002` backfills `started_at` | `tests/db/test_migrations.py` |
| No technical detail in job responses | `tests/db/test_extraction_jobs_endpoints.py` (sentinel exception text must not appear) |
