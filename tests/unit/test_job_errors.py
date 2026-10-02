import httpx
import openai
import pytest
from google.genai import errors as google_errors
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior

from jarit.jobs.errors import TranscriptionFailedError, VideoUnreachableError, classify
from jarit.jobs.models import FailureReason


@pytest.mark.parametrize(
    "exc, reason",
    [
        (VideoUnreachableError(), FailureReason.VIDEO_UNREACHABLE),
        (TranscriptionFailedError(), FailureReason.TRANSCRIPTION_FAILED),
        (TimeoutError(), FailureReason.TIMEOUT),
        (ModelHTTPError(503, "model"), FailureReason.LLM_ERROR),
        (UnexpectedModelBehavior("bad output"), FailureReason.LLM_ERROR),
        (
            openai.APIConnectionError(request=httpx.Request("POST", "https://x")),
            FailureReason.LLM_ERROR,
        ),
        (google_errors.APIError(500, {}), FailureReason.LLM_ERROR),
        (httpx.ConnectError("refused"), FailureReason.LLM_ERROR),
        (ValueError("bug"), FailureReason.UNKNOWN),
    ],
)
def test_classify(exc, reason):
    assert classify(exc) == reason
