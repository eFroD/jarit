"""This agent obtains the description of a recipe and validates it against the pydantic standard for recipes."""

import asyncio

from pydantic_ai import Agent, RunContext

from jarit.agents.deps import ExtractionDeps
from jarit.agents.model_factory import create_model
from jarit.jobs.errors import TranscriptionFailedError, VideoUnreachableError
from jarit.jobs.models import JobStatus
from jarit.models.input_models.video import VideoUrl
from jarit.models.output_models import RecipeResponse
from jarit.models.output_models.video import (
    VideoDescriptionResponse,
    VideoTranscriptResponse,
)
from jarit.tools import video_loader


async def _report(ctx: RunContext[ExtractionDeps | None], stage: JobStatus) -> None:
    # Runs without deps (e.g. tests/model_eval) simply skip progress reporting.
    if ctx.deps is not None:
        await ctx.deps.report(stage)


async def get_description(
    ctx: RunContext[ExtractionDeps | None], input: VideoUrl
) -> VideoDescriptionResponse:
    """Get video description and title with yt-dlp."""
    await _report(ctx, JobStatus.FETCHING_DESCRIPTION)
    try:
        description = await asyncio.to_thread(video_loader.get_description, input)
    except Exception as e:
        raise VideoUnreachableError() from e
    await _report(ctx, JobStatus.EXTRACTING)
    return description


async def get_transcript(
    ctx: RunContext[ExtractionDeps | None], input: VideoUrl
) -> VideoTranscriptResponse:
    """
    Extract audio using yt-dlp, transcribe it using OpenAI Whisper API.
    Returns transcript text as a Pydantic model.
    """
    await _report(ctx, JobStatus.TRANSCRIBING)
    try:
        transcript = await asyncio.to_thread(video_loader.get_transcript, input)
    except Exception as e:
        raise TranscriptionFailedError() from e
    await _report(ctx, JobStatus.EXTRACTING)
    return transcript


model = create_model()
video_agent = Agent(
    model=model,
    deps_type=ExtractionDeps | None,
    tools=[get_description, get_transcript],
    output_type=RecipeResponse,
    system_prompt="""You are a precise and cautious Recipe Extraction agent.

- Your input is an URL pointing to a video source.
- First, call the tool fetch_description(URL) to retrieve the video description.
- Carefully analyze the description for recipe information.
- **Do not hallucinate or guess ingredients or instructions. Only use information actually present.**
- If the description does not contain enough information to form a complete recipe, then call the tool transcribe_video(URL) to obtain the full transcript.
- Combine the description and transcript texts and re-analyze for recipe completeness.
- Only after confirming sufficient information is available based on the combined data, extract the full recipe.
- you may improve the readability of the recipe to make it more actionable by putting the cooking times of certain steps at the right place.
- Focus on typical neutral recipe language, you would find in Books.
- If necessary, translate the complete recipe into the target language specified in the user query.
- Use the exact schema and fields defined by the Recipe pydantic model. Fields that you cannot obtain from the description or transcript should be left with an empty string "".
- If you are sure, that this is a recipie, but you cannot obtain all the required fields, output the version that strictly uses the info available from the transcript and the description in "recipe" and
    a "suggested_version" that fills in the missing fields (e.g. Prep time) with plausible values in the "suggested_version" key.
- Do not create any information not present in the description or transcript in the recipie filed.
- Return only the JSON output, no additional explanation or commentary.

Be methodical and only use the tools when required.

""",
)
