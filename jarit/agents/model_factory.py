"""A Factory to create different LLM models based on configuration."""

import os
from typing import Union
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.settings import ModelSettings

REASONING_EFFORT_ENV = "LLM_REASONING_EFFORT"
_REASONING_LEVELS = ("minimal", "low", "medium", "high", "xhigh")


def _reasoning_setting() -> bool | str | None:
    """Map LLM_REASONING_EFFORT to pydantic-ai's provider-neutral `thinking` setting.

    Unset or empty means the model's own default. pydantic-ai drops the setting for
    models that can't reason, so it is safe for every provider.
    """
    raw = os.getenv(REASONING_EFFORT_ENV, "")
    value = raw.strip().lower()
    if not value:
        return None
    if value in ("off", "none"):
        return False
    if value in _REASONING_LEVELS:
        return value
    raise ValueError(
        f"Unsupported {REASONING_EFFORT_ENV}: {raw!r}. "
        f"Use one of: off, none, {', '.join(_REASONING_LEVELS)}, or leave it unset."
    )


def create_model() -> Union[OpenAIResponsesModel, OpenAIChatModel, GoogleModel]:
    """Create a model based on the configuration in environment variables.

    Returns:
        An OpenAIResponsesModel (openai), GoogleModel (google) or OpenAIChatModel
        (ollama), based on the LLM_PROVIDER env variable.
    """
    model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash")
    provider = os.getenv("LLM_PROVIDER", "google").lower()
    ollama_url = os.getenv("OLLAMA_URL", None)

    # pydantic-ai drops the temperature itself while an OpenAI model is reasoning.
    settings: ModelSettings = {"temperature": 0.4}
    thinking = _reasoning_setting()
    if thinking is not None:
        settings["thinking"] = thinking

    if provider == "openai":
        # Reasoning models only accept tool calls with reasoning on via the Responses API.
        return OpenAIResponsesModel(model_name=model_name, settings=settings)
    elif provider == "google":
        return GoogleModel(model_name=model_name, settings=settings)
    elif provider == "ollama":
        # Ollama's OpenAI-compatible API only offers Chat Completions.
        return OpenAIChatModel(
            model_name=model_name,
            provider=OllamaProvider(ollama_url),
            settings=settings,
        )
    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: {provider}. Supported providers are 'openai', 'google', and 'ollama'. Make sure to check your .env file."
        )
