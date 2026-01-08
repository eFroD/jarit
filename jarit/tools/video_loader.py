"""A module for downloading video files for description extraction and - if needed further transcription."""

import yt_dlp
import os
import tempfile
from openai import OpenAI

from jarit.models.input_models.video import VideoUrl
from jarit.models.output_models.video import (
    VideoDescriptionResponse,
    VideoTranscriptResponse,
)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


def get_description(input: VideoUrl) -> VideoDescriptionResponse:
    """Get video description and title with yt-dlp."""
    with yt_dlp.YoutubeDL({}) as ydl:
        info = ydl.extract_info(input.url, download=False)
        return VideoDescriptionResponse(
            description=info.get("description", ""),
            title=info.get("title"),
            image=info.get("thumbnail"),
        )


def get_transcript(input: VideoUrl) -> VideoTranscriptResponse:
    """
    Extract audio using yt-dlp, transcribe it using OpenAI Whisper API.
    Returns transcript text as a Pydantic model. Assumes 'openai' package v1+.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        audio_path = os.path.join(tmp_dir, "audio")
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": audio_path,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([input.url])

        client = OpenAI(api_key=OPENAI_API_KEY)
        with open(audio_path + ".mp3", "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1", file=audio_file, response_format="text"
            )
        return VideoTranscriptResponse(transcript=response)
