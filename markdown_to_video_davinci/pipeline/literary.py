"""Pipeline stage 1 — Literary markdown → Technical YAML draft.

Reads a literary Markdown file in the existing format (parsed by the core
``parser`` module) and emits a technical YAML scaffold that a human can then
refine with shot-level detail, dialogue cues, and timing overrides.

The technical YAML is written to ``input/technical/<episode_id>.yaml`` and
can be read back by :mod:`.breakdown`.
"""

from __future__ import annotations

from pathlib import Path

from ..parser import EpisodePackage, parse_episode, slugify

_YAML_INDENT = "  "


def _yaml_str(value: str) -> str:
    """Return a safe single-line YAML string (double-quoted, escaped)."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _block_str(value: str, indent: int = 4) -> str:
    """Return a YAML literal block scalar for multiline / long strings."""
    prefix = " " * indent
    lines = value.splitlines()
    body = ("\n" + prefix).join(lines)
    return "|\n" + prefix + body


def compile_literary(
    project_dir: Path,
    markdown_path: Path,
    episode_id: str | None = None,
) -> Path:
    """Parse a literary Markdown file and write a technical YAML draft.

    Parameters
    ----------
    project_dir:
        Root project directory.
    markdown_path:
        Path to the literary ``.md`` source file.
    episode_id:
        Identifier used for the output filename. Defaults to the Markdown
        file stem.

    Returns
    -------
    Path
        The path of the generated technical YAML file.
    """
    markdown_text = markdown_path.read_text(encoding="utf-8")
    episode: EpisodePackage = parse_episode(markdown_text)

    ep_id = episode_id or slugify(markdown_path.stem)
    title = ep_id.replace("-", " ").title()

    technical_dir = project_dir / "input" / "technical"
    technical_dir.mkdir(parents=True, exist_ok=True)
    out_path = technical_dir / f"{ep_id}.yaml"

    lines: list[str] = []

    def w(text: str = "") -> None:
        lines.append(text)

    w("schema_version: '1.0'")
    w(f"episode_id: {_yaml_str(ep_id)}")
    w(f"title: {_yaml_str(title)}")
    w(f"quality_prompt: {_yaml_str(episode.quality_prompt)}")
    w()

    # Characters
    w("characters:")
    for slug, character in episode.characters.items():
        w(f"  {slug}:")
        w(f"    name: {_yaml_str(character.name)}")
        w(f"    prompt: {_yaml_str(character.prompt)}")
    if not episode.characters:
        w("  # No se encontraron personajes en el Markdown")
    w()

    # Scenes
    w("scenes:")
    for scene in episode.scenes:
        scene_slug = slugify(f"{scene.code} {scene.title}")
        w(f"  - code: {_yaml_str(scene.code)}")
        w(f"    title: {_yaml_str(scene.title)}")
        w(f"    visual_summary: {_yaml_str(scene.visual_summary)}")
        w(f"    visual_prompt: {_yaml_str(scene.visual_prompt)}")

        # Characters list
        w("    characters:")
        for char in scene.characters:
            w(f"      - {_yaml_str(char)}")
        if not scene.characters:
            w("      []")

        # Shots — one default shot per scene as a scaffold
        w("    shots:")
        w(f"      - index: 1")
        w(f"        code: {_yaml_str(scene.code + ' - PLANO 01')}")
        w(f"        description: {_yaml_str(scene.visual_summary)}")
        w(f"        visual_prompt: {_yaml_str(scene.visual_prompt)}")
        w("        timing:")
        w("          duration_seconds: 6.0")
        w("          transition_in: cut")
        w("          transition_out: cut")
        w("          timeline_track: V1")

        # Characters in shot
        w("        characters:")
        for char in scene.characters:
            w(f"          - {_yaml_str(char)}")
        if not scene.characters:
            w("          []")

        # Dialogue — empty scaffold
        w("        dialogue: []")
        w("        # Example dialogue entry:")
        w("        #   - character: PERSONAJE")
        w("        #     text: Texto del dialogo")
        w("        #     timing_offset_seconds: 0.0")

        # Resources
        w("        resources:")
        w(f"          - kind: image")
        w(f"            slug: {_yaml_str(scene_slug + '-plano-01')}")
        w(f"            prompt: {_yaml_str(scene.visual_prompt)}")
        w(f"            state: planned")
        w()

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
