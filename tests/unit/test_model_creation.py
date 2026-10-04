import pytest
from pydantic_ai.models import ModelRequestParameters
from jarit.agents.model_factory import create_model
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider


@pytest.mark.parametrize(
    "env,expected_type,expected_name,expected_provider",
    [
        (
            {
                "LLM_PROVIDER": "openai",
                "MODEL_NAME": "gpt-4",
                "OPENAI_API_KEY": "sk-test",
                "GOOGLE_API_KEY": "test-google-key",
            },
            OpenAIResponsesModel,
            "gpt-4",
            OpenAIProvider,
        ),
        (
            {
                "LLM_PROVIDER": "google",
                "MODEL_NAME": "gemini-pro",
                "OPENAI_API_KEY": "sk-test",
                "GOOGLE_API_KEY": "test-google-key",
            },
            GoogleModel,
            "gemini-pro",
            GoogleProvider,
        ),
        (
            {
                "LLM_PROVIDER": "ollama",
                "MODEL_NAME": "llama3",
                "OLLAMA_URL": "http://localhost:11434",
                "OPENAI_API_KEY": "sk-test",
                "GOOGLE_API_KEY": "test-google-key",
            },
            OpenAIChatModel,
            "llama3",
            OllamaProvider,
        ),
        (
            {
                "OPENAI_API_KEY": "sk-test",
                "GOOGLE_API_KEY": "test-google-key",
            },
            GoogleModel,
            "gemini-2.5-flash",
            GoogleProvider,
        ),
    ],
)
def test_create_model(
    env, expected_type, expected_name, expected_provider, monkeypatch
):
    # Remove all possible keys first
    for var in (
        "LLM_PROVIDER",
        "MODEL_NAME",
        "OLLAMA_URL",
        "OPENAI_API_KEY",
        "GOOGLE_API_KEY",
        "LLM_REASONING_EFFORT",
    ):
        monkeypatch.delenv(var, raising=False)
    # Set needed env vars
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    model = create_model()
    assert isinstance(model, expected_type)
    assert getattr(model, "model_name", None) == expected_name
    if expected_provider:
        assert isinstance(getattr(model, "_provider", None), expected_provider)


def test_invalid_provider(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("LLM_PROVIDER", "unknown_provider")
    with pytest.raises(ValueError):
        create_model()


def test_openai_gpt6_profile_supports_reasoning(monkeypatch):
    # Guards against a pydantic-ai version that doesn't know the gpt-6 family yet.
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("MODEL_NAME", "gpt-6-luna")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert create_model().profile.get("supports_thinking") is True


PROVIDER_ENVS = {
    "openai": {"LLM_PROVIDER": "openai", "MODEL_NAME": "gpt-6-luna"},
    "google": {"LLM_PROVIDER": "google", "MODEL_NAME": "gemini-2.5-flash"},
    "ollama": {
        "LLM_PROVIDER": "ollama",
        "MODEL_NAME": "llama3",
        "OLLAMA_URL": "http://localhost:11434/v1",
    },
}


def _set_env(monkeypatch, provider, effort):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    for k, v in PROVIDER_ENVS[provider].items():
        monkeypatch.setenv(k, v)
    if effort is None:
        monkeypatch.delenv("LLM_REASONING_EFFORT", raising=False)
    else:
        monkeypatch.setenv("LLM_REASONING_EFFORT", effort)


_UNSET = object()


@pytest.mark.parametrize("provider", PROVIDER_ENVS)
@pytest.mark.parametrize(
    "effort, thinking",
    [
        (None, _UNSET),
        ("", _UNSET),
        ("off", False),
        ("none", False),
        ("low", "low"),
        (" HIGH ", "high"),
        ("xhigh", "xhigh"),
    ],
)
def test_reasoning_effort_setting(provider, effort, thinking, monkeypatch):
    _set_env(monkeypatch, provider, effort)
    settings = create_model().settings
    assert settings["temperature"] == 0.4
    if thinking is _UNSET:
        assert "thinking" not in settings
    else:
        assert settings["thinking"] == thinking


def test_invalid_reasoning_effort(monkeypatch):
    _set_env(monkeypatch, "openai", "fast")
    with pytest.raises(ValueError, match="LLM_REASONING_EFFORT") as exc_info:
        create_model()
    assert "'fast'" in str(exc_info.value)
    assert "xhigh" in str(exc_info.value)


def test_reasoning_setting_dropped_for_unsupported_ollama_model(monkeypatch):
    """pydantic-ai strips `thinking` in `Model.prepare_request` when the profile
    has no thinking support, so the setting can't break a plain Ollama model."""
    _set_env(monkeypatch, "ollama", "high")
    model = create_model()
    settings, params = model.prepare_request(None, ModelRequestParameters())
    assert "thinking" not in (settings or {})
    assert params.thinking is None
