"""Pipeline stage 2 — Technical YAML → Canonical JSON.

Reads a refined technical YAML file and produces the authoritative canonical
JSON manifest (``output/manifests/<episode_id>.canonical.json``) that all
downstream stages consume.

The canonical JSON follows the :class:`~markdown_to_video_davinci.models.canonical.CanonicalEpisode`
schema.  It can also be generated directly from an existing ``EpisodePackage``
(legacy Markdown path) by calling :func:`canonical_from_episode`.
"""

from __future__ import annotations

import json
from pathlib import Path

try:
    import yaml  # optional dependency

    _HAS_YAML = True
except ModuleNotFoundError:
    _HAS_YAML = False

from ..models.canonical import (
    AssetState,
    CanonicalEpisode,
    DialogueCue,
    ResourceIntent,
    Scene,
    Shot,
    TimingHint,
)
from ..parser import EpisodePackage, slugify


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def build_canonical(
    project_dir: Path,
    technical_path: Path,
) -> Path:
    """Parse a technical YAML file and write the canonical JSON manifest.

    Parameters
    ----------
    project_dir:
        Root project directory.
    technical_path:
        Path to the ``.yaml`` technical script.

    Returns
    -------
    Path
        Path to the written canonical JSON file.
    """
    episode = _parse_technical_yaml(technical_path)
    return _write_canonical(project_dir, episode)


def canonical_from_episode(
    project_dir: Path,
    episode: EpisodePackage,
    episode_id: str,
    title: str = "",
) -> Path:
    """Convert a legacy :class:`~markdown_to_video_davinci.parser.EpisodePackage`
    to a canonical JSON manifest.

    Each scene becomes a single-shot scene using the scene's visual prompt.
    """
    canonical = _episode_package_to_canonical(episode, episode_id, title)
    return _write_canonical(project_dir, canonical)


# ---------------------------------------------------------------------------
# Internal conversion helpers
# ---------------------------------------------------------------------------


def _parse_technical_yaml(path: Path) -> CanonicalEpisode:
    if not _HAS_YAML:
        raise RuntimeError(
            "PyYAML is required to parse technical YAML files. "
            "Install it with: pip install pyyaml"
        )
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return _canonical_from_dict(raw)


def _canonical_from_dict(raw: dict) -> CanonicalEpisode:
    scenes: list[Scene] = []
    for raw_scene in raw.get("scenes", []):
        shots: list[Shot] = []
        for raw_shot in raw_scene.get("shots", []):
            timing_data = raw_shot.get("timing", {})
            timing = TimingHint(
                duration_seconds=float(timing_data.get("duration_seconds", 6.0)),
                transition_in=timing_data.get("transition_in", "cut"),
                transition_out=timing_data.get("transition_out", "cut"),
                timeline_track=timing_data.get("timeline_track", "V1"),
            )

            dialogue: list[DialogueCue] = []
            for d in raw_shot.get("dialogue", []):
                dialogue.append(
                    DialogueCue(
                        character=d["character"],
                        text=d["text"],
                        timing_offset_seconds=float(
                            d.get("timing_offset_seconds", 0.0)
                        ),
                        voice_path=d.get("voice_path"),
                        state=AssetState(d.get("state", "planned")),
                    )
                )

            resources: list[ResourceIntent] = []
            for r in raw_shot.get("resources", []):
                resources.append(
                    ResourceIntent(
                        kind=r["kind"],
                        slug=r["slug"],
                        prompt=r.get("prompt"),
                        path=r.get("path"),
                        state=AssetState(r.get("state", "planned")),
                    )
                )

            shots.append(
                Shot(
                    index=int(raw_shot["index"]),
                    code=raw_shot["code"],
                    description=raw_shot["description"],
                    visual_prompt=raw_shot["visual_prompt"],
                    timing=timing,
                    characters=raw_shot.get("characters", []),
                    dialogue=dialogue,
                    resources=resources,
                )
            )

        scenes.append(
            Scene(
                code=raw_scene["code"],
                title=raw_scene["title"],
                visual_summary=raw_scene["visual_summary"],
                visual_prompt=raw_scene["visual_prompt"],
                characters=raw_scene.get("characters", []),
                shots=shots,
            )
        )

    characters: dict[str, dict] = {}
    for slug, char_data in raw.get("characters", {}).items():
        characters[slug] = {
            "name": char_data.get("name", slug),
            "prompt": char_data.get("prompt", ""),
        }

    return CanonicalEpisode(
        episode_id=raw["episode_id"],
        title=raw.get("title", raw["episode_id"]),
        quality_prompt=raw.get("quality_prompt", ""),
        characters=characters,
        scenes=scenes,
        schema_version=raw.get("schema_version", "1.0"),
    )


def _episode_package_to_canonical(
    episode: EpisodePackage,
    episode_id: str,
    title: str,
) -> CanonicalEpisode:
    """Produce a CanonicalEpisode from the legacy parser output.

    Each scene is mapped to a single-shot scene so the downstream pipeline
    has a consistent data model even when no technical YAML exists.
    """
    characters = {
        slug: {"name": char.name, "prompt": char.prompt}
        for slug, char in episode.characters.items()
    }

    scenes: list[Scene] = []
    for scene in episode.scenes:
        shot_slug = slugify(f"{scene.code} plano-01")
        shot = Shot(
            index=1,
            code=f"{scene.code} - PLANO 01",
            description=scene.visual_summary,
            visual_prompt=scene.visual_prompt,
            timing=TimingHint(),
            characters=scene.characters,
            dialogue=[],
            resources=[
                ResourceIntent(
                    kind="image",
                    slug=shot_slug,
                    prompt=scene.visual_prompt,
                    state=AssetState.PLANNED,
                )
            ],
        )
        scenes.append(
            Scene(
                code=scene.code,
                title=scene.title,
                visual_summary=scene.visual_summary,
                visual_prompt=scene.visual_prompt,
                characters=scene.characters,
                shots=[shot],
            )
        )

    return CanonicalEpisode(
        episode_id=episode_id,
        title=title or episode_id,
        quality_prompt=episode.quality_prompt,
        characters=characters,
        scenes=scenes,
    )


def _write_canonical(project_dir: Path, episode: CanonicalEpisode) -> Path:
    manifests_dir = project_dir / "output" / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    out_path = manifests_dir / f"{episode.episode_id}.canonical.json"
    out_path.write_text(
        json.dumps(episode.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path
