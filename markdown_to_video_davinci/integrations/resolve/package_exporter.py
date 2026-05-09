"""Rich JSON package exporter for DaVinci Resolve.

Emits a ``<episode_id>.resolve_package.json`` that contains the complete
timeline specification including audio tracks, subtitle paths, bin structure,
media relink map, and per-shot marker labels.

This file can be consumed by a future DaVinci Resolve Python scripting
integration or used as a reference document for manual assembly.
"""

from __future__ import annotations

import json
from pathlib import Path

from ...models.resolve import ResolvePackage


def export_package(package: ResolvePackage, output_path: Path) -> Path:
    """Write the full Resolve package JSON for *package*.

    Parameters
    ----------
    package:
        The loaded resolve package.
    output_path:
        Destination JSON path (parent directory must exist or will be created).

    Returns
    -------
    Path
        The written JSON file path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(package.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path
