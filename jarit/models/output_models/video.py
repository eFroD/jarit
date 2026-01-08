"""Output models for video related uses."""

from pydantic import BaseModel
from typing import Optional


class VideoDescriptionResponse(BaseModel):
    description: str
    title: Optional[str] = None
    image: Optional[str] = None


# Tool Output for Transcript
class VideoTranscriptResponse(BaseModel):
    transcript: str
