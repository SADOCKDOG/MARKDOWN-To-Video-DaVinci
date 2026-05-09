"""CSV exporter for DaVinci Resolve (legacy format).

Emits a ``davinci_shotlist.csv`` compatible with the original ``builder``
output so existing Resolve workflows continue to work unchanged.
"""

from __future__ import annotations

import csv
from pathlib import Path

from ...models.resolve import ResolvePackage


def export_csv(package: ResolvePackage, output_path: Path) -> Path:
    """Write a legacy-compatible CSV shotlist for *package*.

    Parameters
    ----------
    package:
        The loaded resolve package.
    output_path:
        Destination CSV path (parent directory must exist or will be created).

    Returns
    -------
    Path
        The written CSV file path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "scene_index",
        "scene_code",
        "shot_code",
        "scene_title",
        "duration_seconds",
        "timeline_track",
        "image_path",
        "prompt_path",
        "notes",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as fh:
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
                    "image_path": item.image_path or "",
                    "prompt_path": "",
                    "notes": item.notes,
                }
            )
    return output_path
