# Quickstart: validating asynchronous extraction jobs

Run guide for checking the feature end to end. Shapes and status codes are in [contracts/http-api.md](./contracts/http-api.md), states in [data-model.md](./data-model.md).

## Prerequisites

- `.env` from `.env_example` with a valid `JARIT_ENCRYPTION_KEY` and working LLM/OpenAI keys (only for the manual end-to-end part).
- Docker, `uv`, Node 24.

## 1. Automated checks (no LLM, no network)

```bash
# Throwaway Postgres for tests/db (name must end in _test)
docker run -d --rm --name jarit-test-pg -e POSTGRES_USER=jarit -e POSTGRES_PASSWORD=jarit \
  -e POSTGRES_DB=jarit_test -p 55432:5432 postgres:16

DATABASE_URL=postgresql://jarit:jarit@localhost:55432/jarit_test \
  uv run pytest -q --cov=jarit --cov=main --cov-report=term-missing --cov-fail-under=80

uv run ruff check . && uv run ruff format --check .
(cd frontend && npm ci && npm run lint && npm run check && npm run build)

docker stop jarit-test-pg
```

Expected: all tests pass, coverage ≥ 80 %, the inventory in [contracts/ci-checks.md](./contracts/ci-checks.md) is present.

## 2. Upgrade of an existing installation (SC-007)

1. Check out `dev` before this feature and start the dev stack (`docker compose -f docker-compose.dev.yml up`). Register a user and store Mealie credentials.
2. Switch to the feature branch and restart the backend.
3. Expected log: `Upgrading database schema …` and `Database schema at revision 0003_job_started_at`.
4. Check: `docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c 'select version_num from alembic_version; select count(*) from users; select count(*) from api_keys;'`. The revision is `0003_…` and the counts are unchanged. Logging in and verifying Mealie still work.

## 3. Happy path with progress (Stories 1 and 2)

1. Submit a recipe video URL on the dashboard. The page switches to `/jobs/<id>` in under 2 s (SC-001).
2. Watch the steps advance. For a video whose description already holds the recipe, "Transcribing audio" is shown as skipped. For a video without a description recipe it is shown (SC-002: every change visible within 5 s).
3. On completion the editor opens with the recipe, as before.
4. While a job runs, reload the page, or go to the dashboard and back via "in progress". The job and then the result are still there (SC-003).

## 4. Failure, retry and restart (Stories 3 and 5)

- Submit `https://www.youtube.com/watch?v=xxxxxxxxxxx` (non-existent). Expected: `FAILED` with "Video unreachable"; the UI and `GET /extraction-jobs/<id>` show no stack trace; the backend log has the yt-dlp error with the job id.
- Click **Try again**. The job goes back to waiting and runs again (and fails again here).
- Submit a valid URL and restart the backend while it runs (`docker compose restart backend`). Expected: the job is `FAILED` with "Interrupted by an application restart"; retry works (SC-006).

## 5. Concurrency limit (Story 4)

1. Set `JARIT_MAX_CONCURRENT_EXTRACTIONS=1`, restart, and submit three URLs quickly.
2. `GET /api/v1/extraction-jobs` at the same time: at most one job is in an active stage, the others are `QUEUED` and start in submission order (SC-005).
3. Set it to `abc`, restart. Expected: a warning in the log, and the limit is 2.

## 6. History, editing, upload, delete (Stories 6 and 7)

1. Open **History**: all own jobs, newest first, titles for completed ones, URLs otherwise.
2. Open a completed job, change the title, **Save**, reload. The change is still there; the history shows the new title (SC-009).
3. **Upload to Mealie**. The recipe in Mealie has the edited title; the history shows the "In Mealie" badge (SC-010). Upload again: the confirmation dialog appears.
4. Delete a completed job. It disappears; `GET /extraction-jobs/<id>` → 404. Try to delete a running job → refused.

## 7. Isolation (SC-008)

Log in as a second user and as an admin: `/history` shows only their own jobs, and `GET/PUT/POST/DELETE` on a job id of the first user all return `404 Extraction job not found`.

## 8. Review follow-ups (FR-009c, FR-023a, FR-023b)

1. **Unsaved edits after back navigation**: open a completed job, change the title, do **not** save, click **← Back**, then reopen the job from the history. Expected: the changed title is shown with "Unsaved changes", and **Save** is enabled. Click **Upload to Mealie**: the recipe in Mealie has the changed title, and reopening the job after a reload still shows it (SC-012).
2. **Failed load does not show another job**: open job A in the editor. Then open `/jobs/<id of a deleted or foreign job>/recipe` (or block the API in the browser dev tools and open job B). Expected: an error with a link to the history; neither A's recipe nor any form is shown, and nothing is sent to `PUT …/recipe`.
3. **Running time after retry**: retry a job that failed some minutes ago. Expected: "Running for" starts again at 0 s; the history still shows the original submission time. `GET /extraction-jobs/<id>` returns a `started_at` later than `created_at` (SC-013).
4. **Upgrade from `0002`**: on a database already at `0002_extraction_jobs`, restart the backend. Expected log: upgrade to `0003_job_started_at`; existing jobs have `started_at = created_at`.
