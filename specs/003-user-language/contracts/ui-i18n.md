# UI Contract: Lokalisierung des Frontends

## Module layout

```text
frontend/src/lib/i18n/
├── index.ts          # locale store, t store, setLocaleFromUser(), resetLocale(), errorMessage()
├── languages.ts      # Locale type, LANGUAGES (code + native name), matchLocale()
├── format.ts         # formatDate(), formatDateTime(), formatDuration() via Intl
└── messages/
    ├── en.ts         # source dictionary; defines the Messages type
    ├── de.ts         # const de: Messages = { … }
    ├── es.ts
    ├── fr.ts
    └── it.ts
```

## Rules

1. **No UI text outside the dictionaries.** Every user-visible string in `.svelte` and `.ts` files under `frontend/src` comes from `$t` (or `get(t)` outside components). This includes `<title>`, placeholders, `aria-label`s, `confirm()` texts, status and failure labels, and error messages. Recipe content, URLs and user-entered values are not translated.
2. **Keys** are flat, `area_name` style (`dashboard_title`, `jobs_status_QUEUED`, `error_JOB_NOT_FOUND`). Status, failure-reason and error-code keys embed the code so they can be looked up by value.
3. **Parameters** use functions with a single object argument: `history_uploadedOn: (p: { date: string }) => …`. Plurals are handled inside the function per language.
4. **Completeness**: every dictionary has exactly the keys and signatures of `en.ts`. `npm run check` fails otherwise (FR-020).
5. **Dates** are formatted only through `format.ts` with the current `locale`.
6. `document.documentElement.lang` always equals `$locale`.

## Locale lifecycle

| Moment | Locale |
|--------|--------|
| App start, not logged in | `matchLocale(navigator.languages)` (`de-AT` → `de`; unsupported → `en`) |
| App start with token | browser locale until `GET /users/me` returns, then `user.language` |
| After login | `user.language` from the profile loaded right after login |
| Register page: user picks a language | the page switches to it at once; it is sent as `language` with the registration |
| Settings: user picks a language | `PATCH /users/me`; on `200` set `user` and `locale`; on error show the translated error and keep both |
| Logout | back to the browser locale |

## Screens affected

| Screen / component | Change |
|--------------------|--------|
| `+layout.svelte` (root) | initial locale, `<title>`, `<html lang>` |
| `Navigation.svelte` | all labels |
| `LoginForm.svelte`, `RegisterForm.svelte` | all labels and errors; register gets a language select (FR-017) |
| Dashboard + `RecipeExtractor.svelte` | labels; target language select from `LANGUAGES`, preselected with `$user.language` (FR-007, FR-008) |
| Dashboard + new `LanguageSettings.svelte` | language select, saves on change (FR-003) |
| `MealieConfig.svelte` | all labels and errors |
| `JobProgress.svelte`, `ActiveJobs.svelte`, `jobs.ts` | stage/status/failure labels and durations from the dictionary |
| `JobHistory.svelte` | labels, dates, confirm dialogs |
| `RecipePreview.svelte` | labels, confirm dialog, dates; recipe content untouched |
| `AdminPanel.svelte` | all labels, dates; follows the admin's own language |
| `api.ts` | `ApiError.code`; `error` store gets translated text via `errorMessage()`; logout only on session-related `401` |

## Error messages

`errorMessage(err, t)`:

1. `ApiError` with a known `code` → `t['error_' + code]`
2. `ApiError` without code → generic message by status: `401` session expired, `403` not allowed, `404` not found, `409` conflict, `422` invalid input, `5xx` server error
3. network failure (`TypeError` from `fetch`) → "server not reachable"
4. anything else → generic "something went wrong"
