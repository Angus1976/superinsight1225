"""Unit tests for MediaTranscriber."""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.extractors.media import (
    AUDIO_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    SUPPORTED_EXTENSIONS,
    VIDEO_EXTENSIONS,
    MediaTranscriber,
)


@pytest.fixture
def transcriber():
    return MediaTranscriber(api_key="test-key-123")


def _create_file(path: str, size: int = 1024) -> str:
    """Helper: create a dummy file with given size."""
    with open(path, "wb") as f:
        f.write(b"\x00" * size)
    return path


class TestMediaTranscriberValidation:
    """Tests for input validation."""

    def test_file_not_found(self, transcriber):
        with pytest.raises(FileNotFoundError, match="File not found"):
            asyncio.get_event_loop().run_until_complete(
                transcriber.transcribe("/nonexistent/path/file.mp4")
            )

    def test_unsupported_extension(self, transcriber, tmp_path):
        path = str(tmp_path / "test.pdf")
        _create_file(path)

        with pytest.raises(ValueError, match="Unsupported file extension"):
            asyncio.get_event_loop().run_until_complete(
                transcriber.transcribe(path)
            )

    def test_empty_file(self, transcriber, tmp_path):
        path = str(tmp_path / "test.mp3")
        _create_file(path, size=0)

        with pytest.raises(ValueError, match="File is empty"):
            asyncio.get_event_loop().run_until_complete(
                transcriber.transcribe(path)
            )

    def test_file_too_large(self, transcriber, tmp_path):
        path = str(tmp_path / "test.mp3")
        # Create a file that appears too large via mock
        _create_file(path, size=100)

        with patch("os.path.getsize", return_value=MAX_FILE_SIZE_BYTES + 1):
            with pytest.raises(ValueError, match="exceeds limit"):
                asyncio.get_event_loop().run_until_complete(
                    transcriber.transcribe(path)
                )

    def test_all_audio_extensions_accepted(self, transcriber, tmp_path):
        """All audio extensions pass validation (no ValueError)."""
        for ext in AUDIO_EXTENSIONS:
            path = str(tmp_path / f"test{ext}")
            _create_file(path)
            # Validation should pass (will fail later at Whisper call)
            transcriber._validate_file(path)

    def test_all_video_extensions_accepted(self, transcriber, tmp_path):
        """All video extensions pass validation (no ValueError)."""
        for ext in VIDEO_EXTENSIONS:
            path = str(tmp_path / f"test{ext}")
            _create_file(path)
            transcriber._validate_file(path)


class TestMediaTranscriberAudio:
    """Tests for audio transcription (direct Whisper call)."""

    @pytest.mark.asyncio
    async def test_audio_calls_whisper_directly(self, transcriber, tmp_path):
        """Audio files should be sent directly to Whisper without ffmpeg."""
        path = str(tmp_path / "test.mp3")
        _create_file(path)

        mock_response = MagicMock()
        mock_response.text = "Hello world transcription"

        mock_client_instance = MagicMock()
        mock_client_instance.audio.transcriptions.create = AsyncMock(
            return_value=mock_response
        )

        with patch("openai.AsyncOpenAI", return_value=mock_client_instance):
            result = await transcriber.transcribe(path)

        assert result == "Hello world transcription"
        mock_client_instance.audio.transcriptions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_audio_missing_api_key(self, tmp_path):
        """Should raise RuntimeError when API key is missing."""
        t = MediaTranscriber(api_key="")
        path = str(tmp_path / "test.mp3")
        _create_file(path)

        with pytest.raises(RuntimeError, match="API key is required"):
            await t.transcribe(path)

    @pytest.mark.asyncio
    async def test_whisper_api_failure(self, transcriber, tmp_path):
        """Should wrap Whisper API errors in RuntimeError."""
        path = str(tmp_path / "test.wav")
        _create_file(path)

        mock_client_instance = MagicMock()
        mock_client_instance.audio.transcriptions.create = AsyncMock(
            side_effect=Exception("API timeout")
        )

        with patch("openai.AsyncOpenAI", return_value=mock_client_instance):
            with pytest.raises(RuntimeError, match="Whisper API transcription failed"):
                await transcriber.transcribe(path)


class TestMediaTranscriberVideo:
    """Tests for video transcription (ffmpeg + Whisper)."""

    @pytest.mark.asyncio
    async def test_video_extracts_audio_then_transcribes(self, transcriber, tmp_path):
        """Video files should use ffmpeg to extract audio, then call Whisper."""
        path = str(tmp_path / "test.mp4")
        _create_file(path)

        mock_response = MagicMock()
        mock_response.text = "Video transcription result"

        mock_client_instance = MagicMock()
        mock_client_instance.audio.transcriptions.create = AsyncMock(
            return_value=mock_response
        )

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("asyncio.create_subprocess_exec", return_value=mock_process), \
             patch("openai.AsyncOpenAI", return_value=mock_client_instance), \
             patch("os.path.exists", side_effect=lambda p: True), \
             patch("os.path.getsize", side_effect=lambda p: 1024), \
             patch("os.path.isfile", return_value=True), \
             patch("os.unlink"):
            result = await transcriber.transcribe(path)

        assert result == "Video transcription result"

    @pytest.mark.asyncio
    async def test_video_ffmpeg_not_installed(self, transcriber, tmp_path):
        """Should raise RuntimeError when ffmpeg is not available."""
        path = str(tmp_path / "test.mp4")
        _create_file(path)

        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="ffmpeg is required"):
                await transcriber.transcribe(path)

    @pytest.mark.asyncio
    async def test_video_ffmpeg_failure(self, transcriber, tmp_path):
        """Should raise RuntimeError when ffmpeg exits with error."""
        path = str(tmp_path / "test.mp4")
        _create_file(path)

        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(
            return_value=(b"", b"Error: invalid input")
        )

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with pytest.raises(RuntimeError, match="ffmpeg audio extraction failed"):
                await transcriber.transcribe(path)

    @pytest.mark.asyncio
    async def test_video_cleans_up_temp_file(self, transcriber, tmp_path):
        """Temp WAV file should be cleaned up even on Whisper failure."""
        path = str(tmp_path / "test.mp4")
        _create_file(path)

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        mock_client_instance = MagicMock()
        mock_client_instance.audio.transcriptions.create = AsyncMock(
            side_effect=Exception("API error")
        )

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("asyncio.create_subprocess_exec", return_value=mock_process), \
             patch("openai.AsyncOpenAI", return_value=mock_client_instance), \
             patch("os.path.exists", return_value=True), \
             patch("os.path.getsize", side_effect=lambda p: 1024), \
             patch("os.path.isfile", return_value=True), \
             patch("os.unlink") as mock_unlink:
            with pytest.raises(RuntimeError):
                await transcriber.transcribe(path)

        # Verify temp file cleanup was attempted
        mock_unlink.assert_called_once()


class TestMediaTranscriberInit:
    """Tests for constructor defaults."""

    def test_default_api_key_from_env(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key-456"}):
            t = MediaTranscriber()
            assert t._api_key == "env-key-456"

    def test_explicit_api_key_overrides_env(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
            t = MediaTranscriber(api_key="explicit-key")
            assert t._api_key == "explicit-key"

    def test_default_model(self):
        t = MediaTranscriber(api_key="k")
        assert t._model == "whisper-1"

    def test_custom_model(self):
        t = MediaTranscriber(api_key="k", model="whisper-large-v3")
        assert t._model == "whisper-large-v3"
