# Research: Sprache pro Nutzer für Oberfläche und Rezepte

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-10-02

## R1 – Frontend localization approach (FR-011, FR-014, FR-015, FR-020)

- **Decision**: A small in-house i18n module in `frontend/src/lib/i18n/`, no new dependency.
  - One TypeScript dictionary per locale (`messages/en.ts`, `de.ts`, `es.ts`, `fr.ts`, `it.ts`). `en.ts` is the source; every other dictionary is declared as `const de: Messages = { … }`, where `Messages` is derived from the type of `en`.
  - Messages are plain strings or small functions for interpolation and plurals, e.g. `jobs_runningFor: (p: { time: string }) => \`Running for ${p.time}\``.
  - A writable store `locale` and a derived store `t = derived(locale, (l) => dictionaries[l])`. Components use `$t.key` or `$t.key({ … })`.
  - Changing `locale` re-renders every component that reads `$t` at once, with no page reload, so unsaved editor state and running polls survive a language change.
- **Rationale**:
  - The app is small (~2.9k lines of Svelte/TS, an estimated 250–300 UI strings). A typed dictionary covers that without build plugins.
  - **Completeness is enforced by the compiler**: a missing or extra key in `de.ts` is a type error, so `npm run check` (already in CI) fails. That satisfies FR-020 and SC-005 without extra tooling.
  - Switching without reload matches the spec scenario "wechselt ohne Neuladen" (US2 scenario 2, SC-003).
- **Alternatives considered**:
  - **Paraglide JS 2** (`/opral/paraglide-js`, the official SvelteKit add-on). Compiler-based and tree-shakable, but `setLocale()` reloads the document by default; `reload: false` is documented as an escape hatch that does not re-render the framework, so we would still need our own reactive layer. Missing translations silently fall back to the base locale; detecting them needs the inlang lint tooling. Rejected: more moving parts for this size.
  - **svelte-i18n**: runtime ICU messages and a store API, but no type safety for keys and no compile-time completeness check. Rejected.
- **FR-015 (fallback to English)**: Satisfied by construction because every dictionary must be complete. If a key is ever added to `en.ts` only, the build fails instead of showing a placeholder.

## R2 – Language codes and one shared list (FR-002)

- **Decision**: ISO 639-1 codes `en`, `de`, `es`, `fr`, `it` everywhere: user language, UI locale, and job target language.
  - Backend: `jarit/languages.py` with `class Language(str, Enum)` and `PROMPT_NAMES = {Language.EN: "English", Language.DE: "German", …}` for the LLM prompt.
  - Frontend: `frontend/src/lib/i18n/languages.ts` with the same five codes and native display names (`English`, `Deutsch`, `Español`, `Français`, `Italiano`).
  - A unit test in the backend pins the code list; the frontend type `Locale` is the union of the same codes. The contract ([contracts/http-api.md](./contracts/http-api.md)) is the reference for both.
- **Rationale**: Codes are stable, short and map directly to `Intl` locales and `navigator.languages`. Today the job stores free-text English names (`"english"`); one list for all three uses removes the mismatch.
- **Alternatives considered**: Keep the English names (`english`, `german`, …) as values. Rejected: they don't match browser locale tags and would need a second mapping for `Intl`.

## R3 – Target language of jobs (FR-007 – FR-010, FR-008a)

- **Decision**:
  - `POST /extraction-jobs` accepts `target_language` as an optional `Language` code. If it is omitted or `null`, the server uses the caller's stored language (FR-009). Any other value → `422`.
  - The job stores the code. The pipeline turns it into an English language name for the prompt (`"The target language is German."`), so the agent prompt and its behaviour stay as today. The agent already translates the complete recipe into the target language (FR-008a); no prompt change beyond the name mapping.
  - Migration `0004_user_language` rewrites existing job values `english/german/spanish/french/italian` to their codes. Other legacy values (only possible via direct API calls) stay as they are; the pipeline passes an unknown value through unchanged, so a retry of such a job behaves as before.
- **Rationale**: Server-side default is the only way to satisfy FR-009 for API clients that omit the field; storing codes keeps the job consistent with the user language.
- **Alternatives considered**: Default only in the frontend. Rejected: FR-009 explicitly covers submissions without a language.

## R4 – Storing the user language (FR-001, FR-004 – FR-006)

- **Decision**: New column `users.language VARCHAR(8) NOT NULL DEFAULT 'en'` with a check constraint on the five codes, added by Alembic revision `0004_user_language`. Existing rows get `en` through the server default (FR-006).
  - `GET /users/me` returns `language`.
  - New `PATCH /users/me` with body `{ "language": "de" }` changes only the caller's own language (FR-005: there is no user id in the path). Unsupported value → `422`, nothing changes (FR-004).
  - `POST /auth/register` accepts an optional `language` (default `en`, FR-017).
  - Admin endpoints never change another user's language (spec assumption).
- **Rationale**: One column, one self-service endpoint; the check constraint makes invalid values impossible even outside the API.
- **Alternatives considered**: A generic `user_settings` key/value table. Rejected: one setting does not justify it (YAGNI).

## R5 – Locale resolution in the browser (FR-014, FR-016, FR-018)

- **Decision**: The `locale` store is resolved in this order:
  1. Logged in and the profile is loaded → `user.language` (FR-018).
  2. Otherwise → the first entry of `navigator.languages` whose primary subtag is supported (`de-AT` → `de`), else `en` (FR-016).
  - The root layout sets the locale from `navigator.languages` before first render, then switches to `user.language` once `GET /users/me` returns. Login and register forms set it from the login response's follow-up profile load.
  - Changing the language in settings sends `PATCH /users/me`; only on success are `user` and `locale` updated. On failure the error is shown and both stay unchanged (edge case "Speichern schlägt fehl").
  - On logout, the locale falls back to the browser language.
  - `document.documentElement.lang` follows the `locale` store, so screen readers and the browser use the right language.
  - The language is not written to `localStorage`; the server is the only source of truth for logged-in users (FR-001: device-independent). Other open tabs pick up the change on their next reload (edge case "Mehrere offene Tabs").
- **Rationale**: Matches spec priorities exactly with no extra persistence.
- **Alternatives considered**: Cache the language in `localStorage` to avoid a flash of browser-language text before `/users/me` returns. Rejected for now: the profile request already gates the authenticated UI; revisit only if the flash is visible.

## R6 – Translating error messages (FR-012)

- **Decision**: Error responses get a stable machine-readable `code` next to the existing English `detail`:
  - New `jarit/api/errors.py` with `class AppError(HTTPException)` that takes `code` and an exception handler that returns `{"detail": "<English text>", "code": "<CODE>"}`. All 21 current `HTTPException` sites move to `AppError` with a code from the list in [contracts/http-api.md](./contracts/http-api.md#error-codes).
  - FastAPI validation errors (`422`) keep their shape; the frontend maps them to one generic translated message per form, and the forms validate input client-side first (URL, password length, email) so users normally see field-specific translated messages.
  - Frontend: `ApiError` gets an optional `code`. `request()` no longer writes server text into the `error` store; it writes a translated message from `errorMessage(err, $t)`: known `code` → its message key; otherwise a generic message per status class (`401`, `403`, `404`, `409`, `422`, `5xx`, network).
  - Job failure reasons and statuses are already codes (`FAILED/LLM_ERROR`, …); `STATUS_LABELS`/`FAILURE_REASON_LABELS` in `jobs.ts` move into the dictionaries.
  - The English `detail` stays for logs, API clients and backwards compatibility.
- **Rationale**: Translating by matching English `detail` strings would silently break when a text changes. Codes are a stable contract that a backend test can pin.
- **Alternatives considered**:
  - Translate on the server using the user's language. Rejected: the UI must also translate client-side errors (network, session expired) and pre-login errors, so one place (the frontend) is simpler.
  - Map only by HTTP status. Rejected: `409` alone does not tell "cannot retry" from "cannot delete".

## R7 – Dates and numbers (FR-013)

- **Decision**: A helper `formatDateTime(value, locale)` / `formatDate(value, locale)` in `frontend/src/lib/i18n/format.ts` using `Intl.DateTimeFormat(locale, …)`. All current `toLocaleString()` / `toLocaleDateString()` calls (history, editor, admin panel) use it. Durations ("Running for 1 min 5 s") come from dictionary functions.
- **Rationale**: `Intl` ships with every supported browser; no library needed.

## R8 – Where the setting lives in the UI (FR-003, FR-017)

- **Decision**:
  - Dashboard: a new component `LanguageSettings.svelte` next to `MealieConfig.svelte`, with a select of the five native names and immediate save on change (with a short "Saved" confirmation).
  - Register form: a language select, preselected with the current `locale`; changing it also switches the registration page's language immediately.
  - Recipe submission (`RecipeExtractor.svelte`): the target language select uses the same list and is preselected with `$user.language`; changing it affects only that submission (FR-008).
- **Rationale**: Reuses the existing settings area (spec assumption) and avoids a new route.
