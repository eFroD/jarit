"""Runs one recipe extraction with the video agent."""

from collections.abc import Awaitable, Callable

from jarit.agents.deps import ExtractionDeps
from jarit.agents.video_agent import video_agent
from jarit.jobs.models import JobStatus
from jarit.languages import prompt_name
from jarit.models.output_models.recipe import RecipeResponse


async def extract(
    url: str,
    target_language: str,
    report: Callable[[JobStatus], Awaitable[None]],
) -> RecipeResponse:
    response = await video_agent.run(
        f"Please extract the recipe from the given url: {url}. "
        f"The target language is {prompt_name(target_language)}.",
        deps=ExtractionDeps(report=report),
    )
    return RecipeResponse.model_validate(response.output)
