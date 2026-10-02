"""Failure types of an extraction and their user-facing reasons.

The tools raise the typed errors where the cause is unambiguous; everything else
is classified by exception type. Exception messages never leave the log.
"""

import httpx
import openai
from google.genai import errors as google_errors
from pydantic_ai.exceptions import AgentRunError

from jarit.jobs.models import FailureReason


class ExtractionError(Exception):
    """Base class for errors with a known user-facing reason."""


class VideoUnreachableError(ExtractionError):
    """The video or its description could not be loaded."""


class TranscriptionFailedError(ExtractionError):
    """Downloading or transcribing the audio failed."""


_LLM_ERRORS = (AgentRunError, openai.APIError, google_errors.APIError, httpx.HTTPError)


def classify(exc: BaseException) -> FailureReason:
    if isinstance(exc, VideoUnreachableError):
        return FailureReason.VIDEO_UNREACHABLE
    if isinstance(exc, TranscriptionFailedError):
        return FailureReason.TRANSCRIPTION_FAILED
    if isinstance(exc, TimeoutError):
        return FailureReason.TIMEOUT
    if isinstance(exc, _LLM_ERRORS):
        return FailureReason.LLM_ERROR
    return FailureReason.UNKNOWN
