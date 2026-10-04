# Data Model: Neuere Reasoning-Modelle für die Extraktion nutzbar machen

No database changes. No migration. `FailureReason` and the `extraction_jobs` CHECK constraint stay unchanged.

## Model configuration (in memory, built once per process)

Built by `create_model()` in `jarit/agents/model_factory.py` from the environment when `jarit.agents.video_agent` is imported. Applies to every extraction in the instance; changing it requires a restart.

| Field | Source | Values | Default | Validation |
|---|---|---|---|---|
| provider | `LLM_PROVIDER` | `openai`, `google`, `ollama` (case-insensitive) | `google` | Anything else → `ValueError`, start fails (unchanged) |
| model name | `MODEL_NAME` | provider-specific string | `gemini-2.5-flash` | None; the provider rejects unknown names at the first request (→ log line per R5) |
| Ollama URL | `OLLAMA_URL` | URL | — | Only used for `ollama` (unchanged) |
| reasoning effort | `LLM_REASONING_EFFORT` (**new**) | `off`, `none`, `minimal`, `low`, `medium`, `high`, `xhigh` (trimmed, case-insensitive) | unset = model default | Anything else → `ValueError` naming the value and the allowed values, start fails |
| temperature | fixed | `0.4` | — | pydantic-ai drops it while an OpenAI model is reasoning (R4) |

### Derived model object

| `LLM_PROVIDER` | Model class | Provider | API |
|---|---|---|---|
| `openai` | `OpenAIResponsesModel` (**was** `OpenAIChatModel`) | `OpenAIProvider` (implicit, `OPENAI_API_KEY`) | `/v1/responses` |
| `google` | `GoogleModel` | `GoogleProvider` (implicit, `GOOGLE_API_KEY`) | Gemini API |
| `ollama` | `OpenAIChatModel` | `OllamaProvider(OLLAMA_URL)` | Ollama's `/v1/chat/completions` |

### Model settings passed to the model

```text
{ "temperature": 0.4 }                          # LLM_REASONING_EFFORT unset
{ "temperature": 0.4, "thinking": False }       # off | none
{ "temperature": 0.4, "thinking": "<level>" }   # minimal | low | medium | high | xhigh
```

`thinking` is pydantic-ai's provider-neutral setting (research R3). Mapping to `reasoning.effort` (OpenAI) or Gemini's thinking config, and dropping it for models without reasoning, happens inside pydantic-ai.

## Rejected request (log only)

Not persisted. Derived from a `pydantic_ai.exceptions.ModelHTTPError` in the job runner (research R5).

| Field | From |
|---|---|
| provider | `LLM_PROVIDER` (as configured) |
| model | `exc.model_name` |
| status | `exc.status_code`; only 400, 401, 403, 404, 422 count as a rejected configuration |
| provider message | `exc.body["message"]` if the body is a dict with a string `message`; otherwise `str(exc.body)`, truncated to 500 characters |

The job itself still ends with `FailureReason.LLM_ERROR`.
