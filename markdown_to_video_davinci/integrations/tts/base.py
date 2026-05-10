"""Abstract base class for TTS (text-to-speech) providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...models.assets import AssetRegistry, VoiceJob


class TTSProvider(ABC):
    """Pluggable backend for speech synthesis.

    Concrete implementations synthesise the dialogue line in a :class:`VoiceJob`
    and write a WAV file to ``job.output_path``.
    """

    @abstractmethod
    def synthesise(self, job: VoiceJob) -> VoiceJob:
        """Synthesise one dialogue cue and return the updated job."""

    def run_registry(self, registry: AssetRegistry) -> AssetRegistry:
        """Process all ``planned`` voice jobs in *registry* and return it."""
        from ...models.canonical import AssetState

        for i, job in enumerate(registry.voice_jobs):
            if job.state == AssetState.PLANNED:
                registry.voice_jobs[i] = self.synthesise(job)
        return registry
