from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Optional

from .canonical import AssetState


@dataclass
class ImageJob:
    """Job descriptor for generating a single still image."""

    job_id: str
    episode_id: str
    scene_code: str
    shot_code: str
    prompt: str
    output_path: str
    state: AssetState = AssetState.PLANNED
    provider: str = "stability"
    width: int = 1920
    height: int = 1080

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass
class VoiceJob:
    """Job descriptor for synthesizing a single dialogue line."""

    job_id: str
    episode_id: str
    scene_code: str
    shot_code: str
    character: str
    text: str
    output_path: str
    state: AssetState = AssetState.PLANNED
    provider: str = "local"
    language: str = "es"

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass
class ClipJob:
    """Job descriptor for assembling a base video clip from a still + audio."""

    job_id: str
    episode_id: str
    scene_code: str
    shot_code: str
    image_path: str
    audio_path: Optional[str]
    output_path: str
    duration_seconds: float = 6.0
    state: AssetState = AssetState.PLANNED

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass
class AssetRegistry:
    """Complete asset job registry for one episode."""

    episode_id: str
    schema_version: str = "1.0"
    image_jobs: list[ImageJob] = field(default_factory=list)
    voice_jobs: list[VoiceJob] = field(default_factory=list)
    clip_jobs: list[ClipJob] = field(default_factory=list)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)
