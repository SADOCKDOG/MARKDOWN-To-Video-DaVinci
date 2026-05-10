"""Stability AI Stable Image API provider.

Sends prompts to the Stability AI REST API (``stable-image/generate/core``
endpoint) and saves the returned PNG to the job's output path.

Requirements
------------
``pip install requests``

Environment variable
--------------------
``STABILITY_API_KEY`` — your Stability AI API key.

Usage
-----
>>> from markdown_to_video_davinci.integrations.images.stability import StabilityProvider
>>> provider = StabilityProvider()
>>> updated_job = provider.generate(job)
"""

from __future__ import annotations

import os
from pathlib import Path

from ...models.assets import ImageJob
from ...models.canonical import AssetState
from .base import ImageProvider


class StabilityProvider(ImageProvider):
    """Image generation via Stability AI Stable Image API."""

    API_URL = "https://api.stability.ai/v2beta/stable-image/generate/core"
    DEFAULT_OUTPUT_FORMAT = "png"

    def __init__(
        self,
        api_key: str | None = None,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
    ) -> None:
        self._api_key = api_key or os.environ.get("STABILITY_API_KEY", "")
        self._output_format = output_format

    def generate(self, job: ImageJob) -> ImageJob:
        try:
            import requests
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "The 'requests' package is required for StabilityProvider. "
                "Install it with: pip install requests"
            ) from exc

        if not self._api_key:
            raise RuntimeError(
                "STABILITY_API_KEY is not set. "
                "Export it as an environment variable or pass api_key= to StabilityProvider."
            )

        response = requests.post(
            self.API_URL,
            headers={
                "authorization": f"Bearer {self._api_key}",
                "accept": "image/*",
            },
            files={"none": ""},
            data={
                "prompt": job.prompt,
                "output_format": self._output_format,
                "width": job.width,
                "height": job.height,
            },
            timeout=120,
        )

        if response.status_code != 200:
            job.state = AssetState.REJECTED
            return job

        out_path = Path(job.output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(response.content)
        job.state = AssetState.GENERATED
        return job
