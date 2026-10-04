# Quickstart: Validate reasoning-model support

Proves [spec.md](./spec.md) end to end. Configuration contract: [contracts/operator-config.md](./contracts/operator-config.md).

## Prerequisites

- Branch `feature/005-reasoning-effort-compat`, `uv sync` done (pulls pydantic-ai 2.x, openai 3.x).
- An `OPENAI_API_KEY` with access to `gpt-6-luna` and an older model (e.g. `gpt-4.1-mini`).
- For step 5: a `GOOGLE_API_KEY`. For step 6: a running Ollama with any chat model that supports tool calling.
- One recipe video URL whose description is incomplete, so the transcript tool runs too.

## 1. Automated tests

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

Expected: all green, including the new cases in `tests/unit/test_model_creation.py` and `tests/unit/test_job_errors.py`. No test sends a real LLM request.

## 2. gpt-6-luna without extra settings (US1, SC-001)

```bash
LLM_PROVIDER=openai MODEL_NAME=gpt-6-luna docker compose -f docker-compose.dev.yml up --build
```

Submit the video in the UI. Expected: the job goes through "fetching description" → "transcribing" → done, with a recipe. The backend log contains **no** `status_code: 400`. In Logfire (if configured), the request goes to `/v1/responses` and contains two tool calls.

Repeat with 10 recipe videos for SC-001: 10/10 without a provider rejection.

## 3. Reasoning effort (US2)

Repeat step 2 with each of the following, restarting each time:

| `LLM_REASONING_EFFORT` | Expected |
|---|---|
| `off` | Recipe; in the trace, reasoning effort `none`; noticeably faster |
| `high` | Recipe; reasoning effort `high` |
| ` Low ` | Recipe; reasoning effort `low` (spaces and case ignored) |
| `fast` | Backend doesn't start; log shows `Unsupported LLM_REASONING_EFFORT: 'fast'` and the allowed values |

## 4. Older OpenAI model unchanged (US1 scenario 3, SC-002)

`MODEL_NAME=gpt-4.1-mini`, `LLM_REASONING_EFFORT` unset. Expected: same extraction result as on `dev` before the change.

## 5. Gemini unchanged (FR-002, FR-006)

`LLM_PROVIDER=google`, `MODEL_NAME=gemini-2.5-flash`, once without and once with `LLM_REASONING_EFFORT=low`. Expected: recipe both times, no error caused by the setting.

## 6. Ollama unchanged (FR-002, FR-006, Edge Case)

`LLM_PROVIDER=ollama`, `OLLAMA_URL=http://<host>:11434`, a local model, once with `LLM_REASONING_EFFORT=high`. Expected: the extraction still uses Chat Completions (Ollama log: `POST /v1/chat/completions`) and doesn't fail because of the setting.

## 7. Clear log line on rejection (US3, SC-004)

Force a rejection, e.g. with `MODEL_NAME=gpt-does-not-exist`. Submit a video. Expected:

- Backend log has one `ERROR` line `LLM provider rejected the request (check the model configuration): provider=openai model=gpt-does-not-exist status=404: …`, followed by the traceback as before.
- The UI shows the job as "Language model error", without the provider's text.
- Disconnecting the network instead (a temporary error) produces **no** such line.
