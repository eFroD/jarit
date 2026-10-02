# Quickstart: Validate encrypted integration keys and PR CI

Contracts: [http-api](./contracts/http-api.md) · [operator-config](./contracts/operator-config.md) · [ci-checks](./contracts/ci-checks.md) · Data model: [data-model.md](./data-model.md)

## Prerequisites

- Docker with Compose, `uv`, Node 24.
- A local stack: `docker compose -f docker-compose.dev.yml up -d postgres`.
- `psql` access to the dev DB (`docker compose -f docker-compose.dev.yml exec postgres psql -U devuser devdb`).

## 1. Automated checks (same as CI)

```sh
uv sync --locked
uv run ruff check . && uv run ruff format --check .
docker run -d --rm --name jarit-test-pg -e POSTGRES_USER=jarit -e POSTGRES_PASSWORD=jarit -e POSTGRES_DB=jarit_test -p 127.0.0.1:55432:5432 postgres:16
DATABASE_URL=postgresql://jarit:jarit@localhost:55432/jarit_test uv run pytest   # tests/db only runs against a *_test database
cd frontend && npm ci && npm run lint && npm run check && npm run build
```

**Expected**: everything passes. `uv sync` finishes in about a minute, because the heavy eval packages moved to the `eval` group.

## 2. Startup refuses to run without a valid key (Story 2, SC-002)

```sh
unset JARIT_ENCRYPTION_KEY; uv run uvicorn main:app          # → exit code 1, block on stderr, line "JARIT_ENCRYPTION_KEY=…"
JARIT_ENCRYPTION_KEY=CHANGEME uv run uvicorn main:app        # → "is invalid", the value CHANGEME is NOT printed
```

Run the first command twice. **Expected**: the suggested keys are different.

Copy the suggested line into `.env` and start again. **Expected**: the server starts.

## 3. Stored values are ciphertext (Story 1, SC-001)

1. Log in through the UI and save Mealie credentials with a recognisable key, e.g. `test-sentinel-123`.
2. `SELECT api_key FROM api_keys;` → **Expected**: the value starts with `enc:v1:` and does not contain `test-sentinel-123`.
3. Run `GET /api/v1/users/me/api-keys`. **Expected**: there is no `api_key` field in the response.
4. Upload a recipe to a real or mocked Mealie. **Expected**: the upload succeeds.

## 4. Legacy migration (Story 3, SC-003)

1. Stop the backend. `UPDATE api_keys SET api_key='legacy-plain-key' WHERE service_name='mealie';`
2. Start the backend. **Expected**: one INFO line "Encrypted 1 legacy plaintext …". `SELECT` shows `enc:v1:…`.
3. Repeat step 1, then hit `GET /integrations/verify-mealie-user` before the next restart. Lazy path: **Expected**: the request works, and the row is encrypted afterwards.

## 5. Key change (Story 4, SC-004)

1. Replace `JARIT_ENCRYPTION_KEY` with a newly generated key and restart.
2. Upload a recipe. **Expected**: HTTP 409 with the "please enter your Mealie API key again" message, shown in the UI. Other pages keep working.
3. The log has one WARNING with `user_id` and `service_name`, and no secret.
4. Re-enter the credentials in the UI. **Expected**: the upload works again.

## 6. Leak check (SC-005)

`uv run pytest tests/db/test_no_secret_leaks.py`. **Expected**: the sentinel key appears 0 times in all captured responses and log records.

## 7. CI on a pull request (Story 6, SC-006)

Open a draft PR from this branch to `dev`.

**Expected**: the `backend` and `frontend` jobs start on their own and finish green in under 10 minutes. Then push a commit with a failing assert. **Expected**: the `backend` job turns red, and the failing test is named in the log.
