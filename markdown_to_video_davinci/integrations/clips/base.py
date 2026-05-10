"""Abstract base class for clip assembly runners."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...models.assets import AssetRegistry, ClipJob


class ClipRunner(ABC):
    """Pluggable backend for assembling base video clips.

    Concrete implementations accept a :class:`~markdown_to_video_davinci.models.assets.ClipJob`
    (image + optional audio + duration), produce an MP4 clip at ``job.output_path``,
    and return the updated job with ``state`` set to ``generated`` or ``rejected``.
    """

    @abstractmethod
    def assemble(self, job: ClipJob) -> ClipJob:
        """Assemble one base clip and return the updated job."""

    def run_registry(self, registry: AssetRegistry) -> AssetRegistry:
        """Process all ``planned`` clip jobs in *registry* and return it."""
        from ...models.canonical import AssetState

        for i, job in enumerate(registry.clip_jobs):
            if job.state == AssetState.PLANNED:
                registry.clip_jobs[i] = self.assemble(job)
        return registry
