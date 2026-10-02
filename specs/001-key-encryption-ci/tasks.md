---

description: "Task list for encrypted integration keys and PR CI"
---

# Tasks: Verschlüsselte Integrations-Keys und PR-CI

**Input**: Design documents from `specs/001-key-encryption-ci/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Included. The spec requires that the encryption tests run as part of the PR checks (US6, scenario 4) and that a leak test exists (SC-005).

**Organization**: Tasks are grouped by user story, so each story can be implemented and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on unfinished tasks)
- **[Story]**: The user story the task belongs to (US1–US6 from spec.md)

## Path Conventions

Web app with the backend at the repo root (`main.py`, `jarit/`, `tests/`) and the frontend in `frontend/`. Shared names used throughout:

- Env var: `JARIT_ENCRYPTION_KEY`
- Ciphertext prefix: `enc:v1:`
- ORM attribute: `APIKey.api_key_ciphertext` (DB column stays `api_key`)
- Run tests with `uv run pytest`. DB tests need `DATABASE_URL` pointing at Postgres (see [quickstart.md](./quickstart.md) §1).

---

## Phase 1: Setup (Baseline green)

**Purpose**: Make every check the CI will run pass on the current code ([research.md](./research.md) R8 baseline table). Formatting and logic fixes go in separate commits.

- [X] T001 In `pyproject.toml`, add `cryptography>=46.0.3` to `[project].dependencies`. Create a new `[dependency-groups].eval` group and move `pydantic-evals[logfire]`, `scikit-learn` and `sentence-transformers` from `dev` into it. Then run `uv lock` to update `uv.lock` and check that `uv sync --locked` installs no torch.
- [X] T002 [P] Fix the ruff F401 in `jarit/models/output_models/__init__.py` by adding `__all__ = ["RecipeResponse"]` (keep the re-export). Then run `uv run ruff format main.py jarit/api/v1/endpoints/users.py jarit/auth/service.py`, and check that `uv run ruff check . && uv run ruff format --check .` passes.
- [X] T003 [P] Fix `tests/unit/test_mealie_integration.py`:
  - Remove the imports of `MEALIE_ENDPOINT`, `MEALIE_API_KEY` and the unused `MagicMock`.
  - Define module constants `MEALIE_ENDPOINT = "https://mealie.test"` and `MEALIE_API_KEY = "test-key"` in the test file.
  - Make sure every call to `push_recipe_to_mealie` and `push_image_to_mealie` passes them as the `mealie_endpoint` and `mealie_api_key` arguments (signatures in `jarit/integrations/mealie_integration.py`).
  - Check that `uv run pytest tests/unit` passes.
- [X] T004 [P] In `frontend/eslint.config.js`, change `gitignorePath` to `new URL('../.gitignore', import.meta.url)`, because `frontend/.gitignore` does not exist. Check that `npx eslint .` starts, and fix any ESLint errors it reports in `frontend/src/`.
- [X] T005 Run `npx prettier --write .` in `frontend/` and commit it alone as "style(frontend): apply prettier". Check that `npm run lint` passes. Depends on T004.
- [X] T006 [P] Fix the 7 `svelte-check` errors and check that `npm run check` passes:
  - `frontend/src/lib/api.ts:30`: type `headers` as `Record<string, string>`.
  - `frontend/src/lib/components/AdminPanel.svelte` lines 49, 86, 105: narrow the `catch (e)` value with `e instanceof Error ? e.message : String(e)`.
  - `frontend/src/lib/components/AdminPanel.svelte:132`: drop the dead `|| u.role === 'admin'`.
  - `frontend/src/lib/components/Navigation.svelte:18`: type the parameter as `(e: MouseEvent)` and cast `e.target as HTMLElement`.
  - `frontend/src/lib/components/RecipePreview.svelte:311`: handle `recipe.image` being `string[]`, e.g. `Array.isArray(recipe.image) ? recipe.image[0] : recipe.image`.

**Checkpoint**: All six commands in [contracts/ci-checks.md](./contracts/ci-checks.md) pass locally (`tests/db` does not exist yet).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The cipher and test infrastructure that every story needs.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T007 Create `jarit/core/crypto.py` with:
  - `PREFIX = "enc:v1:"` and `ENV_VAR = "JARIT_ENCRYPTION_KEY"`.
  - `class EncryptionKeyError(Exception)`, carrying a `reason` of `"missing"` or `"invalid"`.
  - `class SecretDecryptionError(Exception)`.
  - `class SecretCipher`:
    - `__init__(self, key: str)` wraps `cryptography.fernet.Fernet` and turns `ValueError` and `binascii.Error` into `EncryptionKeyError("invalid")` using `from None`.
    - `encrypt(plaintext: str) -> str` returns `PREFIX + token`.
    - `decrypt(stored: str) -> str` raises `SecretDecryptionError` (from `None`) on `InvalidToken`, and `ValueError` if the prefix is missing.
    - `@staticmethod is_encrypted(stored: str) -> bool`.
    - `__repr__` returns `"SecretCipher(<redacted>)"`.
  - `load_cipher_from_env() -> SecretCipher`: raises `EncryptionKeyError("missing")` for an unset or blank value. It never puts the value in a message.
  - `get_cipher()`: a cached module-level accessor (`functools.lru_cache`) around `load_cipher_from_env`.
- [X] T008 [P] Create `tests/conftest.py`. At import time, call `os.environ.setdefault("JARIT_ENCRYPTION_KEY", Fernet.generate_key().decode())`, so every test run uses a throwaway key and no key is ever committed.
- [X] T009 [P] Create `tests/unit/test_crypto.py` with these cases:
  - Round trip.
  - Output starts with `enc:v1:` and does not contain the plaintext.
  - Two encryptions of the same value differ.
  - `is_encrypted` returns true for ciphertext and false for legacy values like `eyJhbGciOi...`.
  - Decrypting with a different key raises `SecretDecryptionError`.
  - `SecretCipher("CHANGEME")` raises `EncryptionKeyError` whose `str()` does not contain `CHANGEME`.
  - `repr()` contains no key material.
- [X] T010 Create `tests/db/__init__.py` and `tests/db/conftest.py`:
  - Skip the whole package with `pytest.skip(allow_module_level=True)` if `DATABASE_URL` is unset or not `postgresql://…`.
  - Session fixture: `Base.metadata.create_all(engine)` (imports from `jarit.db.database` and `jarit.db.models`).
  - Function fixture `db`: a `SessionLocal()` that runs `TRUNCATE users, api_keys RESTART IDENTITY CASCADE` after each test.
  - Fixture `user`: inserts a `User` row.
  - Fixture `client`: a `fastapi.testclient.TestClient(main.app)` with `get_current_user` overridden to return `user`.

**Checkpoint**: `uv run pytest tests/unit` is green, including `test_crypto.py`.

---

## Phase 3: User Story 1 – Zugangsdaten werden nur verschlüsselt gespeichert (P1) 🎯 MVP

**Goal**: Every integration secret is stored as `enc:v1:` ciphertext and decrypted only where it is sent to the integration. It never appears in API responses.

**Independent Test**: Save Mealie credentials and check that `SELECT api_key FROM api_keys` shows `enc:v1:…` without the plaintext. Upload or verify against Mealie (mocked) still works. ([quickstart.md](./quickstart.md) §3)

### Tests for User Story 1

- [X] T011 [P] [US1] Create `tests/db/test_credentials_service.py` with the US1 cases:
  - `set_secret` stores ciphertext, which matches `^enc:v1:` and does not contain the plaintext.
  - `reveal_secret` returns the plaintext.
  - Replacing a secret stores new ciphertext.
  - The module works for any `service_name` (use `"other-service"`) without special handling.
- [X] T012 [P] [US1] Create `tests/db/test_api_keys_endpoints.py` with these cases:
  - `POST /api/v1/users/me/api-keys` stores ciphertext (checked through `db`).
  - `GET /api/v1/users/me/api-keys` and `GET /api/v1/users/me/api-keys/mealie` responses have no `api_key` key, and the plaintext and ciphertext do not appear in `response.text`.
  - A blank or whitespace-only `api_key` returns 422 and stores no row.
  - `GET /api/v1/integrations/verify-mealie-user`, with `jarit.api.v1.endpoints.integrations.verify_mealie_user` patched via `AsyncMock`, receives the decrypted plaintext.

### Implementation for User Story 1

- [X] T013 [US1] In `jarit/db/models/api_keys.py`, rename the attribute to `api_key_ciphertext = Column("api_key", String, nullable=False)`. The DB column name stays the same and there is no schema change.
- [X] T014 [US1] Create `jarit/integrations/credentials.py` with:
  - `set_secret(entry: APIKey, plaintext: str) -> None`, which sets `entry.api_key_ciphertext = get_cipher().encrypt(plaintext)` and `entry.updated_at = func.now()`.
  - `reveal_secret(db: Session, entry: APIKey) -> str`, which, if `is_encrypted`, decrypts with `get_cipher()`. For now the legacy branch just returns the value; it is completed in T021.
  - `logger = logging.getLogger(__name__)`.
  - No function may log or include the plaintext or ciphertext in an exception message.
  - Depends on T007 and T013.
- [X] T015 [US1] In `jarit/api/v1/endpoints/users.py`:
  - Add a pydantic `field_validator` on `APIKeyCreate.api_key` that strips the value and rejects empty input (gives 422).
  - In `create_or_update_api_key`, replace both direct assignments with `set_secret(entry, api_key_data.api_key)`. For new rows, build the `APIKey` without the secret, then call `set_secret` before `db.add`.
  - Depends on T014.
- [X] T016 [US1] In `jarit/api/v1/endpoints/integrations.py`, change `get_mealie_credentials` to return `{"endpoint": api_key_entry.base_url, "api_key": reveal_secret(db, api_key_entry)}`. Depends on T014.
- [X] T017 [US1] Grep for `\.api_key\b` on `APIKey` instances in `jarit/` and `main.py`, and check that no direct access to the old attribute remains. `APIKeyCreate.api_key` is a pydantic field and stays. Run `uv run pytest tests/unit tests/db`.

**Checkpoint**: US1 is fully working. New and updated secrets are encrypted; legacy plaintext rows still work through the legacy branch of `reveal_secret`.

---

## Phase 4: User Story 2 – Der Host richtet den Schlüssel beim Start sicher ein (P1)

**Goal**: With a missing or invalid key, the backend exits with code 1. Before that, it prints a block with a newly generated key, a copy-paste `.env` line and a warning about losing the key. It does this before Logfire is configured ([contracts/operator-config.md](./contracts/operator-config.md)).

**Independent Test**: [quickstart.md](./quickstart.md) §2.

### Tests for User Story 2

- [X] T018 [P] [US2] Create `tests/unit/test_startup_key_check.py`:
  - Call `require_encryption_key()` with `monkeypatch.delenv("JARIT_ENCRYPTION_KEY")`. Assert `SystemExit` with code 1. In `capsys.readouterr().err`, assert there is a line matching `^JARIT_ENCRYPTION_KEY=\S{44}$`, that `Fernet(<that value>)` constructs, that the text contains "missing" and the loss warning, and that stdout is empty.
  - Same with the value `CHANGEME`: "invalid" appears, `CHANGEME` does not.
  - Two calls produce different suggested keys.
  - A valid key returns without output.

### Implementation for User Story 2

- [X] T019 [US2] In `jarit/core/crypto.py`, add `require_encryption_key() -> None`, which calls `get_cipher()`. On `EncryptionKeyError`, it writes the block from [contracts/operator-config.md](./contracts/operator-config.md) to `sys.stderr`: the cause, the `JARIT_ENCRYPTION_KEY=<Fernet.generate_key()>` line, and the warning about losing the key. It never includes the current value, and then calls `sys.exit(1)`. Also add `format_startup_failure(reason: str, suggested_key: str) -> str` so the text can be tested.
- [X] T020 [US2] Make startup order explicit in `main.py`. The first lines must be `from jarit.core.crypto import require_encryption_key` and `require_encryption_key()`. They come before importing `jarit.db.database` and `jarit.api.router`, before `Base.metadata.create_all`, and before `logfire.configure`. Add `# noqa: E402` to the later imports if ruff complains.
- [X] T021 [P] [US2] Add `- JARIT_ENCRYPTION_KEY=${JARIT_ENCRYPTION_KEY}` under `backend.environment` in `docker-compose.yml`, and the same entry under the backend service in `docker-compose.dev.yml` if it has an `environment` list. The dev compose file also uses `--env-file`, so check that both paths deliver the variable.
- [X] T022 [P] [US2] In `.env_example`, add a section "Encryption of user integration credentials" with a comment (how to generate the key, back it up, loss means re-entry) and `JARIT_ENCRYPTION_KEY=CHANGEME`. This placeholder must fail validation.

**Checkpoint**: The backend refuses to start without a valid key and starts normally with one. US1 still passes.

---

## Phase 5: User Story 3 – Bestehende Installationen werden ohne Zutun migriert (P2)

**Goal**: Legacy plaintext rows are encrypted at startup and, as a fallback, on first access. Concurrent migrations never double-encrypt (FR-011 to FR-013).

**Independent Test**: [quickstart.md](./quickstart.md) §4.

### Tests for User Story 3

- [X] T023 [P] [US3] Extend `tests/db/test_credentials_service.py` with these cases:
  - **Lazy:** insert a raw row with `api_key='legacy-plain'`. `reveal_secret` returns `'legacy-plain'`, and afterwards the row matches `^enc:v1:` and decrypts to `'legacy-plain'`.
  - **Startup:** three legacy rows and one encrypted row. `migrate_plaintext_secrets()` returns `(3, 0)`, all rows are encrypted, and the already-encrypted row's value is unchanged byte for byte.
  - **Compare-and-set:** call the internal `_migrate_row(db, id, old_value)` twice with the same `old_value`. The second call updates 0 rows, and the stored value decrypts to the original.
  - **Failure isolation:** make the update fail for one row by patching. Migration returns `failed=1` and does not raise.

### Implementation for User Story 3

- [X] T024 [US3] In `jarit/integrations/credentials.py`, add `_migrate_row(db, entry_id: int, old_value: str) -> bool`. It runs `update(APIKey).where(APIKey.id == entry_id, APIKey.api_key_ciphertext == old_value).values(api_key_ciphertext=get_cipher().encrypt(old_value), updated_at=func.now())`, commits, and returns `rowcount == 1`. Complete the legacy branch of `reveal_secret`: if the value is not encrypted, call `_migrate_row` inside `try/except Exception`. On failure, log a WARNING with only `entry.id` and `service_name`, then return the plaintext either way.
- [X] T025 [US3] In `jarit/integrations/credentials.py`, add `migrate_plaintext_secrets() -> tuple[int, int]`:
  - Open its own `SessionLocal()` and select `id`, `api_key_ciphertext` where the value does not start with `enc:v1:`.
  - Call `_migrate_row` for each row. Wrap each call in `try/except`, roll back on error, and count successes and failures.
  - If any legacy rows were found, log one INFO line in the format from [contracts/operator-config.md](./contracts/operator-config.md). The line contains counts only.
- [X] T026 [US3] In `main.py`, call `migrate_plaintext_secrets()` right after `Base.metadata.create_all(bind=engine)`, wrapped in `try/except Exception` that logs a WARNING (without values) so startup is never blocked.

**Checkpoint**: An old database works after the upgrade with zero user action, and there are no plaintext rows after the first start.

---

## Phase 6: User Story 4 – Ein unlesbarer Eintrag legt die Anwendung nicht lahm (P2)

**Goal**: A row that the current key cannot decrypt leads to HTTP 409 with a "please re-enter" message and a WARNING log without secrets. The app keeps running, and the user can overwrite or delete the row (FR-014 to FR-016).

**Independent Test**: [quickstart.md](./quickstart.md) §5.

### Tests for User Story 4

- [X] T027 [P] [US4] Add these cases to `tests/db/test_api_keys_endpoints.py`. For setup, store a secret encrypted with a different `Fernet.generate_key()` via `SecretCipher(other).encrypt(...)` and write it raw.
  - `POST /api/v1/integrations/upload-mealie` (with a minimal valid `Recipe` body) returns 409, the `detail` mentions re-entering the key, and the body has no `enc:v1:`.
  - `GET /api/v1/integrations/verify-mealie-user` returns 409.
  - `GET /api/v1/users/me/api-keys` still returns 200.
  - `DELETE /api/v1/users/me/api-keys/mealie` returns 204.
  - `POST` with new credentials, then verify (mocked), works.
  - `caplog` has exactly one WARNING containing `user_id` and `mealie`, and no ciphertext.

### Implementation for User Story 4

- [X] T028 [US4] In `jarit/integrations/credentials.py`, add `class SecretUnreadableError(Exception)` carrying `entry_id`, `user_id` and `service_name` (no secret). In `reveal_secret`, catch `SecretDecryptionError`, log `logger.warning("Stored credential unreadable with current key", extra={...})`, and raise `SecretUnreadableError(...) from None`.
- [X] T029 [US4] In `jarit/api/v1/endpoints/integrations.py`, `get_mealie_credentials` catches `SecretUnreadableError` and raises `HTTPException(status_code=409, detail=<exact text from contracts/http-api.md>)`. Check that `frontend/src/lib/api.ts` shows `detail` for 409 and does not trigger logout. Change it only if it does not.

**Checkpoint**: After a key change, the app stays usable, affected users see a clear message and recover by re-entering their credentials.

---

## Phase 7: User Story 5 – Der Host weiß, wie er den Schlüssel erzeugt und rotiert (P3)

**Goal**: The README documents key generation, where to put the key, backup, and what rotation means ([contracts/operator-config.md](./contracts/operator-config.md)).

**Independent Test**: A person new to the project sets up an instance with a valid key using only the README.

- [X] T030 [US5] In `README.md`:
  - Add a section "Encryption key for integration credentials". Cover the two generation commands from [contracts/operator-config.md](./contracts/operator-config.md), the `.env` line, the fact that the backend refuses to start without the key and prints a suggestion, the backup recommendation, and rotation: changing the key makes all stored integration keys unreadable, affected users get a re-entry prompt, and there is no automatic re-encryption.
  - Add an "Upgrading from earlier versions" note: setting the key is required, and existing keys are migrated automatically.
  - Reword the Features bullet "encrypted API keys" so it says precisely which data is encrypted.
  - Link the new section from the Table of Contents.

**Checkpoint**: The README covers FR-017 to FR-019.

---

## Phase 8: User Story 6 – Pull Requests werden automatisch geprüft (P3)

**Goal**: Every PR runs the checks from [contracts/ci-checks.md](./contracts/ci-checks.md) without secrets, and failures show on the PR.

**Independent Test**: [quickstart.md](./quickstart.md) §7.

- [X] T031 [P] [US6] Create `.github/workflows/ci.yml`:
  - **Trigger and permissions:** `on: pull_request` (types opened, synchronize, reopened), `permissions: contents: read`, and `concurrency` per PR ref with `cancel-in-progress: true`.
  - **Job `backend`** (`ubuntu-latest`):
    - `services.postgres`: image `postgres:16`, env `POSTGRES_USER/PASSWORD/DB=jarit`/`jarit`/`jarit_test`, port `5432:5432`, health check `pg_isready`.
    - Steps: `actions/checkout@v4`, then `astral-sh/setup-uv` at its current major version with `enable-cache: true` and `python-version: "3.13"`.
    - Then `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest tests/unit tests/db -q` with env `DATABASE_URL=postgresql://jarit:jarit@localhost:5432/jarit_test`.
  - **Job `frontend`**:
    - Defaults to `working-directory: frontend`.
    - Steps: `actions/checkout@v4`, `actions/setup-node@v4` with `node-version: 24`, `cache: npm` and `cache-dependency-path: frontend/package-lock.json`.
    - Then `npm ci`, `npm run lint`, `npm run check`, `npm run build`.
  - No `secrets.*` anywhere.
- [X] T032 [US6] Run `grep -n "secrets\." .github/workflows/ci.yml` and check it returns nothing. Validate the YAML syntax with `uvx check-jsonschema --builtin-schema vendor.github-workflows .github/workflows/ci.yml`.

**Checkpoint**: Opening a PR to `dev` runs both jobs, and both are green.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [X] T033 [P] Create `tests/db/test_no_secret_leaks.py` (SC-005), using the sentinel `"LEAK-SENTINEL-7f3a"`. With `caplog` at DEBUG level, run this sequence through `client`:
  - store the secret, list, get by service, verify (mocked);
  - insert a legacy plaintext row and verify again (lazy migration);
  - swap the stored value for one encrypted with a foreign key and call the 409 path;
  - delete.

  Assert that the sentinel appears in no `response.text` and in no `caplog.text`, and that no `enc:v1:` string appears in any response.
- [X] T034 [P] Remove the `print(f"User count: {count}")` debug output in `jarit/auth/service.py`, or replace it with `logger.debug`, to keep log output intentional.
- [X] T035 Run the full local check suite from [quickstart.md](./quickstart.md) §1 (backend and frontend) and fix any failures.
- [X] T036 Run the manual quickstart validation §2–§5 against `docker-compose.dev.yml`, then tick the items in `specs/001-key-encryption-ci/checklists/requirements.md`, which should still be all green.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies. T005 depends on T004.
- **Foundational (Phase 2)**: depends on T001, which provides `cryptography` as a direct dependency. Blocks all stories.
- **US1 (Phase 3)**: depends on Phase 2.
- **US2 (Phase 4)**: depends on Phase 2 only (T007). It can run in parallel with US1, but T020 and T026 both edit `main.py`, so do them in order.
- **US3 (Phase 5)**: depends on US1 (T014 `reveal_secret`, T013 attribute name).
- **US4 (Phase 6)**: depends on US1 (T014, T016).
- **US5 (Phase 7)**: depends on US2 (env var name and messages are final). Content-wise it is independent of the code.
- **US6 (Phase 8)**: depends on Phase 1 being green and T010 (`tests/db` exists). **Recommended: do it right after Phase 2**, so every later commit is checked in the PR.
- **Polish (Phase 9)**: after US1–US4.

### Story Dependency Graph

```text
Setup ─▶ Foundational ─┬─▶ US1 ─┬─▶ US3
                       │        └─▶ US4 ─┐
                       ├─▶ US2 ─▶ US5     ├─▶ Polish
                       └─▶ US6 ───────────┘
```

### Within Each User Story

Write the tests first and confirm they fail, then implement until they pass. Models come before the service, and the service before the endpoints.

### Parallel Opportunities

- Phase 1: T002, T003, T004 and T006 can run in parallel (separate files). T005 comes after T004.
- Phase 2: T008 and T009 in parallel, after T007.
- US1: T011 and T012 in parallel (separate test files).
- US2: T018, T021 and T022 in parallel.
- After US1: US3 and US4 can go in parallel, but both edit `credentials.py`, so coordinate or run them in order.
- US6 (T031) can run in parallel with any story.

## Parallel Example: User Story 1

```text
# Tests together (separate files):
Task T011: tests/db/test_credentials_service.py
Task T012: tests/db/test_api_keys_endpoints.py

# Then in order: T013 → T014 → (T015 ∥ T016) → T017
```

## Parallel Example: User Story 2

```text
Task T018: tests/unit/test_startup_key_check.py
Task T021: docker-compose.yml / docker-compose.dev.yml
Task T022: .env_example
# Then: T019 → T020
```

## Implementation Strategy

### MVP (US1 + US2, both P1)

1. Phase 1 (baseline green), then Phase 2.
2. Phase 8 / US6 early (recommended), so the PR shows the checks.
3. US1, then US2. Stop and validate with [quickstart.md](./quickstart.md) §2–§3.

US1 alone is not deployable without US2, because without the startup check a missing key would only surface on first use. Ship US1 and US2 together as the MVP.

### Incremental Delivery

1. MVP (US1 + US2): new secrets are encrypted, and startup is safe.
2. Add US3: existing installations upgrade with zero user steps. **Required before tagging a release**, because otherwise legacy rows stay plaintext.
3. Add US4: a key change no longer breaks integrations silently.
4. Add US5 (README) and Polish (leak test), then open the PR to `dev`.

### Commit hygiene

The Prettier reformat (T005) is its own commit, with no logic changes mixed in. Use one commit per task or tightly related task group.
