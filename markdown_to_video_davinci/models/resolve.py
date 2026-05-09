from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TimelineItem:
    """A single item in the DaVinci Resolve timeline."""

    index: int
    scene_code: str
    shot_code: str
    scene_title: str
    duration_seconds: float
    timeline_track: str
    transition_in: str
    transition_out: str
    image_path: Optional[str]
    audio_paths: list[str] = field(default_factory=list)
    subtitle_path: Optional[str] = None
    marker_label: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass
class ResolvePackage:
    """Full Resolve project package for one episode."""

    episode_id: str
    schema_version: str = "1.0"
    timeline_items: list[TimelineItem] = field(default_factory=list)
    bins: list[str] = field(default_factory=list)
    relink_map: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)
