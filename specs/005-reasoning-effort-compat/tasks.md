---

description: "Task list for making newer reasoning models usable for extraction"
---

# Tasks: Neuere Reasoning-Modelle für die Extraktion nutzbar machen

**Input**: Design documents from `specs/005-reasoning-effort-compat/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/operator-config.md](./contracts/operator-config.md), [quickstart.md](./quickstart.md)

**Tests**: Required by FR-010. Unit tests only, without network access (`tests/conftest.py` sets `models.ALLOW_MODEL_REQUESTS = False`, and that stays). Real provider runs are manual, following [quickstart.md](./quickstart.md).

**Organization**: Tasks are grouped by user story (US1–US3 from spec.md), so each story can be implemented and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on unfinished tasks)
- **[Story]**: The user story the task belongs to

## Path Conventions

Backend only: package `jarit/`, tests in `tests/unit/`. Shared names used throughout:

- Env variables: `LLM_PROVIDER`, `MODEL_NAME`, `OLLAMA_URL` (existing), `LLM_REASONING_EFFORT` (new).
- Allowed values for `LLM_REASONING_EFFORT`, in this order: `off`, `none`, `minimal`, `low`, `medium`, `high`, `xhigh`. `off` and `none` → `False`; the others → the same string ([data-model.md](./data-model.md)).
- Status codes that count as a "rejected configuration": `400, 401, 403, 404, 422` ([research R5](./research.md#r5--clear-log-line-for-rejected-configurations-fr-007-fr-008-sc-004)).
- Commands: `uv sync`, `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`.
- Style: like `jarit/jobs/settings.py` and `jarit/jobs/errors.py`: short module docstrings, comments only to explain *why*, `logging.getLogger(__name__)`.

---

## Phase 1: Setup (dependency upgrade)

**Purpose**: Bring pydantic-ai to 2.x, without changing any feature yet ([research R1](./research.md#r1--library-version-fr-001-fr-002), plan "Implementation order" step 1).

- [X] T001 In `pyproject.toml`, replace the dependencies `"pydantic-ai>=1.0.10"` and `"pydantic-ai-slim[google]>=1.0.10"` with one entry `"pydantic-ai-slim[openai,google]>=2.54.0"`; raise `"openai>=1.108.2"` to `"openai>=3.19.0"`; in the `eval` group, raise `"pydantic-evals[logfire]>=1.0.11"` to the 2.x release that matches the resolved pydantic-ai-slim (check on PyPI, e.g. `>=2.54.0`)
- [X] T002 Run `uv lock --upgrade-package pydantic-ai-slim --upgrade-package openai --upgrade-package google-genai --upgrade-package pydantic-evals --upgrade-package logfire`, then `uv sync`; make sure `uv.lock` now has pydantic-ai-slim ≥ 2.54, openai ≥ 3.19 and google-genai ≥ 2.25, and that the `pydantic-ai` meta package is gone from the lock (`grep -n '^name = "pydantic-ai"$' uv.lock` is empty)

---

## Phase 2: Foundational (make the existing code run on 2.x)

**Purpose**: Bring the existing suite back to green on the new versions. Every user story builds on this.

**⚠️ CRITICAL**: Don't start any user story work before T009 is green.

- [X] T003 Run `uv run pytest -q` and record the failures. Expect them in `tests/unit/test_model_creation.py`, `tests/unit/test_job_errors.py`, `tests/unit/test_extraction_pipeline.py` and `tests/unit/test_extraction_runner.py`. Don't change any tests yet
- [X] T004 [P] In `jarit/jobs/errors.py`, check whether `import httpx2` exists and exposes `httpx2.HTTPError` (`uv run python -c "import httpx2; print(httpx2.HTTPError)"`). If yes: `import httpx2` and add `httpx2.HTTPError` to `_LLM_ERRORS` (keep `httpx.HTTPError`, which google-genai still uses). Otherwise leave it out and say so in a short comment that `openai.APIError` covers OpenAI transport errors ([research R6](./research.md#r6--httpx2-in-the-error-classification))
- [X] T005 [P] In `jarit/jobs/errors.py`, make sure `from google.genai import errors as google_errors` and `google_errors.APIError` still exist in google-genai 2.x (`uv run python -c "from google.genai import errors; print(errors.APIError)"`); if renamed, update the import and `_LLM_ERRORS` accordingly
- [X] T006 [P] In `jarit/tools/video_loader.py`, check the Whisper call (`OpenAI(api_key=...)`, `client.audio.transcriptions.create(...)` and how the response is read) against openai 3.x (signature through `uv run python -c "import inspect, openai; print(inspect.signature(openai.OpenAI().audio.transcriptions.create))"` with `OPENAI_API_KEY=sk-test`); only adjust if the signature or return type changed
- [X] T007 [P] In `main.py`, make sure `logfire.configure(token=None)` plus `logfire.instrument_pydantic_ai()` works with the locked logfire and pydantic-ai 2.x, using `uv run python -c "import logfire; logfire.configure(token=None, send_to_logfire=False); logfire.instrument_pydantic_ai()"`. If it raises, raise the `logfire[fastapi]` minimum in `pyproject.toml` to the first compatible version, then run `uv lock` + `uv sync` again
- [X] T008 [P] Check `jarit/agents/video_agent.py` against the 2.x `Agent` signature: `model`, `deps_type`, `tools`, `output_type` and `system_prompt` must still be accepted (`uv run python -c "import os; os.environ.setdefault('GOOGLE_API_KEY','x'); import jarit.agents.video_agent"`). Make only the minimum changes required, don't migrate to `instructions=`
- [X] T009 Fix any remaining failures from T003 in the tests only where the API really changed (e.g. a different `ModelHTTPError` constructor or `FunctionModel` callback signature in `tests/unit/test_extraction_pipeline.py` / `tests/unit/test_extraction_runner.py` / `tests/unit/test_job_errors.py`). Behavior stays as it is: `test_model_creation.py` still expects `OpenAIChatModel` for `openai` at this point. Finish with `uv run pytest -q` green and `uv run ruff check .` clean

**Checkpoint**: The app runs unchanged on pydantic-ai 2.x. This is a good place for a separate commit (`chore: upgrade pydantic-ai to 2.x`).

---

## Phase 3: User Story 1 - Extract a recipe with a current OpenAI reasoning model (Priority: P1) 🎯 MVP

**Goal**: `LLM_PROVIDER=openai` + `MODEL_NAME=gpt-6-luna` extracts recipes with tool calls and no 400 ([research R2](./research.md#r2--which-openai-api-to-use-fr-001-fr-003)).

**Independent Test**: [quickstart.md](./quickstart.md) steps 2 and 4; automated: `uv run pytest tests/unit/test_model_creation.py`.

### Tests for User Story 1

- [X] T010 [US1] In `tests/unit/test_model_creation.py`, change the expected type for the `openai` case from `OpenAIChatModel` to `OpenAIResponsesModel` (import from `pydantic_ai.models.openai`). The `ollama` case still expects `OpenAIChatModel` + `OllamaProvider`, `google` and the default case stay unchanged. Run the test and make sure the `openai` case now fails
- [X] T011 [US1] In `tests/unit/test_model_creation.py`, add a test `test_openai_gpt6_profile_supports_reasoning` that sets `LLM_PROVIDER=openai`, `MODEL_NAME=gpt-6-luna`, `OPENAI_API_KEY=sk-test` and asserts `create_model().profile.supports_thinking is True`. It guards against a pydantic-ai version without gpt-6 profiles. Check the attribute name first with `uv run python -c "from pydantic_ai.profiles.openai import openai_model_profile as p; print(p('gpt-6-luna'))"`

### Implementation for User Story 1

- [X] T012 [US1] In `jarit/agents/model_factory.py`, return `OpenAIResponsesModel(model_name=model_name, settings={"temperature": 0.4})` instead of `OpenAIChatModel(...)` for `provider == "openai"`; add `OpenAIResponsesModel` to the import from `pydantic_ai.models.openai`; adjust the return annotation to `OpenAIResponsesModel | OpenAIChatModel | GoogleModel`, and the docstring as well. Leave the `ollama` branch on `OpenAIChatModel` with a one-line comment explaining why (Ollama's OpenAI-compatible API offers only Chat Completions). Run T010 and T011 until they're green

**Checkpoint**: US1 is fully usable on its own. gpt-6-luna works with the model's default reasoning.

---

## Phase 4: User Story 2 - Set the reasoning effort as an operator (Priority: P2)

**Goal**: Optional `LLM_REASONING_EFFORT` controls reasoning across providers. An invalid value stops the start ([research R3](./research.md#r3--reasoning-setting-fr-004-fr-005-fr-006), [contracts/operator-config.md](./contracts/operator-config.md)).

**Independent Test**: [quickstart.md](./quickstart.md) steps 3, 5 and 6; automated: `uv run pytest tests/unit/test_model_creation.py -k reasoning`.

### Tests for User Story 2

- [X] T013 [US2] In `tests/unit/test_model_creation.py`: add `"LLM_REASONING_EFFORT"` to the list of variables `test_create_model` deletes. Add a parametrized test `test_reasoning_effort_setting` over all three providers (`openai`/`gpt-6-luna`, `google`/`gemini-2.5-flash`, `ollama`/`llama3` with `OLLAMA_URL`) × values: unset → `"thinking" not in model.settings`; `"off"` → `False`; `"none"` → `False`; `"low"` → `"low"`; `" HIGH "` → `"high"`; `""` → not set. Also always assert `model.settings["temperature"] == 0.4`
- [X] T014 [US2] In `tests/unit/test_model_creation.py`, add `test_invalid_reasoning_effort`: `LLM_PROVIDER=openai`, `LLM_REASONING_EFFORT=fast` → `pytest.raises(ValueError, match="LLM_REASONING_EFFORT")`, and the message contains `'fast'` and `xhigh`
- [X] T015 [US2] In `tests/unit/test_model_creation.py`, add `test_reasoning_setting_dropped_for_unsupported_ollama_model` (FR-006): build the ollama model with `LLM_REASONING_EFFORT=high` and check that pydantic-ai doesn't treat it as thinking-capable (`model.profile.supports_thinking is False` for `llama3`). If the profile doesn't reliably answer that, assert instead that `pydantic_ai.models.openai` drops the setting for unsupported profiles (find the relevant function in `.venv/lib/python3.13/site-packages/pydantic_ai/models/openai.py`, e.g. through `grep -n "thinking" …`) and note the line in the test's docstring

### Implementation for User Story 2

- [X] T016 [US2] In `jarit/agents/model_factory.py`, add a module constant `REASONING_EFFORT_ENV = "LLM_REASONING_EFFORT"` and a function `_reasoning_setting() -> bool | str | None`: read the variable, `strip().lower()`; empty/unset → `None`; `off`/`none` → `False`; `minimal|low|medium|high|xhigh` → the string; anything else → `ValueError(f"Unsupported LLM_REASONING_EFFORT: {raw!r}. Use one of: off, none, minimal, low, medium, high, xhigh, or leave it unset.")` (exact text from [contracts/operator-config.md](./contracts/operator-config.md))
- [X] T017 [US2] In `create_model()` in `jarit/agents/model_factory.py`, build the settings once: `settings: ModelSettings = {"temperature": 0.4}`; if `_reasoning_setting()` isn't `None`, set `settings["thinking"] = …`; pass the same `settings` dict to all three branches (import `ModelSettings` from `pydantic_ai.settings`). Call `_reasoning_setting()` before the provider branch, so an invalid value fails even before an invalid provider. Run T013–T015 until they're green

**Checkpoint**: US1 and US2 work independently of each other; with the variable unset, behavior is exactly that of US1.

---

## Phase 5: User Story 3 - Recognize an incompatible model configuration clearly (Priority: P3)

**Goal**: One `ERROR` line with provider, model, status and the provider's reason for 400/401/403/404/422; users still see only `LLM_ERROR` ([research R5](./research.md#r5--clear-log-line-for-rejected-configurations-fr-007-fr-008-sc-004)).

**Independent Test**: [quickstart.md](./quickstart.md) step 7; automated: `uv run pytest tests/unit/test_job_errors.py tests/unit/test_extraction_runner.py`.

### Tests for User Story 3

- [X] T018 [P] [US3] In `tests/unit/test_job_errors.py`, add tests for `describe_rejected_request` (import from `jarit.jobs.errors`):
  - `ModelHTTPError(status_code=400, model_name="gpt-6-luna", body={"message": "Function tools with reasoning_effort are not supported for gpt-6-luna in /v1/chat/completions. To use function tools, use /v1/responses or set reasoning_effort to 'none'.", "type": "invalid_request_error", "param": "reasoning_effort", "code": None})` → result contains `model=gpt-6-luna`, `status=400` and `Function tools with reasoning_effort`.
  - Parametrized 401/403/404/422 → not `None`; 408/409/429/500/503 → `None`.
  - `body="plain text"` → text contained; `body=None` → still a line without crashing.
  - A body longer than 500 characters is cut to 500.
  - `UnexpectedModelBehavior("x")`, `TimeoutError()`, `ValueError()` → `None`.
  - In addition, `classify(...)` stays `FailureReason.LLM_ERROR` for the 400 case (FR-008)
- [X] T019 [P] [US3] In `tests/unit/test_extraction_runner.py`, add a test, following the pattern of the existing failure test there (a stub extract function that raises `ModelHTTPError(status_code=400, model_name="gpt-6-luna", body={"message": "…"})`), that uses `caplog` to check: exactly one record at `ERROR` from `jarit.jobs.runner` whose message starts with `LLM provider rejected the request` and contains `provider=` and `model=gpt-6-luna`; the job ends with `FailureReason.LLM_ERROR`. A second test with `status_code=429` → no such record

### Implementation for User Story 3

- [X] T020 [US3] In `jarit/jobs/errors.py`, add `REJECTED_STATUS_CODES = frozenset({400, 401, 403, 404, 422})` and `describe_rejected_request(exc: BaseException) -> str | None`: `None` if not `isinstance(exc, ModelHTTPError)` (import from `pydantic_ai.exceptions`) or the status isn't in the set; otherwise `f"model={exc.model_name} status={exc.status_code}: {message}"`, where `message = exc.body["message"]` if the body is a dict with a `str` `message`, otherwise `str(exc.body)`; cut to 500 characters. Add a sentence to the module docstring saying this text goes only into the log
- [X] T021 [US3] In `jarit/jobs/runner.py`, in the `except Exception as exc:` block before `logger.exception(...)`, call `describe_rejected_request(exc)`; if not `None`: `logger.error("LLM provider rejected the request (check the model configuration): provider=%s %s", provider, detail, extra={"job_id": str(job_id), "provider": provider, "model": getattr(exc, "model_name", None), "status": getattr(exc, "status_code", None)})`, with `provider = os.getenv("LLM_PROVIDER", "google").lower()` (same default as `model_factory.create_model`). `classify`, `logger.exception` and `self._store.fail` stay unchanged. Run T018–T019 until they're green

**Checkpoint**: All three stories work independently of each other.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T022 [P] In `.env_example`, add the commented block from [contracts/operator-config.md](./contracts/operator-config.md) right below `MODEL_NAME=…` (3 comment lines + `# LLM_REASONING_EFFORT=`)
- [X] T023 [P] In `docker-compose.yml` and `docker-compose.dev.yml`, add `- LLM_REASONING_EFFORT=${LLM_REASONING_EFFORT:-}` to the backend `environment` list right after `- MODEL_NAME=${MODEL_NAME}`
- [X] T024 [P] In `README.md`: add the same line to the compose example (around `- MODEL_NAME=${MODEL_NAME}`, ~line 115); add the commented block to the `.env` example (~line 159); in the "LLM Provider Configuration" block (~line 262), add `LLM_REASONING_EFFORT=           # Optional: off, minimal, low, medium, high, xhigh (unset = model default)` plus two sentences: OpenAI now uses the Responses API (gateways that only implement Chat Completions no longer work with `openai`), and Google/Ollama ignore the setting if the model doesn't support reasoning
- [X] T025 Run `uv run ruff format .`, `uv run ruff check .` and `uv run pytest -q`; everything green
- [X] T026 Build the backend image (`docker compose -f docker-compose.dev.yml build backend`) and make sure it starts with `LLM_PROVIDER=openai MODEL_NAME=gpt-6-luna` (the log shows the app starting, no import error) and refuses to start with `LLM_REASONING_EFFORT=fast` and the message from the contract
- [ ] T027 Manual validation on the dev deployment following [quickstart.md](./quickstart.md) steps 2–7 (needs real API keys; the user does this or approves it); note the results in the PR description

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (T001–T002)**: no prerequisites.
- **Foundational (T003–T009)**: after Setup. T004–T008 in parallel once T003 is done; T009 after T004–T008. **Blocks all stories.**
- **US1 (T010–T012)**: after Phase 2.
- **US2 (T013–T017)**: after Phase 2. Technically independent of US1, but touches the same files (`model_factory.py`, `test_model_creation.py`), so run it **after** US1 to avoid conflicts.
- **US3 (T018–T021)**: after Phase 2; separate files (`errors.py`, `runner.py` and their tests), so it can run **in parallel** with US1/US2.
- **Polish (T022–T027)**: T022–T024 in parallel at any time after Phase 2; T025–T027 after all stories.

### Within each story

Tests first (they must fail), then implementation, then run the tests again.

### Parallel opportunities

- Phase 2: T004, T005, T006, T007, T008 (different files or read-only checks).
- US3 as a whole alongside US1 → US2.
- T018 and T019 (different test files).
- T022, T023, T024 (different files).

---

## Parallel Example: Foundational + US3

```text
# After T003:
Task: "T004 httpx2 in jarit/jobs/errors.py"
Task: "T006 Whisper call in jarit/tools/video_loader.py"
Task: "T007 logfire in main.py"
Task: "T008 Agent signature in jarit/agents/video_agent.py"

# After T009, two parallel tracks:
Track A: T010 → T011 → T012 (US1) → T013 → T014 → T015 → T016 → T017 (US2)
Track B: T018 + T019 → T020 → T021 (US3)
```

---

## Implementation Strategy

### MVP first (US1 only)

1. Phase 1 + Phase 2: upgrade, suite green, separate commit.
2. Phase 3: switch to the Responses model.
3. **STOP and validate**: quickstart steps 2 and 4 with gpt-6-luna and an older model. That's already enough to fix the reported bug.

### Incremental delivery

1. Setup + Foundational → upgrade commit.
2. US1 → gpt-6-luna works (MVP).
3. US2 → reasoning effort can be set.
4. US3 → clear log line.
5. Polish → docs, compose, image check, manual validation, PR to `dev`.
