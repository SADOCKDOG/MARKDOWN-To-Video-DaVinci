"""Abstract base class for image generation providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ...models.assets import AssetRegistry, ImageJob


class ImageProvider(ABC):
    """Pluggable backend for text-to-image generation.

    Concrete implementations handle communication with the actual backend
    (local model, API, etc.).  The contract is simple: accept an
    :class:`~markdown_to_video_davinci.models.assets.ImageJob`, produce an
    image file at ``job.output_path``, and return the updated job.
    """

    @abstractmethod
    def generate(self, job: ImageJob) -> ImageJob:
        """Generate one image and return the updated job with state set to
        ``generated`` (or ``rejected`` on failure).
        """

    def run_registry(self, registry: AssetRegistry) -> AssetRegistry:
        """Process all ``planned`` image jobs in *registry* and return it."""
        from ...models.canonical import AssetState

        for i, job in enumerate(registry.image_jobs):
            if job.state == AssetState.PLANNED:
                registry.image_jobs[i] = self.generate(job)
        return registry
