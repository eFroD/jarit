"""The real video agent with a scripted model: stage reporting and error typing."""

import os

import pytest
from pydantic_ai.messages import (
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

os.environ.setdefault("GOOGLE_API_KEY", "test-dummy")  # model is never called

from yt_dlp.utils import DownloadError  # noqa: E402

from jarit.agents.video_agent import video_agent  # noqa: E402
from jarit.jobs import pipeline  # noqa: E402
from jarit.jobs.errors import TranscriptionFailedError, VideoUnreachableError  # noqa: E402
from jarit.jobs.models import JobStatus  # noqa: E402
from jarit.models.output_models.video import (  # noqa: E402
    VideoDescriptionResponse,
    VideoTranscriptResponse,
)
from tests.factories import make_response  # noqa: E402

pytestmark = pytest.mark.asyncio

URL = "https://example.com/reel/1"


def scripted_model(tools: list[str]) -> FunctionModel:
    """Calls the given tools one per turn, then returns a recipe."""

    def respond(messages, info: AgentInfo) -> ModelResponse:
        done = sum(
            isinstance(part, ToolReturnPart)
            for message in messages
            for part in message.parts
        )
        if done < len(tools):
            return ModelResponse(parts=[ToolCallPart(tools[done], {"url": URL})])
        output = make_response("Soup").model_dump(mode="json", by_alias=True)
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, output)])

    return FunctionModel(respond)


@pytest.fixture
def loader(monkeypatch):
    calls = []

    def description(input):
        calls.append("description")
        return VideoDescriptionResponse(description="Some text", title="Soup")

    def transcript(input):
        calls.append("transcript")
        return VideoTranscriptResponse(transcript="Add salt")

    monkeypatch.setattr("jarit.tools.video_loader.get_description", description)
    monkeypatch.setattr("jarit.tools.video_loader.get_transcript", transcript)
    return calls


async def run(tools):
    stages = []

    async def report(stage):
        stages.append(stage)

    with video_agent.override(model=scripted_model(tools)):
        response = await pipeline.extract(URL, "en", report)
    return response, stages


async def test_description_only_skips_transcription(loader):
    response, stages = await run(["get_description"])

    assert response.recipe.name == "Soup"
    assert loader == ["description"]
    assert stages == [JobStatus.FETCHING_DESCRIPTION, JobStatus.EXTRACTING]


async def test_transcription_is_reported_when_used(loader):
    _, stages = await run(["get_description", "get_transcript"])

    assert loader == ["description", "transcript"]
    assert stages == [
        JobStatus.FETCHING_DESCRIPTION,
        JobStatus.EXTRACTING,
        JobStatus.TRANSCRIBING,
        JobStatus.EXTRACTING,
    ]


async def test_unreachable_video(monkeypatch):
    def fail(input):
        raise DownloadError("ERROR: [youtube] xyz: Video unavailable")

    monkeypatch.setattr("jarit.tools.video_loader.get_description", fail)
    with pytest.raises(VideoUnreachableError):
        await run(["get_description"])


async def test_failed_transcription(loader, monkeypatch):
    def fail(input):
        raise RuntimeError("whisper exploded")

    monkeypatch.setattr("jarit.tools.video_loader.get_transcript", fail)
    with pytest.raises(TranscriptionFailedError):
        await run(["get_description", "get_transcript"])


async def test_agent_runs_without_deps(loader):
    # tests/model_eval runs the agent without job context.
    with video_agent.override(model=scripted_model(["get_description"])):
        result = await video_agent.run("extract")
    assert result.output.recipe.name == "Soup"


async def prompt_for(language: str) -> str:
    prompts = []

    def respond(messages, info: AgentInfo) -> ModelResponse:
        prompts.extend(
            part.content
            for part in messages[0].parts
            if isinstance(part, UserPromptPart)
        )
        output = make_response("Soup").model_dump(mode="json", by_alias=True)
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, output)])

    async def report(stage):
        pass

    with video_agent.override(model=FunctionModel(respond)):
        await pipeline.extract(URL, language, report)
    return prompts[0]


async def test_prompt_names_the_language():
    assert "The target language is German." in await prompt_for("de")


async def test_prompt_passes_legacy_language_through():
    assert "The target language is japanese." in await prompt_for("japanese")
