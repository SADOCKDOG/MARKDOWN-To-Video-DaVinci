from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AssetState(str, Enum):
    """Lifecycle state of any generated asset."""

    PLANNED = "planned"
    GENERATED = "generated"
    SELECTED = "selected"
    REJECTED = "rejected"
    APPROVED = "approved"


@dataclass
class TimingHint:
    """Per-shot timing and Resolve placement defaults."""

    duration_seconds: float = 6.0
    transition_in: str = "cut"
    transition_out: str = "cut"
    timeline_track: str = "V1"


@dataclass
class DialogueCue:
    """A single line of dialogue attached to a shot."""

    character: str
    text: str
    timing_offset_seconds: float = 0.0
    voice_path: Optional[str] = None
    state: AssetState = AssetState.PLANNED


@dataclass
class ResourceIntent:
    """An intended asset (image, audio clip, base video clip) for a shot."""

    kind: str  # "image" | "audio" | "clip"
    slug: str
    prompt: Optional[str] = None
    path: Optional[str] = None
    state: AssetState = AssetState.PLANNED


@dataclass
class Shot:
    """A single camera shot within a scene."""

    index: int
    code: str
    description: str
    visual_prompt: str
    timing: TimingHint = field(default_factory=TimingHint)
    characters: list[str] = field(default_factory=list)
    dialogue: list[DialogueCue] = field(default_factory=list)
    resources: list[ResourceIntent] = field(default_factory=list)


@dataclass
class Scene:
    """A scene composed of one or more shots."""

    code: str
    title: str
    visual_summary: str
    visual_prompt: str
    characters: list[str] = field(default_factory=list)
    shots: list[Shot] = field(default_factory=list)


@dataclass
class CanonicalEpisode:
    """The canonical, versioned, normalized representation of one episode."""

    episode_id: str
    title: str
    quality_prompt: str
    characters: dict[str, dict]  # slug → {name, prompt}
    scenes: list[Scene] = field(default_factory=list)
    schema_version: str = "1.0"

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> CanonicalEpisode:
        scenes = [_scene_from_dict(s) for s in data.get("scenes", [])]
        return cls(
            episode_id=data["episode_id"],
            title=data["title"],
            quality_prompt=data["quality_prompt"],
            characters=data.get("characters", {}),
            scenes=scenes,
            schema_version=data.get("schema_version", "1.0"),
        )


# --- helpers ------------------------------------------------------------------


def _timing_from_dict(d: dict) -> TimingHint:
    return TimingHint(
        duration_seconds=d.get("duration_seconds", 6.0),
        transition_in=d.get("transition_in", "cut"),
        transition_out=d.get("transition_out", "cut"),
        timeline_track=d.get("timeline_track", "V1"),
    )


def _dialogue_from_dict(d: dict) -> DialogueCue:
    return DialogueCue(
        character=d["character"],
        text=d["text"],
        timing_offset_seconds=d.get("timing_offset_seconds", 0.0),
        voice_path=d.get("voice_path"),
        state=AssetState(d.get("state", AssetState.PLANNED)),
    )


def _resource_from_dict(d: dict) -> ResourceIntent:
    return ResourceIntent(
        kind=d["kind"],
        slug=d["slug"],
        prompt=d.get("prompt"),
        path=d.get("path"),
        state=AssetState(d.get("state", AssetState.PLANNED)),
    )


def _shot_from_dict(d: dict) -> Shot:
    return Shot(
        index=d["index"],
        code=d["code"],
        description=d["description"],
        visual_prompt=d["visual_prompt"],
        timing=_timing_from_dict(d.get("timing", {})),
        characters=d.get("characters", []),
        dialogue=[_dialogue_from_dict(x) for x in d.get("dialogue", [])],
        resources=[_resource_from_dict(x) for x in d.get("resources", [])],
    )


def _scene_from_dict(d: dict) -> Scene:
    return Scene(
        code=d["code"],
        title=d["title"],
        visual_summary=d["visual_summary"],
        visual_prompt=d["visual_prompt"],
        characters=d.get("characters", []),
        shots=[_shot_from_dict(s) for s in d.get("shots", [])],
    )
