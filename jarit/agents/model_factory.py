"""A Factory to create different LLM models based on configuration."""

import os
from typing import Union
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.ollama import OllamaProvider


def create_model() -> Union[OpenAIChatModel, GoogleModel]:
    """Create a model based on the configuration in environment variables.

    Returns:
        An instance of OpenAIChatModel or GoogleModel based on the LLM_PROVIDER env variable.
    """
    model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash")
    provider = os.getenv("LLM_PROVIDER", "google").lower()
    ollama_url = os.getenv("OLLAMA_URL", None)

    if provider == "openai":
        return OpenAIChatModel(model_name=model_name, settings={"temperature": 0.4})
    elif provider == "google":
        return GoogleModel(model_name=model_name, settings={"temperature": 0.4})
    elif provider == "ollama":
        return OpenAIChatModel(
            model_name=model_name,
            provider=OllamaProvider(ollama_url),
            settings={"temperature": 0.4},
        )
    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: {provider}. Supported providers are 'openai', 'google', and 'ollama'. Make sure to check your .env file."
        )
