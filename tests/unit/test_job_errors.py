import httpx
import httpx2
import openai
import pytest
from google.genai import errors as google_errors
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior

from jarit.jobs.errors import (
    TranscriptionFailedError,
    VideoUnreachableError,
    classify,
    describe_rejected_request,
)
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
            openai.APIConnectionError(request=httpx2.Request("POST", "https://x")),
            FailureReason.LLM_ERROR,
        ),
        (google_errors.APIError(500, {}), FailureReason.LLM_ERROR),
        (httpx.ConnectError("refused"), FailureReason.LLM_ERROR),
        (httpx2.ConnectError("refused"), FailureReason.LLM_ERROR),
        (ValueError("bug"), FailureReason.UNKNOWN),
    ],
)
def test_classify(exc, reason):
    assert classify(exc) == reason


GPT6_REJECTION = ModelHTTPError(
    status_code=400,
    model_name="gpt-6-luna",
    body={
        "message": "Function tools with reasoning_effort are not supported for "
        "gpt-6-luna in /v1/chat/completions. To use function tools, use "
        "/v1/responses or set reasoning_effort to 'none'.",
        "type": "invalid_request_error",
        "param": "reasoning_effort",
        "code": None,
    },
)


def test_rejected_request_names_model_status_and_reason():
    text = describe_rejected_request(GPT6_REJECTION)
    assert "model=gpt-6-luna" in text
    assert "status=400" in text
    assert "Function tools with reasoning_effort" in text


def test_rejected_request_stays_an_llm_error_for_users():
    assert classify(GPT6_REJECTION) == FailureReason.LLM_ERROR


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_configuration_statuses_are_described(status):
    assert describe_rejected_request(ModelHTTPError(status, "m", {"message": "x"}))


@pytest.mark.parametrize("status", [408, 409, 429, 500, 503])
def test_transient_statuses_are_not_described(status):
    assert (
        describe_rejected_request(ModelHTTPError(status, "m", {"message": "x"})) is None
    )


@pytest.mark.parametrize(
    "body, expected",
    [("plain text", "plain text"), (None, "None"), ({"error": "x"}, "error")],
)
def test_bodies_without_a_message_are_still_described(body, expected):
    assert expected in describe_rejected_request(ModelHTTPError(400, "m", body))


def test_long_provider_messages_are_truncated():
    text = describe_rejected_request(ModelHTTPError(400, "m", {"message": "x" * 2000}))
    assert text.count("x") == 500


@pytest.mark.parametrize(
    "exc", [UnexpectedModelBehavior("x"), TimeoutError(), ValueError("bug")]
)
def test_other_errors_are_not_described(exc):
    assert describe_rejected_request(exc) is None
