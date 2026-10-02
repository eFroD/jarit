# Contract: Host configuration and upgrade

## New environment variable

| Variable | Default | Valid values | Invalid value |
|---|---|---|---|
| `JARIT_MAX_CONCURRENT_EXTRACTIONS` | `2` | integer ≥ 1 | Falls back to `2`, logs `WARNING: JARIT_MAX_CONCURRENT_EXTRACTIONS=<value> is not an integer >= 1; using 2` (the value is not a secret, so it may be logged) |

It is read once at startup. Changing it needs a restart.

Must be added to:

- `.env_example`: commented, e.g. `# Maximum number of recipe extractions running at the same time. Further jobs wait.` / `JARIT_MAX_CONCURRENT_EXTRACTIONS=2`
- `docker-compose.yml` and `docker-compose.dev.yml`: `- JARIT_MAX_CONCURRENT_EXTRACTIONS=${JARIT_MAX_CONCURRENT_EXTRACTIONS:-2}` (the compose files pass variables explicitly, see feature 001 R4).
- README configuration section.

## Single backend process

Jobs run inside the backend process, so the backend must run as **one** uvicorn worker (current default; the compose command has no `--workers`). The README states this, and that a restart fails running and waiting jobs (users can retry them).

## Database migrations

- Migrations run automatically at backend startup, before requests are accepted. Hosts do nothing beyond pulling the new image and restarting.
- Upgrading an existing installation (tables created by the old `create_all`): the backend detects the missing `alembic_version` table, stamps the baseline and applies the new revisions. Users and integration credentials are kept (SC-007).
- Startup log lines (INFO): `Database schema at revision <rev>`; on upgrade also `Upgrading database schema from <old> to <new>`.
- A failed migration aborts startup with the Alembic error in the log (no partial start).
- Developer CLI (documented in README, not needed by hosts): `uv run alembic upgrade head`, `uv run alembic revision --autogenerate -m "…"`, using `alembic.ini` in the repo root and `DATABASE_URL` from the environment.
- Backup recommendation in the README before upgrading, as for any schema change.

## Startup order (`main.py` / lifespan)

1. `require_encryption_key()` (unchanged, first).
2. `run_migrations(engine)`, replacing `Base.metadata.create_all`.
3. `migrate_plaintext_secrets()` (unchanged).
4. Lifespan startup: `fail_orphaned_jobs()` (logs count), then `ExtractionRunner.start(limit)`.
5. Requests are served.

On shutdown the lifespan cancels the worker tasks. Jobs interrupted this way are cleaned up by step 4 on the next start.
