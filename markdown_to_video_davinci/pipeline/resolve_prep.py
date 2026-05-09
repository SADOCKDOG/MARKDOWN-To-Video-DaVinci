"""Pipeline stage 4 — Canonical JSON → Resolve package.

Produces:

- ``output/davinci/<episode_id>.resolve_package.json`` — rich timeline
  descriptor for DaVinci Resolve scripting or manual reference.
- ``output/davinci/<episode_id>.davinci_shotlist.csv`` — legacy CSV for
  backward compatibility (same format as the original ``builder`` output).

The asset registry (if present) is consulted to populate real file paths for
images and audio. If the registry is absent, paths are set to the expected
output locations so DaVinci can be pointed to them after assets are generated.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Optional

from ..models.assets import AssetRegistry
from ..models.canonical import CanonicalEpisode
from ..models.resolve import ResolvePackage, TimelineItem
from ..parser import slugify


def build_resolve_package(
    project_dir: Path,
    episode: CanonicalEpisode,
    registry: Optional[AssetRegistry] = None,
) -> Path:
    """Build Resolve package and legacy CSV from a canonical episode.

    Parameters
    ----------
    project_dir:
        Root project directory.
    episode:
        The loaded canonical episode.
    registry:
        Optional asset registry; when provided, real file paths are used.

    Returns
    -------
    Path
        Path to the written Resolve package JSON file.
    """
    package = _build_package(project_dir, episode, registry)
    package_path = _write_package(project_dir, package)
    _write_legacy_csv(project_dir, package)
    return package_path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_package(
    project_dir: Path,
    episode: CanonicalEpisode,
    registry: Optional[AssetRegistry],
) -> ResolvePackage:
    # Index registry jobs for fast lookup
    image_index: dict[str, str] = {}
    audio_index: dict[str, list[str]] = {}
    if registry:
        for job in registry.image_jobs:
            image_index[job.shot_code] = job.output_path
        for job in registry.voice_jobs:
            audio_index.setdefault(job.shot_code, []).append(job.output_path)

    images_dir = project_dir / "output" / "images"
    audio_dir = project_dir / "output" / "audio"

    items: list[TimelineItem] = []
    bins: set[str] = set()
    relink_map: dict[str, str] = {}
    global_index = 1

    for scene in episode.scenes:
        scene_bin = f"Episode {episode.episode_id} / {scene.code}"
        bins.add(scene_bin)
        for shot in scene.shots:
            shot_slug = slugify(shot.code)
            image_path = image_index.get(
                shot.code,
                str(images_dir / f"{shot_slug}.png"),
            )
            audio_paths = audio_index.get(
                shot.code,
                [str(audio_dir / f"{slugify(shot.code)}-cue-01.wav")]
                if shot.dialogue
                else [],
            )

            subtitle_path = _subtitle_path(project_dir, episode.episode_id, shot_slug)

            item = TimelineItem(
                index=global_index,
                scene_code=scene.code,
                shot_code=shot.code,
                scene_title=scene.title,
                duration_seconds=shot.timing.duration_seconds,
                timeline_track=shot.timing.timeline_track,
                transition_in=shot.timing.transition_in,
                transition_out=shot.timing.transition_out,
                image_path=image_path,
                audio_paths=audio_paths,
                subtitle_path=subtitle_path if Path(subtitle_path).exists() else None,
                marker_label=f"{scene.code} | {shot.code}",
                notes=shot.description,
            )
            items.append(item)
            relink_map[shot_slug] = image_path
            global_index += 1

    return ResolvePackage(
        episode_id=episode.episode_id,
        timeline_items=items,
        bins=sorted(bins),
        relink_map=relink_map,
    )


def _subtitle_path(project_dir: Path, episode_id: str, shot_slug: str) -> str:
    return str(project_dir / "output" / "subtitles" / f"{episode_id}-{shot_slug}.srt")


def _write_package(project_dir: Path, package: ResolvePackage) -> Path:
    davinci_dir = project_dir / "output" / "davinci"
    davinci_dir.mkdir(parents=True, exist_ok=True)
    out_path = davinci_dir / f"{package.episode_id}.resolve_package.json"
    out_path.write_text(
        json.dumps(package.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path


def _write_legacy_csv(project_dir: Path, package: ResolvePackage) -> Path:
    davinci_dir = project_dir / "output" / "davinci"
    csv_path = davinci_dir / f"{package.episode_id}.davinci_shotlist.csv"
    fieldnames = [
        "scene_index",
        "scene_code",
        "shot_code",
        "scene_title",
        "duration_seconds",
        "timeline_track",
        "transition_in",
        "transition_out",
        "image_path",
        "audio_paths",
        "notes",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for item in package.timeline_items:
            writer.writerow(
                {
                    "scene_index": item.index,
                    "scene_code": item.scene_code,
                    "shot_code": item.shot_code,
                    "scene_title": item.scene_title,
                    "duration_seconds": item.duration_seconds,
                    "timeline_track": item.timeline_track,
                    "transition_in": item.transition_in,
                    "transition_out": item.transition_out,
                    "image_path": item.image_path or "",
                    "audio_paths": ";".join(item.audio_paths),
                    "notes": item.notes,
                }
            )
    return csv_path
