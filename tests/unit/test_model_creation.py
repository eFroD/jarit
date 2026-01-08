import pytest
from jarit.agents.model_factory import create_model
from pydantic_ai.models.openai import OpenAIChatModel
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
            OpenAIChatModel,
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
