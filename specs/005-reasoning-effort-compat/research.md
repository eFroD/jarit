# Research: Neuere Reasoning-Modelle für die Extraktion nutzbar machen

Decisions for [spec.md](./spec.md). Each entry: decision, rationale, alternatives.

## R0 – Root cause

`jarit/agents/model_factory.py` builds every OpenAI model as `OpenAIChatModel`, which uses `/v1/chat/completions`, with `settings={"temperature": 0.4}` and no reasoning setting. The installed pydantic-ai-slim **1.0.11** profiles OpenAI models by name prefix (`o*`, `gpt-5*`). It doesn't recognize `gpt-6-luna`, so it treats it as a plain chat model and sends neither `reasoning_effort` nor a request to turn reasoning off.

According to pydantic-ai's model notes, `gpt-6-luna` reasons at `medium` by default. On Chat Completions, OpenAI rejects function tools while reasoning is on. Our agent always has two tools (`get_description`, `get_transcript`), and structured output also goes through a tool, so every request fails with HTTP 400. The error's `param` field says `reasoning_effort`, but the effort being refused is the model's own default, not one we sent.

## R1 – Library version (FR-001, FR-002)

**Decision**: Upgrade to **pydantic-ai 2.x** (`pydantic-ai-slim>=2.54,<3`). The openai SDK moves along to `>=3.19` and google-genai to `>=2.25`, both pulled in by the slim extras. Replace the full `pydantic-ai` dependency with `pydantic-ai-slim[openai,google]`, and move the `eval` group's `pydantic-evals` to the matching 2.x release.

**Rationale**:
- 2.54.0 (2026-10-03) has explicit profiles for `gpt-6-astra`, `gpt-6-sol` and `gpt-6-luna`. For Luna and Sol it records "reasons by default, accepts `effort='none'`" and enables phase, tool search and prompt-cache breakpoints.
- The latest 1.x release (1.107.7, 2026-09-30) does **not** contain `gpt-6-luna`: its gpt-5 prefix list stops at `gpt-5.5`, so it would treat gpt-6 as a non-reasoning model.
- The profiles enumerate known model families on purpose ("a new family must be added here explicitly"). To support future models, we have to keep the library current, not write our own name detection.
- 2.x drops `temperature`/`top_p` itself whenever reasoning is active (`_drop_sampling_params_for_reasoning`), so our fixed temperature can't trigger a second 400 (Edge Case "Temperatur").
- Only the full `pydantic-ai` package pulls in every provider, and we use only OpenAI, Google and Ollama (OpenAI-compatible). The slim package with explicit extras keeps the image smaller and the dependency tree visible.

**Alternatives**:
- Stay on 1.x and set `openai_reasoning_effort='none'` for gpt-6: turns reasoning off across the board (violates FR-003), and it still depends on our own model-name detection, which goes stale with the next release.
- Keep 1.0.11 and only switch to `OpenAIResponsesModel`: the call might go through, but `temperature: 0.4` would be sent to a model that's reasoning, which OpenAI rejects with its own 400. A later fix would still have to upgrade.
- Pin exactly `==2.54.0`: rejected. A lower bound in `pyproject.toml` plus `uv.lock` already pins the build, and the next dependency-update PR should be able to pick up new model profiles.

**Upgrade risks, to verify during implementation** (each becomes a task):

| Area | What changes | Where we're affected |
|------|--------------|----------------------|
| openai SDK 1.x → 3.x | Built on `httpx2` instead of `httpx` | `jarit/jobs/errors.py` (`httpx.HTTPError` in `_LLM_ERRORS`), `jarit/tools/video_loader.py` (Whisper call `OpenAI().audio.transcriptions.create`) |
| google-genai 1.x → 2.x | Major version | `jarit/jobs/errors.py` (`google.genai.errors.APIError`), `tests/unit/test_job_errors.py` |
| pydantic-ai 1 → 2 | Many `Agent(...)` options moved to capabilities; generic deps default changed from `None` to `object`; prefix-less model strings raise errors | `video_agent.py` uses only `model`, `deps_type`, `tools`, `output_type`, `system_prompt`, which all still exist in 2.54. We always pass a `Model` instance, never a string |
| Instrumentation | `Agent(instrument=...)` moved to the `Instrumentation` capability | `main.py` calls `logfire.instrument_pydantic_ai()`; may require a newer `logfire` |
| Test helpers | — | `models.ALLOW_MODEL_REQUESTS`, `FunctionModel`, `AgentInfo` and `ModelHTTPError(status_code, model_name, body)` exist unchanged in 2.54 |

## R2 – Which OpenAI API to use (FR-001, FR-003)

**Decision**: Use `OpenAIResponsesModel` for `LLM_PROVIDER=openai`. Keep `LLM_PROVIDER=ollama` on `OpenAIChatModel` with `OllamaProvider`.

**Rationale**:
- OpenAI's own error message points to `/v1/responses` as the way to combine function tools with reasoning. That's what FR-003 asks for: reasoning stays available and isn't switched off as a workaround.
- pydantic-ai's docs name the Responses API as the default for OpenAI (`infer_model` maps `openai:` to `OpenAIResponsesModel` and treats `openai-chat:` as the explicit legacy path).
- Older models (`gpt-4o`, `gpt-4.1-*`) work on Responses too, so FR-002 holds for OpenAI without a split.
- Ollama's OpenAI-compatible server implements Chat Completions. Switching it to Responses would break FR-002.

**Alternatives**:
- Choose the API by model name (reasoning models → Responses, everything else → Chat): two code paths and our own name list, for no benefit.
- An extra env variable to choose the OpenAI API: an extra setting nobody needs. Can be added later if a Chat-only model shows up.

## R3 – Reasoning setting (FR-004, FR-005, FR-006)

**Decision**: New optional env variable `LLM_REASONING_EFFORT`, read in `create_model()` and mapped to pydantic-ai's **unified `thinking` model setting**:

| `LLM_REASONING_EFFORT` | `thinking` | Meaning |
|---|---|---|
| unset / empty | not set | The model's own default (gpt-6-luna: medium; Gemini: per model) |
| `off`, `none` | `False` | Reasoning off; ignored on models that always reason |
| `minimal`, `low`, `medium`, `high`, `xhigh` | same string | That effort level; pydantic-ai maps a level the model doesn't offer to the nearest one it does |

The value is trimmed and lowercased. Anything else raises `ValueError` from `create_model()`, with the value and the allowed values in the message. `video_agent.py` calls `create_model()` at import, so the backend refuses to start, just as with an invalid `LLM_PROVIDER` today.

**Rationale**:
- `thinking` is provider-neutral: pydantic-ai turns it into `reasoning.effort` on OpenAI and into Gemini's thinking config on Google, and ignores it on models whose profile doesn't support thinking. That's FR-006 without a branch per provider.
- With the variable unset, we send nothing, so User Story 2 / Scenario 1 matches User Story 1, and existing deployments behave exactly as before the setting existed.
- Failing at startup matches how `LLM_PROVIDER` is handled today. A typo in a cost-related setting shouldn't be silently replaced.
- `none` is accepted as an alias for `off` because OpenAI's docs and error message use `none`.

**Alternatives**:
- Provider-specific settings (`openai_reasoning_effort`, `google_thinking_config`): two mappings to maintain, and Ollama would need a third.
- Warn and fall back on invalid values, like `JARIT_MAX_CONCURRENT_EXTRACTIONS` does: fine for a capacity knob, but rejected here because FR-005 asks for a failed start.
- Default to `off` for speed: violates FR-003 and changes behavior for Gemini deployments.

**To verify**: with `LLM_PROVIDER=ollama` and `LLM_REASONING_EFFORT=low`, the request must not fail. pydantic-ai's generic OpenAI-compatible profile should drop `thinking` for an unknown model; this gets a test that inspects the request settings, plus a step in [quickstart.md](./quickstart.md).

## R4 – Temperature (Edge Case)

**Decision**: Keep `temperature: 0.4` in the model settings for all providers.

**Rationale**: pydantic-ai 2.x removes sampling parameters itself when reasoning is active on an OpenAI model and emits a `UserWarning`. Python shows that warning once per call site, so the log doesn't fill up. Models without reasoning, plus Gemini and Ollama, keep the temperature that was used for extraction before.

**Alternatives**: Leave out temperature when `LLM_REASONING_EFFORT` is set: wouldn't help when the variable is unset and the model reasons by default, which is exactly the reported case.

## R5 – Clear log line for rejected configurations (FR-007, FR-008, SC-004)

**Decision**: New helper `describe_rejected_request(exc) -> str | None` in `jarit/jobs/errors.py`. For a `ModelHTTPError` with status 400, 401, 403, 404 or 422, it returns a one-line text with the model name, the status and the provider's `message` from the body. Otherwise it returns `None`. Before the existing `logger.exception(...)`, `runner.py` logs that text as `logger.error("LLM provider rejected the request (configuration?): …")`, including provider and model in `extra`. `classify()` stays unchanged: these cases are still `LLM_ERROR`.

**Rationale**:
- The status codes listed are exactly the ones where retrying is pointless and the cause is in the configuration: invalid parameter, key, permission, unknown model, invalid request. 408, 409, 429 and 5xx are deliberately excluded: they're temporary.
- Users keep seeing only `LLM_ERROR` (FR-008). The message stays in the log, as `errors.py` already promises.
- The full traceback is still logged right after, for cases where one line isn't enough.

**Alternatives**:
- A new `FailureReason.MODEL_CONFIG_ERROR`: would need a DB constraint migration, frontend types and five translations, and would show users an operator problem they can't fix. Rejected; the spec keeps the reasons unchanged.
- Checking the configuration with a test request at startup: costs a request on every start, and the backend could no longer start while the provider is down. Rejected.

## R6 – `httpx2` in the error classification

**Decision**: Add `httpx2.HTTPError` to `_LLM_ERRORS`, keeping `httpx.HTTPError`, because google-genai 2.x still uses `httpx`. Confirm the module name and the exception during implementation. If `httpx2` doesn't expose `HTTPError` at top level, leave it out: `openai.APIConnectionError` is already covered as a subclass of `openai.APIError`.

**Rationale**: Without this, a transport error raised outside the openai SDK's wrapper would fall into `UNKNOWN` after the upgrade instead of `LLM_ERROR`.

## R7 – Documentation (FR-009)

**Decision**: Add `LLM_REASONING_EFFORT` to `.env_example` (commented out), to the README env block under "LLM Provider Configuration", and to both compose examples in the README, `docker-compose.yml` and `docker-compose.dev.yml` as `LLM_REASONING_EFFORT=${LLM_REASONING_EFFORT:-}`. Note there that OpenAI now uses the Responses API and that Ollama ignores the setting when its model doesn't support thinking.

## R8 – Tests (FR-010)

**Decision**:
- `tests/unit/test_model_creation.py`: `openai` now expects `OpenAIResponsesModel`; `ollama` still expects `OpenAIChatModel` + `OllamaProvider`; `google` stays unchanged. New parametrized test for `LLM_REASONING_EFFORT` (unset → no `thinking` key; `off`/`none` → `False`; `low` → `'low'`; ` HIGH ` → `'high'`; `fast` → `ValueError` with the allowed values in the message).
- New check that the Responses model for `gpt-6-luna` gets a profile that supports reasoning (`model.profile`), as a guard against dropping back to a pydantic-ai version without gpt-6 profiles.
- `tests/unit/test_job_errors.py`: cases for `describe_rejected_request` (400 with the body from the bug report → text contains model and message; 429 and 500 → `None`; a non-HTTP error → `None`).
- The existing `test_extraction_pipeline.py` / `test_extraction_runner.py` must stay green after the upgrade. They show whether the 2.x agent API still fits.
- No test sends real requests (`ALLOW_MODEL_REQUESTS = False` stays). The real gpt-6-luna run is manual, following [quickstart.md](./quickstart.md).
