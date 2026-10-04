# Contract: Pull-request checks

File: `.github/workflows/ci.yml`. Trigger: `pull_request` (opened, synchronize, reopened) with base branch `dev` or `main`. Permissions: `contents: read`. **No `secrets.*` references.**

| Job | Check name | Command | Must pass |
|---|---|---|---|
| backend | Ruff lint | `uv run ruff check .` | yes |
| backend | Ruff format | `uv run ruff format --check .` | yes |
| backend | Tests | `uv run pytest` (test paths come from `pyproject.toml`) with a `postgres:16` service and `DATABASE_URL` pointing at it | yes |
| frontend | Lint | `npm run lint` (Prettier + ESLint) | yes |
| frontend | Types | `npm run check` | yes |
| frontend | Build | `npm run build` | yes |

Excluded on purpose: `tests/integration` (imports a non-existent `jarit.main`, needs further work), `tests/model_eval` (real LLM calls), Docker image build (decision Q2 = A).

Environment inside CI:
- `JARIT_ENCRYPTION_KEY` is not set by the workflow. `tests/conftest.py` generates a throwaway key per run.
- `DATABASE_URL=postgresql://jarit:jarit@localhost:5432/jarit_test`. These are local service-container credentials, not secrets. `tests/db` only runs when the database name ends in `_test`, because it truncates tables.

Target: total wall time under 10 minutes (SC-006), helped by the uv cache and the npm cache.

Required status checks for merging are set by the repo owner in the branch protection rules for `main` and `dev`. That setting is outside this repository's files.
