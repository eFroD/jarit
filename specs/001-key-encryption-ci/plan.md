# Implementation Plan: Verschlüsselte Integrations-Keys und PR-CI

**Branch**: `feature/001-key-encryption-ci` (from `dev`) | **Date**: 2026-10-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-key-encryption-ci/spec.md`

## Summary

User integration secrets (`api_keys.api_key`) are stored as Fernet ciphertext with an `enc:v1:` prefix. The key comes only from `JARIT_ENCRYPTION_KEY`. A single credentials service encrypts on write and decrypts only right before a call to the integration. Legacy plaintext rows are migrated once at startup and again lazily on access, using a compare-and-set update.

Startup aborts with a copy-paste `.env` line if the key is missing or invalid. An unreadable row turns into a 409 "please re-enter" response instead of a crash.

A new `pull_request` workflow runs ruff, pytest (with a Postgres service container), and the frontend lint, type and build checks, without any secrets. The existing baseline failures are fixed so that CI starts green. Details: [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript / Svelte 5 with SvelteKit static adapter (frontend), Node 24

**Primary Dependencies**: FastAPI, SQLAlchemy 2, `cryptography` (Fernet; made an explicit dependency), Logfire; CI: `astral-sh/setup-uv`, `actions/setup-node`

**Storage**: PostgreSQL. No schema change; `api_keys.api_key` changes format only ([data-model.md](./data-model.md)).

**Testing**: pytest + pytest-asyncio. New `tests/conftest.py` (generates a throwaway key). New `tests/db/` for DB-backed tests against Postgres.

**Target Platform**: Linux containers (Docker Compose), GitHub-hosted runners for CI

**Project Type**: Web application (FastAPI backend in `jarit/` + `main.py`, SvelteKit frontend in `frontend/`)

**Performance Goals**: Encryption adds less than 1 ms per credential access (negligible). PR checks take under 10 min in total (SC-006).

**Constraints**:
- No secret in API responses, logs or Logfire.
- The suggested key is printed before `logfire.configure`.
- No migration tooling in the project, so no column changes.
- CI must work for fork PRs, so it cannot use secrets.

**Scale/Scope**: A self-hosted instance with a handful of users and one row per user and integration. The startup migration touches at most a few hundred rows.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, so no ratified principles exist and there are no gates to evaluate. **PASS (vacuous).** Run `/speckit-constitution` to define project principles. The plan follows the implicit conventions of the existing code: a flat `jarit/` package and FastAPI dependencies for request-scoped access.

*Post-design re-check (after Phase 1):* still no constitution, so nothing to violate. **PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/001-key-encryption-ci/
├── spec.md
├── plan.md              # this file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── http-api.md
│   ├── operator-config.md
│   └── ci-checks.md
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
main.py                                   # MODIFY: require_encryption_key() first; startup migration after create_all
jarit/
├── core/
│   └── crypto.py                         # NEW: SecretCipher (encrypt/decrypt/is_encrypted), key loading + startup failure block
├── integrations/
│   ├── credentials.py                    # NEW: set_secret, reveal_secret (lazy CAS migration), migrate_plaintext_secrets, SecretUnreadableError
│   └── mealie_integration.py             # unchanged
├── db/models/api_keys.py                 # MODIFY: attribute api_key → api_key_ciphertext (Column("api_key", …))
├── api/v1/endpoints/
│   ├── users.py                          # MODIFY: POST uses set_secret; reject blank key (422)
│   └── integrations.py                   # MODIFY: get_mealie_credentials uses reveal_secret; map SecretUnreadableError → 409
└── auth/service.py                       # MODIFY: ruff format only

tests/
├── conftest.py                           # NEW: set JARIT_ENCRYPTION_KEY to a generated key if unset
├── unit/
│   ├── test_crypto.py                    # NEW: round-trip, prefix, wrong key → error, invalid key → startup block (no value echoed)
│   └── test_mealie_integration.py        # FIX: remove imports of removed constants
└── db/                                   # NEW: needs DATABASE_URL (Postgres)
    ├── conftest.py                       # engine/session fixtures, create_all + truncate per test
    ├── test_credentials_service.py       # set/reveal, lazy + startup migration, CAS idempotency, unreadable row
    ├── test_api_keys_endpoints.py        # POST/GET/DELETE behaviour, 409 path, 422 on blank
    └── test_no_secret_leaks.py           # SC-005 sentinel scan of responses + caplog

.github/workflows/ci.yml                  # NEW: backend + frontend jobs (contracts/ci-checks.md)
pyproject.toml / uv.lock                  # MODIFY: + cryptography; move sentence-transformers, scikit-learn, pydantic-evals to `eval` group
docker-compose.yml, docker-compose.dev.yml# MODIFY: pass JARIT_ENCRYPTION_KEY to backend
.env_example                              # MODIFY: JARIT_ENCRYPTION_KEY=CHANGEME + comment
README.md                                 # MODIFY: key generation, backup, rotation; make "encrypted API keys" claim precise

frontend/
├── eslint.config.js                      # FIX: point includeIgnoreFile at ../.gitignore
├── src/lib/api.ts                        # FIX: typed Authorization header
├── src/lib/components/AdminPanel.svelte  # FIX: unknown catch types; remove dead `'admin'` comparison
├── src/lib/components/Navigation.svelte  # FIX: implicit any
├── src/lib/components/RecipePreview.svelte # FIX: string | string[] binding
└── **/*                                  # Prettier --write (formatting only, separate commit)
```

**Structure Decision**: Keep the existing single-backend layout. Encryption primitives go in `jarit/core/` (next to `security.py`). The integration-agnostic credential access goes in `jarit/integrations/credentials.py`, so every current and future integration uses it (FR-003). DB-backed tests get their own `tests/db/` folder, so it is clear which tests need Postgres.

## Implementation Order

1. **Baseline green** (separate commits): ruff fix and format; fix the mealie unit test; fix the eslint config; run Prettier write (formatting-only commit); fix the svelte-check errors; split dependency groups.
2. **CI workflow** (Story 6): add it early, so every following commit is checked.
3. **Crypto core + startup check** (Story 2): `crypto.py`, `main.py` ordering, compose files, `.env_example`.
4. **Credentials service + endpoints** (Story 1): ORM attribute rename, `set_secret`/`reveal_secret`, endpoint wiring.
5. **Migration** (Story 3): startup bulk + lazy compare-and-set.
6. **Unreadable handling** (Story 4): 409 mapping and the warning log.
7. **Leak test + README** (Story 5, SC-005).

## Risks

- **Prettier diff touches 34 files.** Keep it in its own commit with no logic changes, so review stays possible.
- **Rename of the ORM attribute.** All `.api_key` accesses on `APIKey` must change (only `users.py` and `integrations.py`, both verified by grep). Pydantic models with the field name `api_key` (`APIKeyCreate`) stay the same.
- **Existing installations upgrading without setting the key.** They will not start, which is intended. The release notes and README must call this out as a breaking operator step.
- **`tests/integration/test_api.py` is broken** (`from jarit.main import app`). It is left out of CI and left unchanged; it is a candidate for a follow-up.

## Complexity Tracking

No constitution violations to justify.
