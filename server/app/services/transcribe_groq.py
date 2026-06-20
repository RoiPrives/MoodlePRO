from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.core.config import settings
from app.services.srt import Segment, build_srt

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    text: str
    srt: str
    language: str


class TranscriptionProvider(ABC):
    """Cloud transcription fallback, used when no cluster GPU worker claims a queued
    job within the grace period (see app.services.fallback)."""

    @abstractmethod
    async def transcribe(self, audio_path: Path, language: str) -> TranscriptionResult:
        ...


class GroqTranscriber(TranscriptionProvider):
    """Groq whisper-large-v3 via the OpenAI-compatible /audio/transcriptions endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._api_key = api_key or settings.groq_api_key
        self._model = model or settings.groq_model
        self._base_url = (base_url or settings.groq_base_url).rstrip("/")
        if not self._api_key:
            raise RuntimeError("GROQ_API_KEY is not configured")

    async def transcribe(self, audio_path: Path, language: str) -> TranscriptionResult:
        with audio_path.open("rb") as audio_file:
            files = {"file": (audio_path.name, audio_file, "audio/wav")}
            data = {
                "model": self._model,
                "language": language,
                "response_format": "verbose_json",
            }
            async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as http_client:
                response = await http_client.post(
                    f"{self._base_url}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    data=data,
                    files=files,
                )
        response.raise_for_status()
        body = response.json()

        segments = [
            Segment(
                text=str(seg.get("text", "")).strip(),
                start=float(seg.get("start", 0.0)),
                end=float(seg.get("end", 0.0)),
            )
            for seg in body.get("segments", [])
        ]
        text = str(body.get("text", "")).strip() or " ".join(s.text for s in segments)
        return TranscriptionResult(text=text, srt=build_srt(segments), language=language)
