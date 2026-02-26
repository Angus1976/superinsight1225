"""
Media transcriber for SuperInsight Platform.

Transcribes audio and video files to text using OpenAI Whisper API.
Video files are first processed with ffmpeg to extract the audio track.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import tempfile

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
SUPPORTED_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500MB


class MediaTranscriber:
    """Transcribes audio/video files to text via Whisper API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "whisper-1",
    ) -> None:
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._base_url = base_url or os.getenv(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        )
        self._model = model

    async def transcribe(self, file_path: str) -> str:
        """Transcribe an audio or video file to text.

        For video files, ffmpeg extracts the audio track first.
        For audio files, the file is sent directly to Whisper API.

        Args:
            file_path: Path to the media file on disk.

        Returns:
            Transcribed text string.

        Raises:
            FileNotFoundError: If file_path does not exist.
            ValueError: If file is empty, too large, or unsupported format.
            RuntimeError: If ffmpeg or Whisper API fails.
        """
        self._validate_file(file_path)
        ext = os.path.splitext(file_path)[1].lower()

        if ext in VIDEO_EXTENSIONS:
            return await self._transcribe_video(file_path)
        return await self._transcribe_audio(file_path)

    async def _transcribe_video(self, file_path: str) -> str:
        """Extract audio from video with ffmpeg, then transcribe."""
        self._check_ffmpeg()

        tmp_wav = None
        try:
            tmp_fd, tmp_wav = tempfile.mkstemp(suffix=".wav")
            os.close(tmp_fd)

            await self._extract_audio(file_path, tmp_wav)
            return await self._call_whisper(tmp_wav)
        finally:
            if tmp_wav and os.path.exists(tmp_wav):
                os.unlink(tmp_wav)

    async def _transcribe_audio(self, file_path: str) -> str:
        """Send audio file directly to Whisper API."""
        return await self._call_whisper(file_path)

    async def _extract_audio(self, video_path: str, output_path: str) -> None:
        """Use ffmpeg subprocess to extract audio track as WAV."""
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vn",            # no video
            "-acodec", "pcm_s16le",
            "-ar", "16000",   # 16kHz sample rate for Whisper
            "-ac", "1",       # mono
            "-y",             # overwrite
            output_path,
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode(errors="replace").strip()
            raise RuntimeError(
                f"ffmpeg audio extraction failed (exit {process.returncode}): "
                f"{error_msg[:500]}"
            )

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError("ffmpeg produced empty or missing output file")

        logger.info("Extracted audio from %s to %s", video_path, output_path)

    async def _call_whisper(self, audio_path: str) -> str:
        """Call OpenAI Whisper API to transcribe audio."""
        if not self._api_key:
            raise RuntimeError(
                "OpenAI API key is required for Whisper transcription. "
                "Set OPENAI_API_KEY environment variable."
            )

        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )

        try:
            with open(audio_path, "rb") as audio_file:
                response = await client.audio.transcriptions.create(
                    model=self._model,
                    file=audio_file,
                )
        except Exception as exc:
            raise RuntimeError(f"Whisper API transcription failed: {exc}") from exc

        text = response.text.strip()
        logger.info(
            "Transcribed %s (%d chars)", audio_path, len(text),
        )
        return text

    def _validate_file(self, file_path: str) -> None:
        """Validate file existence, extension, and size."""
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file extension: '{ext}'. "
                f"Supported: {sorted(SUPPORTED_EXTENSIONS)}"
            )

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError("File is empty")
        if file_size > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds "
                f"limit of {MAX_FILE_SIZE_BYTES / 1024 / 1024:.0f}MB"
            )

    @staticmethod
    def _check_ffmpeg() -> None:
        """Verify ffmpeg is available on PATH."""
        if shutil.which("ffmpeg") is None:
            raise RuntimeError(
                "ffmpeg is required for video transcription. "
                "Install with: apt-get install ffmpeg (or brew install ffmpeg)"
            )
