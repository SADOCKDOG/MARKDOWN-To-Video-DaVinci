"""OpenVINO GenAI local image generation provider.

Uses ``openvino_genai.Text2ImagePipeline`` to run a locally converted model
(exported with ``optimum-cli export openvino``) entirely on CPU or Intel GPU
without any internet access.

Requirements
------------
``pip install openvino-genai``

A pre-converted OpenVINO IR model directory must be provided (e.g. a SDXL
or SD 1.5 model converted via ``optimum-cli export openvino``).

Usage
-----
>>> from markdown_to_video_davinci.integrations.images.openvino import OpenVINOProvider
>>> provider = OpenVINOProvider(model_dir="./converted_sdxl")
>>> updated_job = provider.generate(job)
"""

from __future__ import annotations

from pathlib import Path

from ...models.assets import ImageJob
from ...models.canonical import AssetState
from .base import ImageProvider


class OpenVINOProvider(ImageProvider):
    """Local text-to-image generation via OpenVINO GenAI."""

    def __init__(
        self,
        model_dir: str | Path,
        device: str = "CPU",
        num_inference_steps: int = 20,
        guidance_scale: float = 7.5,
    ) -> None:
        self._model_dir = str(model_dir)
        self._device = device
        self._num_inference_steps = num_inference_steps
        self._guidance_scale = guidance_scale
        self._pipeline = None  # lazy-loaded

    def _get_pipeline(self):
        if self._pipeline is None:
            try:
                import openvino_genai as ov_genai  # type: ignore[import]
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "The 'openvino-genai' package is required for OpenVINOProvider. "
                    "Install it with: pip install openvino-genai"
                ) from exc
            self._pipeline = ov_genai.Text2ImagePipeline(
                self._model_dir, self._device
            )
        return self._pipeline

    def generate(self, job: ImageJob) -> ImageJob:
        try:
            import numpy as np
            from PIL import Image  # type: ignore[import]
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Pillow and numpy are required for OpenVINOProvider. "
                "Install them with: pip install pillow numpy"
            ) from exc

        pipeline = self._get_pipeline()
        result = pipeline.generate(
            job.prompt,
            width=job.width,
            height=job.height,
            num_inference_steps=self._num_inference_steps,
            guidance_scale=self._guidance_scale,
        )

        out_path = Path(job.output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.fromarray(result.data[0])
        image.save(str(out_path))
        job.state = AssetState.GENERATED
        return job
