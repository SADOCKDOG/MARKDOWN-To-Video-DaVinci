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

    @classmethod
    def from_dict(cls, data: dict) -> ImageJob:
        return cls(
            job_id=data["job_id"],
            episode_id=data["episode_id"],
            scene_code=data["scene_code"],
            shot_code=data["shot_code"],
            prompt=data["prompt"],
            output_path=data["output_path"],
            state=AssetState(data.get("state", AssetState.PLANNED)),
            provider=data.get("provider", "stability"),
            width=int(data.get("width", 1920)),
            height=int(data.get("height", 1080)),
        )


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

    @classmethod
    def from_dict(cls, data: dict) -> VoiceJob:
        return cls(
            job_id=data["job_id"],
            episode_id=data["episode_id"],
            scene_code=data["scene_code"],
            shot_code=data["shot_code"],
            character=data["character"],
            text=data["text"],
            output_path=data["output_path"],
            state=AssetState(data.get("state", AssetState.PLANNED)),
            provider=data.get("provider", "local"),
            language=data.get("language", "es"),
        )


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

    @classmethod
    def from_dict(cls, data: dict) -> ClipJob:
        return cls(
            job_id=data["job_id"],
            episode_id=data["episode_id"],
            scene_code=data["scene_code"],
            shot_code=data["shot_code"],
            image_path=data["image_path"],
            audio_path=data.get("audio_path"),
            output_path=data["output_path"],
            duration_seconds=float(data.get("duration_seconds", 6.0)),
            state=AssetState(data.get("state", AssetState.PLANNED)),
        )


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

    @classmethod
    def from_dict(cls, data: dict) -> AssetRegistry:
        return cls(
            episode_id=data["episode_id"],
            schema_version=data.get("schema_version", "1.0"),
            image_jobs=[ImageJob.from_dict(j) for j in data.get("image_jobs", [])],
            voice_jobs=[VoiceJob.from_dict(j) for j in data.get("voice_jobs", [])],
            clip_jobs=[ClipJob.from_dict(j) for j in data.get("clip_jobs", [])],
        )
