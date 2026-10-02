# Data Model: Sprache pro Nutzer für Oberfläche und Rezepte

**Feature**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

## Language (value type, no table)

| Code | Native name (UI) | Prompt name (LLM) | `Intl` locale |
|------|------------------|-------------------|---------------|
| `en` | English          | English           | `en`          |
| `de` | Deutsch          | German            | `de`          |
| `es` | Español          | Spanish           | `es`          |
| `fr` | Français         | French            | `fr`          |
| `it` | Italiano         | Italian           | `it`          |

- Backend: `jarit/languages.py` – `Language(str, Enum)`, `PROMPT_NAMES`, `prompt_name(value: str) -> str` (returns the value unchanged for unknown legacy values).
- Frontend: `frontend/src/lib/i18n/languages.ts` – `type Locale = 'en' | 'de' | 'es' | 'fr' | 'it'`, `LANGUAGES: { code: Locale; name: string }[]`, `matchLocale(tags: readonly string[]): Locale`.
- The order above is the display order in every select.

## User (extended)

| Field      | Type         | Rules |
|------------|--------------|-------|
| `language` | `VARCHAR(8)` | `NOT NULL`, server default `'en'`, `CHECK (language IN ('en','de','es','fr','it'))` |

- Set at registration (optional request field, default `en`).
- Changed only by the user via `PATCH /users/me`.
- Existing rows receive `en` through the server default when the column is added (FR-006).

## ExtractionJob (values change, schema unchanged)

| Field             | Type          | Change |
|-------------------|---------------|--------|
| `target_language` | `VARCHAR(64)` | New jobs store a `Language` code. Migration rewrites `english→en`, `german→de`, `spanish→es`, `french→fr`, `italian→it`. Other legacy values stay. No check constraint, so unknown legacy values remain valid. |

- Set once at submission: the request value, or the user's `language` if omitted (FR-009).
- Never changed afterwards, including when the user's language changes (FR-010) or on retry.

## Migration `0004_user_language`

- `down_revision = "0003_job_started_at"`
- **upgrade**:
  1. `ADD COLUMN users.language VARCHAR(8) NOT NULL DEFAULT 'en'`
  2. add check constraint `ck_users_language`
  3. `UPDATE extraction_jobs SET target_language = CASE lower(target_language) WHEN 'english' THEN 'en' … ELSE target_language END`
- **downgrade**: drop the constraint and the column; map job codes back to the English names.

## Frontend state

| Store    | Type            | Source |
|----------|-----------------|--------|
| `locale` | `Locale`        | `user.language` when logged in, otherwise `matchLocale(navigator.languages)` |
| `t`      | `Messages`      | `derived(locale, (l) => dictionaries[l])` |
| `user`   | `User` (+ `language: Locale`) | `GET /users/me`, updated from `PATCH /users/me` |

`Messages` is the type of `messages/en.ts`; every other dictionary must have exactly the same keys and signatures.
