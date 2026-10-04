# Research: Verschlüsselte Integrations-Keys und PR-CI

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-10-02

All Technical Context items were resolved; no `NEEDS CLARIFICATION` remains.

## R1 – Encryption primitive

- **Decision**: Fernet from `cryptography` (AES-128-CBC + HMAC-SHA256, authenticated). `cryptography` becomes a direct dependency. It is already in `uv.lock` (46.0.3) as a transitive dependency of `python-jose[cryptography]`.
- **Rationale**: Fernet is the high-level "recipe" API from pyca. It needs no IV or nonce handling, has built-in integrity checks (`InvalidToken` on any tampering or wrong key), and offers `Fernet.generate_key()` for the startup message. It also rejects keys with the wrong format at construction (`ValueError`), which gives us the "invalid key" check for free.
- **Alternatives considered**:
  - AES-GCM via `cryptography.hazmat`: stronger in theory, but it needs manual nonce management and a custom key format. That is more room for mistakes and gains nothing at this data volume.
  - `pgcrypto` in PostgreSQL: the key would have to travel to the DB in SQL statements and could end up in DB logs, which violates FR-006/FR-007.
  - `sqlalchemy-utils` `EncryptedType`: an extra dependency, and it decrypts on every load (see R3).

## R2 – Telling ciphertext apart from legacy plaintext (FR-004)

- **Decision**: Stored value = `enc:v1:` + Fernet token. A value without this prefix is legacy plaintext.
- **Rationale**: The prefix is explicit and cannot collide with real keys (Mealie keys are JWTs starting with `eyJ`). The version part allows a later scheme change (e.g. multi-key rotation) without guesswork. Relying on Fernet's own `gAAAAA` token start would also work, but that is an internal format detail and not a contract.
- **Alternatives considered**: An extra `is_encrypted` boolean column. Rejected because the project has no migration tooling (`Base.metadata.create_all` only creates missing tables, it never alters them), so adding a column to existing installations would need manual SQL.

## R3 – Where encryption happens (FR-002, FR-003)

- **Decision**: An explicit service layer, `jarit/integrations/credentials.py`, with `set_secret(entry, plaintext)` and `reveal_secret(db, entry) -> str`. Both are built on a pure `SecretCipher` in `jarit/core/crypto.py`. The ORM attribute is renamed to `api_key_ciphertext` (DB column name `api_key` stays), so any leftover direct access to `.api_key` fails loudly instead of silently reading ciphertext.
- **Rationale**: Decryption happens only where the secret is used (Mealie calls), as FR-002 requires. Listing and deleting entries never decrypt, so an unreadable entry can still be deleted (spec edge case). Lazy migration needs write access to the session, which a column type does not have.
- **Alternatives considered**: SQLAlchemy `TypeDecorator` (transparent). Rejected: it decrypts on every row load, so a single unreadable row would make `GET /users/me/api-keys` and `DELETE` fail. It also cannot write migrated values back.

## R4 – Startup key validation and error output (FR-008 to FR-010)

- **Decision**: The env var is `JARIT_ENCRYPTION_KEY`. `main.py` calls `require_encryption_key()` as its first statement, before `create_all`, before `logfire.configure`, and before any router import. A missing or invalid key prints a block to **stderr** and calls `sys.exit(1)`. The block contains:
  1. the cause (`missing` or `invalid`), never the invalid value,
  2. the line `JARIT_ENCRYPTION_KEY=<freshly generated key>`,
  3. the warning about losing the key.
- **Rationale**: Running before `logfire.configure` ensures the suggested key never reaches the external monitoring service. Uvicorn aborts when the module raises `SystemExit` during import, so the container exits with an error and `restart: unless-stopped` shows the message on every retry. Fernet keys are URL-safe base64 (`A–Z a–z 0–9 - _ =`), so the `.env` line needs no quoting. Docker Compose splits on the first `=`.
- **Alternatives considered**: A FastAPI lifespan hook. Rejected because `create_all` and the plaintext migration already run at import time in `main.py`, and the check has to come first.
- **Note**: `docker-compose.yml` passes variables explicitly, so `JARIT_ENCRYPTION_KEY=${JARIT_ENCRYPTION_KEY}` must be added there. Otherwise the key would always be "missing" in production.

## R5 – Plaintext migration (FR-011 to FR-013, clarified: lazy + at startup)

- **Decision**:
  - **At startup**: right after `create_all`, `migrate_plaintext_secrets()` opens its own session, selects rows whose value does not start with `enc:v1:`, and encrypts each one with a compare-and-set update (`UPDATE … SET api_key=:new WHERE id=:id AND api_key=:old`). It logs only counts (migrated, failed). Errors are caught per row, and startup continues.
  - **On access**: `reveal_secret` does the same for a single row and then returns the plaintext.
- **Rationale**: Compare-and-set makes concurrent migrations (two requests, or several workers starting at once) harmless: the loser updates 0 rows and nothing is double-encrypted (FR-012).
- **Alternatives considered**: A one-off CLI migration command. Rejected because the spec requires zero operator steps.

## R6 – Unreadable entries (FR-014 to FR-016)

- **Decision**: `reveal_secret` raises `SecretUnreadableError` on `InvalidToken`. `get_mealie_credentials` maps it to HTTP **409** with a fixed, readable `detail`. The frontend already shows `detail` from error responses (`frontend/src/lib/api.ts:51-55`), so no UI change is needed. One `WARNING` log line goes out with `user_id`, `service_name` and `entry_id`.
- **Rationale**: 409 means "the stored state conflicts with the request". It is different from 404 (not configured) and 401 (session), so the frontend's 401 auto-logout is not triggered.

## R7 – No leaks in responses and logs (FR-005, FR-006)

- **Findings**: `APIKeyResponse` already leaves the key out. The code has no logging setup; the only `print` is a user count in `auth/service.py`. Logfire instruments Pydantic AI only (not FastAPI or httpx), so Mealie request headers are not captured.
- **Decision**: Keep it that way. `SecretCipher` and the credentials service define `__repr__` without secret values. Exceptions are re-raised `from None` so tracebacks do not carry the plaintext. A leak test (SC-005) uses a sentinel key and checks every captured response body and every log record (`caplog`).

## R8 – CI pipeline (FR-020 to FR-023, clarified: default scope)

- **Decision**: `.github/workflows/ci.yml` runs on `pull_request` (all target branches), with `permissions: contents: read` and no secrets. It has two parallel jobs:
  - **backend**: `astral-sh/setup-uv` with cache, `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest tests/unit tests/db`. A `postgres:16` service container provides the DB.
  - **frontend**: `actions/setup-node` (Node 24, npm cache), `npm ci`, `npm run lint`, `npm run check`, `npm run build`.
- **Rationale**: Postgres as a service container needs no secrets, so PRs from forks work. The models use the `now()` server default, which SQLite does not support, so a real Postgres is required for DB-backed tests. A test encryption key is generated per run in `tests/conftest.py`, so no key exists in the repo at all.
- **Dependency groups**: `dev` currently pulls `sentence-transformers` and `scikit-learn` (via torch, several GB). A local `uv sync` with the dev group did not finish within 5 minutes. These packages and `pydantic-evals` move to a new `eval` group, which is only needed for `tests/model_eval`. CI and normal development stay lean.
- **Baseline status today**: CI would be red from the first run. These checks fail on the current code and must be fixed in this feature:

  | Check | Current result |
  |---|---|
  | `pytest tests/unit` | Collection error: `test_mealie_integration.py` imports `MEALIE_ENDPOINT` and `MEALIE_API_KEY`, which no longer exist. The other 10 tests pass. |
  | `ruff check` | 2 errors (unused imports) |
  | `ruff format --check` | 3 files (`main.py`, `users.py`, `auth/service.py`) |
  | `npm run lint` | Prettier: 34 files. ESLint cannot start because `eslint.config.js` points at a missing `frontend/.gitignore`. |
  | `npm run check` | 7 type errors in `api.ts`, `AdminPanel.svelte`, `Navigation.svelte` and `RecipePreview.svelte`. `AdminPanel.svelte:132` also compares the role with `'admin'`, which can never match (backend roles are `ADMIN`/`USER`). This is dead code, not a bug. |
  | `npm run build` | passes |

- **Alternatives considered**: Leaving the failing checks out of CI at first. Rejected because a CI that starts red, or whose checks are skipped, gives no signal.
