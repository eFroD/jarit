---

description: "Task list for per-user language (UI localization and default recipe language)"
---

# Tasks: Sprache pro Nutzer für Oberfläche und Rezepte

**Input**: Design documents from `specs/003-user-language/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Included for the backend. CI must keep ≥ 80 % coverage (FR-019). The frontend has no test runner; dictionary completeness (FR-020) is enforced by `npm run check` through the `Messages` type, and the UI is validated with [quickstart.md](./quickstart.md) §4.

**Organization**: Tasks are grouped by user story (US1–US3 from spec.md), so each story can be implemented and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on unfinished tasks)
- **[Story]**: The user story the task belongs to

## Path Conventions

Web app with the backend at the repo root (`main.py`, `jarit/`, `tests/`) and the frontend in `frontend/`. Shared names used throughout:

- Language codes: `en`, `de`, `es`, `fr`, `it` (in this order everywhere). Backend `jarit.languages.Language`; frontend `Locale` in `frontend/src/lib/i18n/languages.ts`.
- Prompt names: `English`, `German`, `Spanish`, `French`, `Italian`.
- Native names: `English`, `Deutsch`, `Español`, `Français`, `Italiano`.
- Migration: `jarit/db/migrations/versions/0004_user_language.py`, `revision = "0004_user_language"`, `down_revision = "0003_job_started_at"`.
- Error body: `{"detail": "<English text>", "code": "<CODE>"}`; codes and statuses in [contracts/http-api.md](./contracts/http-api.md#error-codes).
- Dictionary keys: flat `area_name` (e.g. `nav_history`, `jobs_status_QUEUED`, `error_JOB_NOT_FOUND`); rules in [contracts/ui-i18n.md](./contracts/ui-i18n.md#rules).
- Test DB: `DATABASE_URL=postgresql://jarit:jarit@localhost:55432/jarit_test` (see [quickstart.md](./quickstart.md) §1).

---

## Phase 1: Setup

- [X] T001 Start the throwaway Postgres from [quickstart.md](./quickstart.md) §1 and run the full backend tests, `uv run ruff check .`, and in `frontend/` `npm run lint` and `npm run check`, so the baseline is known to be green before any change.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: Language codes, the schema change, error codes and the frontend i18n module. Every story depends on these.

### Tests for the foundation

- [X] T002 [P] Create `tests/unit/test_languages.py`:
  - `[l.value for l in Language] == ["en", "de", "es", "fr", "it"]`
  - `prompt_name("de") == "German"` for all five codes
  - `prompt_name("japanese") == "japanese"` (unknown legacy values pass through)
- [X] T003 [P] In `tests/db/test_migrations.py`:
  - set `HEAD = "0004_user_language"` (all existing head assertions use it)
  - new `test_upgrade_from_0003_sets_user_language_and_job_codes(schema_engine)`: `command.upgrade(cfg, "0003_job_started_at")`, insert one user and jobs with `target_language` `'english'`, `'German'`, `'italian'` and `'japanese'`; run `run_migrations`; the user's `language` is `'en'`; jobs are `'en'`, `'de'`, `'it'`, `'japanese'`; inserting a user with `language = 'pt'` raises `IntegrityError`
  - extend `test_downgrade_to_base_and_back` only if it needs the new head name
- [X] T004 [P] Create `tests/unit/test_error_codes.py`:
  - `ErrorCode` values equal the 19 codes of the contract table, in that order
  - a minimal FastAPI app with the handler from `jarit.api.errors` and one route raising `AppError(409, ErrorCode.JOB_NOT_RETRYABLE, "Only failed extractions can be retried")` returns `409` and exactly `{"detail": "Only failed extractions can be retried", "code": "JOB_NOT_RETRYABLE"}`
  - a plain `HTTPException` still returns `{"detail": …}` only

### Backend implementation

- [X] T005 [P] Create `jarit/languages.py`: `class Language(str, Enum)` with `EN = "en"`, `DE = "de"`, `ES = "es"`, `FR = "fr"`, `IT = "it"`; `PROMPT_NAMES: dict[Language, str]`; `LEGACY_NAMES = {"english": "en", "german": "de", "spanish": "es", "french": "fr", "italian": "it"}`; `def prompt_name(value: str) -> str` returning `PROMPT_NAMES[Language(value)]` or `value` if it is not a code.
- [X] T006 Create `jarit/db/migrations/versions/0004_user_language.py` (values spelled out, not imported, like `0002`):
  - upgrade: `op.add_column("users", sa.Column("language", sa.String(8), nullable=False, server_default="en"))`; `op.create_check_constraint("ck_users_language", "users", "language IN ('en','de','es','fr','it')")`; `UPDATE extraction_jobs SET target_language = CASE lower(target_language) WHEN 'english' THEN 'en' WHEN 'german' THEN 'de' WHEN 'spanish' THEN 'es' WHEN 'french' THEN 'fr' WHEN 'italian' THEN 'it' ELSE target_language END`
  - downgrade: map the five codes back to the lowercase English names, drop the constraint, drop the column
- [X] T007 In `jarit/db/models/users.py`, add `language = Column(String(8), nullable=False, server_default="en")` and `__table_args__ = (CheckConstraint("language IN ('en','de','es','fr','it')", name="ck_users_language"),)`.
- [X] T008 Create `jarit/api/errors.py`:
  - `class ErrorCode(str, Enum)` with the 19 codes from [contracts/http-api.md](./contracts/http-api.md#error-codes) in table order
  - `class AppError(HTTPException)` with `__init__(self, status_code: int, code: ErrorCode, detail: str)` storing `self.code`
  - `async def app_error_handler(request, exc: AppError) -> JSONResponse` returning `{"detail": exc.detail, "code": exc.code.value}` with `exc.headers`
  - register it in `main.py` with `app.add_exception_handler(AppError, app_error_handler)` next to the router setup
- [X] T009 Replace every `HTTPException` raised by the application with `AppError` and the code from the contract, keeping status and English `detail` unchanged:
  - `jarit/api/v1/endpoints/users.py` (`INVALID_TOKEN`, `USER_NOT_FOUND` ×2, `ADMIN_REQUIRED`, `API_KEY_NOT_FOUND` ×2, `CANNOT_DELETE_SELF`; keep `WWW-Authenticate` headers if any)
  - `jarit/api/v1/endpoints/auth.py` (`INVALID_CREDENTIALS`)
  - `jarit/auth/service.py` (`REGISTRATION_DISABLED`, `EMAIL_TAKEN`, `USERNAME_TAKEN`)
  - `jarit/api/v1/endpoints/extraction_jobs.py` (`JOB_NOT_FOUND` ×2, `JOB_NOT_EDITABLE`, `JOB_NOT_UPLOADABLE`, `MEALIE_ERROR`, `JOB_NOT_RETRYABLE`, `JOB_NOT_DELETABLE`)
  - `jarit/api/v1/endpoints/integrations.py` (`MEALIE_NOT_CONFIGURED`, `MEALIE_URL_NOT_CONFIGURED`, `MEALIE_CREDENTIALS_UNREADABLE`); the `verify-mealie-user` `JSONResponse` gets `"code": "MEALIE_INVALID_CREDENTIALS"` added to its content
  - `grep -rn "HTTPException(" jarit` afterwards finds only `jarit/api/errors.py`
- [X] T010 Update existing tests that compare whole error bodies: in `tests/db/test_extraction_jobs_endpoints.py`, `NOT_FOUND = {"detail": "Extraction job not found", "code": "JOB_NOT_FOUND"}` and the retry assertion includes `"code": "JOB_NOT_RETRYABLE"`; add `assert response.json()["code"] == "JOB_NOT_DELETABLE"` to the delete test and `== "MEALIE_CREDENTIALS_UNREADABLE"` in `tests/db/test_api_keys_endpoints.py`. Run the backend tests: T002–T004 and all existing tests pass.

### Frontend foundation

- [X] T011 [P] Create `frontend/src/lib/i18n/languages.ts`: `export type Locale = 'en' | 'de' | 'es' | 'fr' | 'it'`; `export const LANGUAGES: { code: Locale; name: string }[]` with the native names; `export const DEFAULT_LOCALE: Locale = 'en'`; `export function isLocale(v: unknown): v is Locale`; `export function matchLocale(tags: readonly string[]): Locale` (first tag whose primary subtag, lower-cased, is a `Locale`; else `'en'`).
- [X] T012 [P] Create `frontend/src/lib/i18n/format.ts`: `formatDate(value: string | Date, locale: Locale)` (`dateStyle: 'medium'`), `formatDateTime(...)` (`dateStyle: 'medium', timeStyle: 'short'`), both via `Intl.DateTimeFormat`.
- [X] T013 Create the dictionaries:
  - `frontend/src/lib/i18n/messages/en.ts`: `export const en = { … }` starting with the keys needed by T014 (`error_generic`, `error_network`, `error_401`, `error_403`, `error_404`, `error_409`, `error_422`, `error_5xx`, `app_title`) and one `error_<CODE>` key per contract code (English texts based on the current `detail`s, user-friendly, no technical details); `export type Messages = { [K in keyof typeof en]: (typeof en)[K] extends (...a: infer A) => string ? (...a: A) => string : string }`.
  - `de.ts`, `es.ts`, `fr.ts`, `it.ts`: `import type { Messages } from './en'; export const de: Messages = { … }` with the same keys, translated.
- [X] T014 Create `frontend/src/lib/i18n/index.ts`:
  - `browserLocale()` = `matchLocale(navigator.languages)` in the browser, `'en'` otherwise
  - `export const locale = writable<Locale>(browserLocale())`; `export const t = derived(locale, (l) => dictionaries[l])`
  - subscribe to the `user` store from `$lib/store`: when a user with a valid `language` is set, `locale.set(user.language)`; when it becomes `null`, `locale.set(browserLocale())` (covers FR-018 and logout)
  - subscribe to `locale` and set `document.documentElement.lang` in the browser
  - `export function errorMessage(err: unknown, m: Messages): string` following [contracts/ui-i18n.md](./contracts/ui-i18n.md#error-messages)
- [X] T015 In `frontend/src/lib/types.ts`, add `language: Locale` to `User`. In `frontend/src/lib/api.ts`: `ApiError` gets `public code?: string`; `request()` reads `errorData.code`; `fetch` network failures are rethrown as-is. Do not change user-visible text yet (that is T034).

**Checkpoint**: Backend tests green, `npm run check` green; the app still looks exactly as before.

---

## Phase 3: User Story 1 – Rezepte standardmäßig in der eigenen Sprache (Priority: P1) 🎯 MVP

**Goal**: The user can store a language, and new extractions use it as the default target language (form preselection and server default).

**Independent Test**: [quickstart.md](./quickstart.md) §3 and §4 step 7: set the language to `de`, the form preselects Deutsch, a submission without a language is stored as `de`, choosing Italian for one job does not change the user language.

### Tests for User Story 1

- [X] T016 [P] [US1] Create `tests/db/test_user_language.py`:
  - `GET /api/v1/users/me` returns `language == "en"` for a new user
  - `PATCH /api/v1/users/me {"language": "de"}` → `200`, body `language == "de"`; a following `GET` returns `de`
  - `PATCH` with `"pt"`, `"german"`, `""` and `{}` → `422`; the stored language is unchanged
  - a `PATCH` by `user` does not change `other_user` (read from the DB)
  - the admin user list includes `language` (use `admin_user` with `act_as`)
- [X] T017 [P] [US1] In `tests/db/test_extraction_jobs_endpoints.py`:
  - change the helper `queued_job` and the submit test to codes (`"en"`, `"de"`)
  - replace `test_target_language_defaults_to_english` with `test_target_language_defaults_to_user_language`: set `user.language = "fr"` in the DB, submit without `target_language` → stored and returned `"fr"`; same with `"target_language": null`
  - `test_invalid_input_creates_no_job` parameters: `"   "`, `"english"`, `"japanese"`, `"x" * 65` → `422`, no job
  - new `test_user_language_change_keeps_job_language` (FR-010): submit with `de`, `PATCH /users/me {"language": "it"}`, the job still has `de`
- [X] T018 [P] [US1] In `tests/unit/test_extraction_pipeline.py`, add a test that `pipeline.extract(URL, "de", report)` sends a user prompt containing `"The target language is German."` (capture the first `UserPromptPart` in the scripted `FunctionModel`), and one with `"japanese"` that contains `"japanese"`. Change the existing call from `"english"` to `"en"`.

### Implementation for User Story 1

- [X] T019 [US1] In `jarit/api/v1/endpoints/users.py`:
  - `UserResponse` gets `language: Language`; `get_current_user_profile` passes `language=current_user.language`
  - new `class UserUpdate(BaseModel): language: Language`
  - new `@router.patch("/me", response_model=UserResponse)` that sets `current_user.language = body.language.value`, commits, refreshes, and returns the same shape as `GET /me`
- [X] T020 [US1] In `jarit/jobs/models.py`, change `ExtractionJobCreate.target_language` to `Language | None = None` and remove the `target_language_not_blank` validator. In `jarit/api/v1/endpoints/extraction_jobs.py` `submit_extraction`, store `request.target_language.value if request.target_language else current_user.language`.
- [X] T021 [US1] In `jarit/jobs/pipeline.py`, build the prompt with `prompt_name(target_language)` from `jarit.languages`. In `jarit/models/input_models/video.py`, change the default `"english"` to `"en"` if the model is still used; otherwise leave it.
- [X] T022 [US1] In `frontend/src/lib/api.ts`: add `updateMe(language: Locale): Promise<User>` (`PATCH /users/me`); change `createExtractionJob(url: string, targetLanguage?: Locale)` to send `target_language` only when given.
- [X] T023 [US1] In `frontend/src/lib/components/RecipeExtractor.svelte`: build the target language `<select>` from `LANGUAGES` (native names, no flags needed); `let targetLanguage: Locale | null = null`; `$: selected = targetLanguage ?? $user?.language ?? 'en'`; bind the select to `selected` and set `targetLanguage` on change; submit with `selected`. After a successful submit, reset `targetLanguage = null` so the next form shows the user's language again.
- [X] T024 [US1] Create `frontend/src/lib/components/LanguageSettings.svelte`: card styled like `MealieConfig.svelte` with a `<select>` of `LANGUAGES` bound to the current `$user.language`; on change call `api.updateMe(code)`; on success `user.set(updated)` (which switches the locale via T014) and show a short saved hint; on error show `errorMessage(err, $t)` and reset the select to `$user.language`. Add it to `frontend/src/routes/(app)/dashboard/+page.svelte` next to `MealieConfig`. Texts can be English literals here; T029 moves them into the dictionary.

**Checkpoint**: US1 works end to end; backend tests green.

---

## Phase 4: User Story 2 – Oberfläche in der eigenen Sprache (Priority: P1)

**Goal**: Every UI text appears in the user's language and switches at once when it changes.

**Independent Test**: [quickstart.md](./quickstart.md) §4 steps 3–6, 8, 9: switch to Deutsch, walk all pages, no English UI text left, dates in German format, errors translated, still logged in.

All tasks in this phase edit `messages/en.ts`, so run T025–T034 in order. For each component: replace every visible string (text nodes, `placeholder`, `title`, `aria-label`, `alt`, `confirm()`/`alert()` texts, `<svelte:head>` titles) with `$t.<key>` / `$t.<key>({ … })`, add the keys to `en.ts`, and replace every `toLocaleString()`/`toLocaleDateString()` with `formatDateTime`/`formatDate` from `format.ts` and `$locale`. Leave `de/es/fr/it` for T035–T038; until then add the new keys to them with the English text so `npm run check` stays green.

- [X] T025 [US2] `frontend/src/routes/+layout.svelte` (`<title>`, meta description), `frontend/src/routes/+page.svelte`, `frontend/src/lib/components/Navigation.svelte` (keys `app_*`, `nav_*`).
- [X] T026 [US2] `frontend/src/lib/components/LoginForm.svelte`, `frontend/src/lib/components/RegisterForm.svelte` and their pages (keys `login_*`, `register_*`), including client-side validation messages.
- [X] T027 [US2] `frontend/src/routes/(app)/dashboard/+page.svelte`, `frontend/src/lib/components/RecipeExtractor.svelte` (keys `dashboard_*`, `extract_*`).
- [X] T028 [US2] `frontend/src/lib/components/MealieConfig.svelte` including the delete `confirm()` and "Last updated" date (keys `mealie_*`).
- [X] T029 [US2] `frontend/src/lib/components/LanguageSettings.svelte` (keys `language_*`).
- [X] T030 [US2] `frontend/src/lib/jobs.ts`: remove `STATUS_LABELS`/`FAILURE_REASON_LABELS`; add `statusLabel(status, m: Messages)` and `failureLabel(reason, m: Messages)` that read `m['jobs_status_' + status]` / `m['jobs_failure_' + reason]` (keys for all 6 statuses and 7 reasons in `en.ts`). Update `frontend/src/lib/components/JobProgress.svelte` (stage names, "Running for" via a dictionary function taking minutes and seconds, buttons, hints) and `frontend/src/lib/components/ActiveJobs.svelte`, and the pages under `frontend/src/routes/(app)/jobs/`.
- [X] T031 [US2] `frontend/src/lib/components/JobHistory.svelte` and `frontend/src/routes/(app)/history/+page.svelte`: labels, empty state, delete `confirm()` (function with `{ name }`), dates, "In Mealie" (keys `history_*`).
- [X] T032 [US2] `frontend/src/lib/components/RecipePreview.svelte`: all labels and placeholders except the ISO duration examples (`PT15M`), the re-upload `confirm()` (function with `{ date }`), saved/unsaved indicator, "In Mealie since", load error texts (use `error_JOB_NOT_FOUND`), success message (keys `editor_*`). Recipe field values stay untouched.
- [X] T033 [US2] `frontend/src/lib/components/AdminPanel.svelte` and `frontend/src/routes/(app)/admin/+page.svelte`: labels, table headers, sort options, role names, delete `confirm()`, dates (keys `admin_*`).
- [X] T034 [US2] Errors in `frontend/src/lib/api.ts`:
  - `request()` sets `error` to `errorMessage(err, get(t))` instead of the server text, also for the `401` case
  - on `401`, log out only when `code` is missing, `INVALID_TOKEN` or `USER_NOT_FOUND`; otherwise just throw the `ApiError`
  - `login()` throws `ApiError` with the response's code (`INVALID_CREDENTIALS`) and sets the translated message
  - components that build their own error text (e.g. `RecipePreview` `loadError`, `JobProgress` 404 handling, `MealieConfig` verify) use `errorMessage` or the matching `error_*` key
- [X] T035 [P] [US2] Translate every key in `frontend/src/lib/i18n/messages/de.ts` (German, informal "du" consistent with a personal app; keep placeholders/function signatures).
- [X] T036 [P] [US2] Translate every key in `frontend/src/lib/i18n/messages/es.ts` (Spanish).
- [X] T037 [P] [US2] Translate every key in `frontend/src/lib/i18n/messages/fr.ts` (French).
- [X] T038 [P] [US2] Translate every key in `frontend/src/lib/i18n/messages/it.ts` (Italian).
- [X] T039 [US2] Leftover check: `grep -rnE ">[^<{}]*[A-Za-z]{3,}[^<{}]*<|placeholder=\"[A-Za-z]|confirm\\(['\`]|title=\"[A-Za-z]" frontend/src --include=*.svelte` and review `.ts` files for literal UI strings; fix every hit except recipe content, `PT15M`-style examples and brand names (JarIt, Mealie). Then `npm run lint`, `npm run check`, `npm run build` in `frontend/`.

**Checkpoint**: US1 and US2 work together; switching the language changes the whole UI without reload.

---

## Phase 5: User Story 3 – Sinnvolle Sprache ab dem ersten Besuch (Priority: P2)

**Goal**: Visitors see login/register in their browser language, and a new account starts with the language chosen at registration.

**Independent Test**: [quickstart.md](./quickstart.md) §4 steps 1–2: German browser → German login page; register without changing the select → account language `de`.

### Tests for User Story 3

- [X] T040 [P] [US3] In `tests/db/test_user_language.py`, add registration tests against `POST /api/v1/auth/register` (no auth override needed; use a client without `act_as` or clear overrides): with `"language": "de"` → `201`, response and DB `language == "de"`; without `language` → `"en"`; with `"pt"` → `422` and no user created.

### Implementation for User Story 3

- [X] T041 [US3] In `jarit/auth/schemas.py`, add `language: Language = Language.EN` to `UserCreate` and `language: Language` to `UserResponse`. In `jarit/auth/service.py` `create_user`, store `language=user.language.value`.
- [X] T042 [US3] In `frontend/src/lib/api.ts`, `register(email, username, password, language: Locale)` sends `language`. In `frontend/src/lib/components/RegisterForm.svelte`, add a language `<select>` (from `LANGUAGES`, label from the dictionary) bound to `$locale`, so changing it switches the page at once; send `$locale` with the registration.
- [X] T043 [US3] Verify the pre-login path: with no token, `frontend/src/routes/+layout.svelte` renders login/register in `browserLocale()` (from T014) and nothing overrides it; after login, `LoginForm.svelte` sets `user`, which switches to the stored language (FR-018). Fix any place that resets the locale unexpectedly.

**Checkpoint**: All three stories work together.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T044 [P] Update `README.md`: users choose their language (Dashboard → Language); supported languages; the default target language follows it; how to add a UI text (add the key to `en.ts`, then to all other dictionaries, `npm run check` enforces it); API clients get a `code` in error responses.
- [X] T045 Run [quickstart.md](./quickstart.md) §1 completely, including the completeness check (remove one key from `de.ts`, `npm run check` fails, restore). Fix findings. Coverage must stay ≥ 80 %.
- [ ] T046 Validate [quickstart.md](./quickstart.md) §2–§4 manually (upgrade, API, browser walkthrough) and §5 if real keys are available.
  - *Covered by automated tests on 2026-10-03:* §2 (upgrade, `tests/db/test_migrations.py`) and §3 (API behaviour, `tests/db/test_user_language.py`, `tests/db/test_extraction_jobs_endpoints.py`, `tests/unit/test_error_codes.py`).
  - *Open:* §4 browser walkthrough and §5 with real LLM keys.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: depends on Phase 1; blocks all stories. Inside: T005 → T006/T007 → T003 passes; T008 → T009 → T010; T011/T012 → T013 → T014 → T015.
- **US1 (Phase 3)**: depends on Phase 2. MVP.
- **US2 (Phase 4)**: depends on Phase 2; uses `LanguageSettings` from T024 (T029) and the API from T022, so do it after US1.
- **US3 (Phase 5)**: depends on Phase 2; T042 touches `RegisterForm.svelte` after T026 if US2 is done first (recommended).
- **Polish (Phase 6)**: after all stories.

### Within each story

- Tests first, and they must fail before the implementation.
- Backend before frontend for the same feature (the frontend calls the new API).
- T025–T034 are sequential (shared `en.ts`); T035–T038 are parallel (one file each).

### Parallel opportunities

- Phase 2: T002, T003, T004 together; T005, T011, T012 together.
- US1: T016, T017, T018 together.
- US2: T035, T036, T037, T038 together.
- US3: T040 in parallel with any frontend task.
- T044 in parallel with T045.

## Parallel Example: User Story 2 translations

```text
Task: "Translate every key in frontend/src/lib/i18n/messages/de.ts"
Task: "Translate every key in frontend/src/lib/i18n/messages/es.ts"
Task: "Translate every key in frontend/src/lib/i18n/messages/fr.ts"
Task: "Translate every key in frontend/src/lib/i18n/messages/it.ts"
```

## Implementation Strategy

### MVP first (User Story 1)

1. Phase 1 + Phase 2.
2. Phase 3 (US1). **Stop and validate**: language stored, default target language works through UI and API.
3. Deployable on its own: the UI is still English, but recipes come in the user's language by default.

### Incremental delivery

1. + US2: full localization (the biggest chunk: string extraction and four translations).
2. + US3: browser language before login and language at registration.
3. Polish: README, full checks, manual validation.
