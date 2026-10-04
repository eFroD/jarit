# Implementation Plan: Neuere Reasoning-Modelle für die Extraktion nutzbar machen

**Branch**: `feature/005-reasoning-effort-compat` (from `dev` at `51c7170`) | **Date**: 2026-10-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/005-reasoning-effort-compat/spec.md`

## Summary

`gpt-6-luna` reasons by default. Our `OpenAIChatModel` sends its requests to Chat Completions, where OpenAI rejects function tools while reasoning is on. The installed pydantic-ai 1.0.11 doesn't recognize gpt-6 and sends nothing that could avoid this ([R0](./research.md#r0--root-cause)).

The fix has three parts:

1. **Upgrade** to pydantic-ai-slim 2.x (≥ 2.54), which has profiles for the gpt-6 family and drops `temperature` during reasoning. openai goes to 3.x and google-genai to 2.x; the full `pydantic-ai` package is replaced by `pydantic-ai-slim[openai,google]` ([R1](./research.md#r1--library-version-fr-001-fr-002)).
2. **`LLM_PROVIDER=openai` uses `OpenAIResponsesModel`**, the API on which OpenAI allows tools together with reasoning. Ollama stays on `OpenAIChatModel` ([R2](./research.md#r2--which-openai-api-to-use-fr-001-fr-003)).
3. **New optional `LLM_REASONING_EFFORT`**, mapped to pydantic-ai's provider-neutral `thinking` setting. An invalid value stops the start ([R3](./research.md#r3--reasoning-setting-fr-004-fr-005-fr-006)).

On top of that, the job runner logs one clear line when the provider rejects a configuration (400/401/403/404/422) ([R5](./research.md#r5--clear-log-line-for-rejected-configurations-fr-007-fr-008-sc-004)). Docs and compose files get the new variable ([R7](./research.md#r7--documentation-fr-009)).

## Technical Context

**Language/Version**: Python 3.13 (backend). The frontend is not affected.

**Primary Dependencies**: pydantic-ai-slim `[openai,google]` ≥ 2.54 (was pydantic-ai 1.0.11), openai ≥ 3.19 (was 1.109), google-genai ≥ 2.25 (via the extra), logfire (version as `logfire.instrument_pydantic_ai()` requires for pydantic-ai 2), `pydantic-evals` 2.x in the `eval` group. Version bounds in `pyproject.toml`, exact versions in `uv.lock`.

**Storage**: none affected; no migration ([data-model.md](./data-model.md)).

**Testing**: pytest (`uv run pytest`), ruff. Unit tests for model construction, the reasoning setting and the log helper ([R8](./research.md#r8--tests-fr-010)). Real provider runs are manual following [quickstart.md](./quickstart.md); `ALLOW_MODEL_REQUESTS = False` stays.

**Target Platform**: Linux container (`Dockerfile.backend`), amd64 and arm64; Docker Compose.

**Project Type**: web service (FastAPI backend + SvelteKit frontend); only the backend changes.

**Performance Goals**: none new. Reasoning can make extractions slower; the existing job timeout applies (Edge Case).

**Constraints**: no new `FailureReason`; no provider details in the API/UI (FR-008); start must fail on an invalid value (FR-005); Ollama must stay on Chat Completions.

**Scale/Scope**: about 4 source files (`model_factory.py`, `errors.py`, `runner.py`, possibly `video_loader.py`/`main.py` for upgrade fixes), 2 test files, `pyproject.toml`/`uv.lock`, `.env_example`, README, two compose files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, so there are no ratified principles to check against. As with features 001–004, the plan follows the repo's existing conventions instead:

| Convention | Plan |
|---|---|
| Configuration only through env variables, passed explicitly in compose (feature 001 R4) | `LLM_REASONING_EFFORT` in `.env_example`, both compose files, README ✅ |
| Error messages don't leave the log (`jarit/jobs/errors.py`) | New log line only in the backend log; `classify()` unchanged ✅ |
| No real LLM requests in tests (`tests/conftest.py`) | All new tests run without the network ✅ |
| Dependencies via `uv`, lock committed | `pyproject.toml` + `uv.lock` updated ✅ |

**Gate result**: PASS (pre-research and post-design). No violations, so Complexity Tracking stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/005-reasoning-effort-compat/
├── spec.md
├── plan.md              # this file
├── research.md          # R0–R8
├── data-model.md        # model configuration, log fields
├── quickstart.md        # manual end-to-end validation
├── contracts/
│   └── operator-config.md
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks (not yet created)
```

### Source Code (repository root)

```text
pyproject.toml                    # pydantic-ai-slim[openai,google]>=2.54, openai>=3.19, eval group pydantic-evals 2.x
uv.lock                           # regenerated
jarit/
├── agents/
│   ├── model_factory.py          # OpenAIResponsesModel for openai; LLM_REASONING_EFFORT → settings["thinking"]
│   └── video_agent.py            # verify against the 2.x Agent API only; no change expected
├── jobs/
│   ├── errors.py                 # describe_rejected_request(); httpx2.HTTPError in _LLM_ERRORS
│   └── runner.py                 # log the line before logger.exception
├── tools/
│   └── video_loader.py           # verify the Whisper call on openai 3.x
main.py                           # verify logfire.instrument_pydantic_ai() on pydantic-ai 2
tests/unit/
├── test_model_creation.py        # Responses model, ollama/google unchanged, reasoning values, gpt-6 profile
└── test_job_errors.py            # describe_rejected_request, httpx2 classification
.env_example                      # LLM_REASONING_EFFORT (commented)
docker-compose.yml                # - LLM_REASONING_EFFORT=${LLM_REASONING_EFFORT:-}
docker-compose.dev.yml            # same
README.md                         # env blocks + note on the Responses API
```

**Structure Decision**: Existing single backend package `jarit/` with `tests/unit/`. No new modules. The reasoning setting lives in `model_factory.py`, where `LLM_PROVIDER` and `MODEL_NAME` are already read. The log helper lives in `jobs/errors.py`, next to `classify()`.

## Implementation order

1. **Upgrade alone** (pyproject, lock), then run the full test suite. Fix 2.x breakages (`errors.py` httpx2, Whisper, logfire) until the suite is green, with `OpenAIChatModel` still unchanged. This keeps upgrade problems apart from feature problems.
2. Switch `openai` → `OpenAIResponsesModel` and adjust the test (US1).
3. Add `LLM_REASONING_EFFORT` and its tests (US2).
4. Add `describe_rejected_request` and the runner log line, with tests (US3).
5. Docs and compose (FR-009).
6. Manual validation following [quickstart.md](./quickstart.md) on the dev deployment with `gpt-6-luna`.

## Risks

| Risk | Mitigation |
|---|---|
| pydantic-ai 2.x / openai 3.x break code we didn't look at | Step 1 is isolated; the existing pipeline and runner tests cover the agent path with `FunctionModel` |
| `logfire` isn't compatible with pydantic-ai 2 | Bump the logfire version within the upgrade step; instrumentation is optional (it only runs with a token), but the call happens on every start, so it must not raise |
| Responses API behaves differently on older OpenAI models | Quickstart step 4 compares directly with `dev` |
| Gemini default `gemini-2.5-flash` may meanwhile be outdated | Out of scope; the default is unchanged |
| The next unknown OpenAI model fails the same way | Responses avoids this class of error regardless of profile; keeping pydantic-ai current through the regular dependency PRs gives correct profiles |

## Complexity Tracking

No violations.
