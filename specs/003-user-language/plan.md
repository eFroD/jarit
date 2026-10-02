# Implementation Plan: Sprache pro Nutzer für Oberfläche und Rezepte

**Branch**: `feature/003-user-language` (from `dev` at `b148fd1`) | **Date**: 2026-10-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-user-language/spec.md`

## Summary

Every user gets a stored `language` (`en`, `de`, `es`, `fr`, `it`; default `en`). It drives two things:

- **UI language**: the SvelteKit frontend is localized into all five languages with a small in-house i18n module: one typed dictionary per locale and a reactive `t` store. A missing translation is a type error, so the existing `npm run check` in CI enforces completeness. Switching the language re-renders at once, without reload or re-login. Before login, the browser language is used ([R1](./research.md#r1--frontend-localization-approach-fr-011-fr-014-fr-015-fr-020), [R5](./research.md#r5--locale-resolution-in-the-browser-fr-014-fr-016-fr-018)).
- **Default target language**: the extraction form preselects the user's language, and `POST /extraction-jobs` without `target_language` uses it on the server. Jobs store language codes; the pipeline maps them to English names for the unchanged agent prompt, which already translates the whole recipe ([R3](./research.md#r3--target-language-of-jobs-fr-007--fr-010-fr-008a)).

Backend changes: column `users.language` and a code rewrite of existing job languages in Alembic revision `0004_user_language`; `PATCH /users/me`; optional `language` on register; and a stable error `code` on every application error so the frontend can translate server errors ([R6](./research.md#r6--translating-error-messages-fr-012)). As a side effect, the frontend stops logging users out on Mealie-related `401`s.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript / Svelte 5 with SvelteKit static adapter (frontend), Node 24

**Primary Dependencies**: FastAPI 0.118, SQLAlchemy 2.0, Alembic, Pydantic 2. Frontend: SvelteKit 2, Tailwind 4. **No new dependencies**; dates use the built-in `Intl` API.

**Storage**: PostgreSQL. Revision `0004_user_language`: `users.language VARCHAR(8) NOT NULL DEFAULT 'en'` with check constraint; data update of `extraction_jobs.target_language` ([data-model.md](./data-model.md)).

**Testing**: pytest + pytest-cov (DB tests in `tests/db/` against Postgres, unit tests in `tests/unit/`). Frontend has no test runner; type checking (`svelte-check`) enforces dictionary completeness, and the quickstart covers the UI manually.

**Target Platform**: Linux containers (Docker Compose), modern browsers with `Intl` and `navigator.languages`

**Project Type**: Web application (FastAPI backend in `jarit/` + `main.py`, SvelteKit frontend in `frontend/`)

**Performance Goals**: A language switch is visible in < 1 s (SC-003): one `PATCH` plus a store update; no reload.

**Constraints**:
- No UI text outside the dictionaries ([contracts/ui-i18n.md](./contracts/ui-i18n.md#rules)).
- Existing users and jobs keep working unchanged (SC-004).
- Coverage stays ≥ 80 % (FR-019).
- Job `target_language` is never changed after creation (FR-010).

**Scale/Scope**: 5 locales × an estimated 250–300 UI strings; ~15 Svelte components and `api.ts`/`jobs.ts`; 21 backend error sites get a code.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, so there are no ratified principles to check. **PASS (vacuous).**

The plan follows the conventions of 001 and 002:
- flat `jarit/` package, FastAPI dependencies for auth, owner-scoped endpoints
- schema changes only through Alembic, applied at startup
- DB tests in `tests/db/`, coverage gate in CI
- no secrets or technical details in user-facing messages

**Post-design re-check**: still PASS. No new projects, no new dependencies, one new table column.

## Project Structure

### Documentation (this feature)

```text
specs/003-user-language/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R8
├── data-model.md        # Phase 1: Language, User.language, job language codes, migration
├── quickstart.md        # Phase 1: validation guide
├── contracts/
│   ├── http-api.md      # PATCH /users/me, language fields, error codes
│   └── ui-i18n.md       # i18n module, rules, locale lifecycle, affected screens
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
jarit/
├── languages.py                         # NEW: Language enum, PROMPT_NAMES, prompt_name()
├── api/
│   ├── errors.py                        # NEW: AppError(HTTPException) + handler adding "code"
│   └── v1/endpoints/
│       ├── users.py                     # language in UserResponse, PATCH /users/me, AppError
│       ├── auth.py                      # AppError
│       ├── extraction_jobs.py           # default target language from user, AppError
│       └── integrations.py              # AppError, MEALIE_INVALID_CREDENTIALS code
├── auth/
│   ├── schemas.py                       # UserCreate.language
│   └── service.py                       # store language, AppError
├── db/
│   ├── models/users.py                  # language column + check constraint
│   └── migrations/versions/
│       └── 0004_user_language.py        # NEW
└── jobs/
    ├── models.py                        # ExtractionJobCreate.target_language: Language | None
    └── pipeline.py                      # prompt_name(target_language)
main.py                                  # register AppError handler

tests/
├── unit/test_languages.py               # NEW: code list, prompt_name incl. legacy values
├── unit/test_extraction_pipeline.py     # prompt uses the language name
└── db/
    ├── test_user_language.py            # NEW: me, PATCH, register, isolation
    ├── test_extraction_jobs_endpoints.py # default from user, explicit code, 422, FR-010
    ├── test_error_codes.py              # NEW: every contract code/status pinned
    └── test_migrations.py               # head 0004, backfill users, job code rewrite, downgrade

frontend/src/
├── lib/
│   ├── i18n/                            # NEW: index.ts, languages.ts, format.ts, messages/{en,de,es,fr,it}.ts
│   ├── api.ts                           # ApiError.code, updateMe(), register(language), translated errors
│   ├── jobs.ts                          # labels moved into dictionaries
│   ├── types.ts                         # User.language, Locale
│   ├── store.ts                         # logout resets locale
│   └── components/
│       ├── LanguageSettings.svelte      # NEW
│       └── *.svelte                     # all texts via $t
└── routes/+layout.svelte                # initial locale, <html lang>, <title>

README.md                                # language setting, supported languages, how to add a translation key
```

**Structure Decision**: Existing web-application layout (`jarit/` backend, `frontend/` SvelteKit). The only new folders are `frontend/src/lib/i18n/` and its `messages/` subfolder.

## Implementation Order (for /speckit-tasks)

1. **Foundation**: `jarit/languages.py`, migration `0004`, model column, `AppError` + handler (with test pinning the codes). Frontend `i18n/` module with `en.ts` and empty-shell structure.
2. **US1 (P1)**: user language in API (`GET`/`PATCH /users/me`), server default for `target_language`, pipeline mapping; frontend target-language select preselected from `$user.language` and a minimal `LanguageSettings`.
3. **US2 (P1)**: move every UI string into `en.ts`, then add `de`, `es`, `fr`, `it`; error translation; date formatting; `<html lang>`; logout only on session `401`.
4. **US3 (P2)**: browser locale before login, language select on register, `language` on register.
5. **Polish**: README, full checks, quickstart.

## Complexity Tracking

No constitution violations; nothing to justify.
