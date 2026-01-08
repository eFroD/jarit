"""Input models for video related uses."""

from pydantic import BaseModel, HttpUrl


class VideoUrl(BaseModel):
    url: str


class VideoRequest(BaseModel):
    url: HttpUrl
    target_language: str = "english"
