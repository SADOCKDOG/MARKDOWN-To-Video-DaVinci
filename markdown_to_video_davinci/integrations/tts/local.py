"""Local CPU TTS provider using pyttsx3.

Synthesises dialogue lines entirely offline without an internet connection or
GPU, making it ideal for first-pass voice drafts on a Windows 11 laptop.

Requirements
------------
``pip install pyttsx3``

On Windows 11, pyttsx3 uses the built-in Microsoft SAPI voices.  No additional
model download is required.

Usage
-----
>>> from markdown_to_video_davinci.integrations.tts.local import LocalTTSProvider
>>> provider = LocalTTSProvider(rate=150)
>>> updated_job = provider.synthesise(job)
"""

from __future__ import annotations

from pathlib import Path

from ...models.assets import VoiceJob
from ...models.canonical import AssetState
from .base import TTSProvider


class LocalTTSProvider(TTSProvider):
    """Offline speech synthesis via pyttsx3 (SAPI on Windows, espeak on Linux)."""

    def __init__(self, rate: int = 150, volume: float = 1.0) -> None:
        self._rate = rate
        self._volume = volume

    def _build_engine(self):
        try:
            import pyttsx3  # type: ignore[import]
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "The 'pyttsx3' package is required for LocalTTSProvider. "
                "Install it with: pip install pyttsx3"
            ) from exc
        engine = pyttsx3.init()
        engine.setProperty("rate", self._rate)
        engine.setProperty("volume", self._volume)
        return engine

    def synthesise(self, job: VoiceJob) -> VoiceJob:
        engine = self._build_engine()
        out_path = Path(job.output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            engine.save_to_file(job.text, str(out_path))
            engine.runAndWait()
        finally:
            engine.stop()
        if out_path.exists() and out_path.stat().st_size > 0:
            job.state = AssetState.GENERATED
        else:
            job.state = AssetState.REJECTED
        return job
