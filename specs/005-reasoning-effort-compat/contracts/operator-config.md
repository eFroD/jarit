# Contract: Operator configuration and logs

## New environment variable

| Variable | Default | Valid values | Invalid value |
|---|---|---|---|
| `LLM_REASONING_EFFORT` | unset (model's own default) | `off`, `none`, `minimal`, `low`, `medium`, `high`, `xhigh`; case and surrounding whitespace ignored; empty counts as unset | Backend fails to start with `ValueError: Unsupported LLM_REASONING_EFFORT: '<value>'. Use one of: off, none, minimal, low, medium, high, xhigh, or leave it unset.` |

It's read once at startup; changing it requires a restart.

Behavior by provider:

- **openai**: sent as the reasoning effort. `off`/`none` turns reasoning off on models that allow it. Models that always reason ignore `off`. A level the model doesn't offer is mapped to the nearest one.
- **google**: mapped to Gemini's thinking setting where the model supports it, otherwise ignored.
- **ollama**: ignored unless pydantic-ai knows the model supports thinking. Never the cause of a failed extraction.

Must be added to:

- `.env_example`: commented, e.g.
  `# Optional: how much the model may reason before answering (off, minimal, low, medium, high, xhigh).`
  `# Unset = the model's default. Higher = slower and more expensive.`
  `# LLM_REASONING_EFFORT=`
- `docker-compose.yml` and `docker-compose.dev.yml`: `- LLM_REASONING_EFFORT=${LLM_REASONING_EFFORT:-}` next to `MODEL_NAME`.
- README: the compose example, the `.env` example and the "LLM Provider Configuration" block.

## Changed behavior without new configuration

- `LLM_PROVIDER=openai` now uses the OpenAI **Responses API** instead of Chat Completions. Existing keys and model names keep working; no action needed. The README states this, because proxies or gateways that only implement Chat Completions are no longer supported for `openai` (use `ollama` or another OpenAI-compatible setup for those).
- `google` and `ollama` behave as before.

## Log line for rejected requests

When the provider rejects a request with HTTP 400, 401, 403, 404 or 422, the job runner logs **one** line at `ERROR` before the existing traceback:

```text
LLM provider rejected the request (check the model configuration): provider=openai model=gpt-6-luna status=400: Function tools with reasoning_effort are not supported for gpt-6-luna in /v1/chat/completions. To use function tools, use /v1/responses or set reasoning_effort to 'none'.
```

`extra` fields: `job_id`, `provider`, `model`, `status`.

- The provider message comes from the error body (max. 500 characters). It contains no secrets: the provider never echoes the API key.
- 408, 409, 429 and 5xx get **no** line like this. They're temporary and are logged only as before.
- The job ends with `LLM_ERROR`, as before. The UI and API show no provider details.
