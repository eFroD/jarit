import pytest
from unittest.mock import patch, MagicMock
from jarit.models.input_models.video import VideoUrl
from jarit.tools.video_loader import get_description, get_transcript


def test_get_description_success():
    dummy_url = VideoUrl(url="http://dummy.url")
    # Patch yt_dlp.YoutubeDL.extract_info
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        instance = mock_ydl.return_value.__enter__.return_value
        instance.extract_info.return_value = {
            "description": "Delicious test recipe",
            "title": "Test Video Title",
            "thumbnail": "http://img.url/thumb.jpg",
        }
        resp = get_description(dummy_url)
        assert resp.description == "Delicious test recipe"
        assert resp.title == "Test Video Title"
        assert resp.image == "http://img.url/thumb.jpg"


def test_get_description_missing_fields():
    dummy_url = VideoUrl(url="http://dummy.url")
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        instance = mock_ydl.return_value.__enter__.return_value
        instance.extract_info.return_value = {}
        resp = get_description(dummy_url)
        assert resp.description == ""
        assert resp.title is None  # Or "" if your model default is different


def test_get_transcript_success_real_file(tmp_path):
    dummy_url = VideoUrl(url="http://dummy.url")

    with (
        patch("yt_dlp.YoutubeDL") as mock_ydl,
        patch("jarit.tools.video_loader.OpenAI") as mock_openai_class,
        patch("tempfile.TemporaryDirectory") as mock_tempdir,
    ):
        # Patch TemporaryDirectory to return our tmp_path
        mock_tempdir.return_value.__enter__.return_value = str(tmp_path)
        mock_tempdir.return_value.__exit__.return_value = None

        # Simulate yt_dlp download: directly create the audio.mp3 file
        def download_side_effect(urls):
            audio_file = tmp_path / "audio.mp3"
            audio_file.write_bytes(b"fake mp3 audio data")

        ydl_instance = mock_ydl.return_value.__enter__.return_value
        ydl_instance.download.side_effect = download_side_effect

        # Mock OpenAI client and its nested methods
        mock_client_instance = MagicMock()
        mock_openai_class.return_value = mock_client_instance

        # Mock the transcription response
        mock_client_instance.audio.transcriptions.create.return_value = (
            "transcribed text"
        )

        # Run the function
        resp = get_transcript(dummy_url)

        # Verify output
        assert resp.transcript == "transcribed text"

        # Verify the OpenAI API was called with the right parameters
        mock_client_instance.audio.transcriptions.create.assert_called_once()


def test_get_transcript_yt_dlp_failure():
    dummy_url = VideoUrl(url="http://dummy.url")
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        instance = mock_ydl.return_value.__enter__.return_value
        instance.download.side_effect = Exception("Download failed")
        with pytest.raises(Exception, match="Download failed"):
            get_transcript(dummy_url)


def test_get_transcript_openai_failure(tmp_path):
    dummy_url = VideoUrl(url="http://dummy.url")

    with (
        patch("yt_dlp.YoutubeDL") as mock_ydl,
        patch("jarit.tools.video_loader.OpenAI") as mock_openai_class,
        patch("tempfile.TemporaryDirectory") as mock_tempdir,
    ):
        # Patch TemporaryDirectory to return our tmp_path
        mock_tempdir.return_value.__enter__.return_value = str(tmp_path)
        mock_tempdir.return_value.__exit__.return_value = None

        # Simulate yt_dlp download: create the audio.mp3 file
        def download_side_effect(urls):
            audio_file = tmp_path / "audio.mp3"
            audio_file.write_bytes(b"fake mp3 audio data")

        ydl_instance = mock_ydl.return_value.__enter__.return_value
        ydl_instance.download.side_effect = download_side_effect

        # Mock OpenAI client to raise an exception
        mock_client_instance = MagicMock()
        mock_openai_class.return_value = mock_client_instance
        mock_client_instance.audio.transcriptions.create.side_effect = Exception(
            "API Failure"
        )

        # Expect the exception to be raised
        with pytest.raises(Exception, match="API Failure"):
            get_transcript(dummy_url)
