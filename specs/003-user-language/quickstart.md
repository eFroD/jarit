# Quickstart: Sprache pro Nutzer – Validierung

**Feature**: [spec.md](./spec.md) | Contracts: [http-api.md](./contracts/http-api.md), [ui-i18n.md](./contracts/ui-i18n.md)

## Prerequisites

- Same as [002 quickstart](../002-async-extraction-jobs/quickstart.md#prerequisites): `.env`, Docker, `uv`, Node 24.
- For §5 only: working LLM/Whisper keys.

## 1. Automated checks (no LLM, no network)

```bash
docker run -d --rm --name jarit-test-pg -e POSTGRES_USER=jarit -e POSTGRES_PASSWORD=jarit \
  -e POSTGRES_DB=jarit_test -p 55432:5432 postgres:16

DATABASE_URL=postgresql://jarit:jarit@localhost:55432/jarit_test \
  uv run pytest -q --cov=jarit --cov=main --cov-report=term-missing --cov-fail-under=80

uv run ruff check . && uv run ruff format --check .

cd frontend && npm ci && npm run lint && npm run check && npm run build
```

Expected: all green, coverage ≥ 80 %.

**Completeness check (FR-020)**: temporarily delete one key from `frontend/src/lib/i18n/messages/de.ts` → `npm run check` must fail and name the key. Restore it.

## 2. Upgrade of an existing database (FR-006, SC-004)

1. Start the backend on a database at revision `0003_job_started_at` that has users and jobs with `target_language = 'german'`.
2. Restart with this feature. Log: upgraded `0003_job_started_at` → `0004_user_language`.
3. `GET /users/me` for an existing user → `"language": "en"`; UI is English, the target language select shows English preselected.
4. `GET /extraction-jobs` → old jobs show `target_language: "de"`.

## 3. API behaviour

With a token for user *alice*:

| Request | Expected |
|---------|----------|
| `PATCH /users/me {"language":"de"}` | `200`, `language: "de"` |
| `PATCH /users/me {"language":"pt"}` | `422`; `GET /users/me` still `de` |
| `POST /extraction-jobs {"url": "…"}` (no language) | `202`, `target_language: "de"` |
| `POST /extraction-jobs {"url": "…", "target_language": "it"}` | `202`, `target_language: "it"`; `GET /users/me` still `de` |
| `POST /extraction-jobs {"url": "…", "target_language": "english"}` | `422`, no job |
| `PATCH /users/me {"language":"fr"}`, then `GET` an older job | old job keeps its `target_language` |
| `POST /extraction-jobs/{completed id}/retry` | `409`, body has `code: "JOB_NOT_RETRYABLE"` |

## 4. UI walkthrough (browser)

1. **Pre-login (US3)**: set the browser language to German → `/login` and `/register` are German. Set it to Portuguese → English.
2. **Register**: language select preselected with German; switch to French → the page turns French at once; register → `GET /users/me` shows `fr`.
3. **Login precedence (FR-018)**: browser German, account English → after login the UI is English.
4. **Switch language (US2)**: Dashboard → language → Deutsch. The page turns German in < 1 s without reload; still logged in. Visit Dashboard, progress page, editor, history, admin (as admin): no English UI text left (recipe content excepted); dates in German format.
5. **Failed save**: stop the backend, change the language → translated error, UI stays in the old language.
6. **Other device (US2 scenario 3)**: log in in a private window → UI in the stored language.
7. **Target language (US1)**: the extraction form preselects the user's language; pick Italian for one submission; reload → preselection is the user's language again.
8. **Errors (FR-012)**: in German, retry a completed job via a second tab or trigger a `409` → German message. Enter wrong Mealie credentials and verify → German message and **no logout**.
9. **Unsaved edits survive a language switch**: open the editor, change a field, switch the language in another view of the same tab (e.g. back to dashboard and return) → edits still marked as unsaved.

## 5. End-to-end with real keys (FR-008a)

Submit a German-language recipe video with target language Spanish → the completed recipe (title, ingredients, steps) is Spanish while the UI stays in the user's language.
