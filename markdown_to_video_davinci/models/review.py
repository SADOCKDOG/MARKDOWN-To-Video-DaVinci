from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ReviewStatus(str, Enum):
    """Approval state for a shot or the overall episode."""

    PENDING = "pending"
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"
    REJECTED = "rejected"


@dataclass
class ShotReview:
    """Human-review record for a single shot."""

    shot_code: str
    scene_code: str
    status: ReviewStatus = ReviewStatus.PENDING
    continuity_ok: Optional[bool] = None
    lipsync_ok: Optional[bool] = None
    subtitle_ok: Optional[bool] = None
    loudness_ok: Optional[bool] = None
    missing_assets: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass
class RenderIntent:
    """Target render format and platform export settings."""

    format: str = "mp4"
    resolution: str = "1920x1080"
    framerate: float = 24.0
    codec: str = "h264"
    platform: str = "youtube"
    loudness_lufs: float = -14.0

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass
class ReviewManifest:
    """Complete human-review manifest for one episode."""

    episode_id: str
    schema_version: str = "1.0"
    overall_status: ReviewStatus = ReviewStatus.PENDING
    render_intent: RenderIntent = field(default_factory=RenderIntent)
    shots: list[ShotReview] = field(default_factory=list)

    def is_ready_to_render(self) -> bool:
        """Returns True only when every shot is approved and none are missing assets."""
        if not self.shots:
            return False
        return all(
            s.status == ReviewStatus.APPROVED and not s.missing_assets
            for s in self.shots
        )

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)
