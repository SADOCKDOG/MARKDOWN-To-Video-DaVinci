import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


PROJECT_SUBDIRS = [
    "00-admin",
    "01-source",
    "02-series-outline",
    "03-shared-assets",
    "04-episodes",
    "05-resolve",
    "06-renders",
    "07-delivery",
]

EPISODE_SUBDIRS = [
    "script",
    "audio\\es",
    "audio\\en",
    "video-stock",
    "semantic-plan",
    "graphics",
    "exports",
]

LIGHTWEIGHT_COPY_RULES = [
    ("{episode}.md", "script\\{episode}.md"),
    ("audio\\es\\narration-source-es.md", "audio\\es\\narration-source-es.md"),
    ("audio\\es\\locucion-es.md", "audio\\es\\locucion-es.md"),
    ("audio\\en\\narration-source-en.md", "audio\\en\\narration-source-en.md"),
    ("audio\\en\\voiceover-en-us.md", "audio\\en\\voiceover-en-us.md"),
    ("videos\\on-screen-text-es.md", "graphics\\on-screen-text-es.md"),
    ("videos\\on-screen-text-en.md", "graphics\\on-screen-text-en.md"),
    ("videos\\edit-manifest.md", "graphics\\edit-manifest.md"),
    ("videos\\semantic-shot-plan.json", "semantic-plan\\semantic-shot-plan.json"),
    ("videos\\semantic-shot-plan.csv", "semantic-plan\\semantic-shot-plan.csv"),
    ("videos\\semantic-shot-plan.md", "semantic-plan\\semantic-shot-plan.md"),
    ("videos\\stock-search-report.json", "video-stock\\stock-search-report.json"),
    ("videos\\stock-sources-sciclip.md", "video-stock\\stock-sources-sciclip.md"),
    ("videos\\stock-sources.md", "video-stock\\stock-sources.md"),
]

PIPELINE_SCRIPT_ASSETS = [
    "semantic_video_planner.py",
    "semantic_sciclip_bridge.py",
    "resolve_import_semantic_timeline.py",
    "resolve21_diagnostics.py",
    "refresh_spanish_voice_catalog.py",
    "generate_episode_audio.py",
]

PIPELINE_TEMPLATE_ASSETS = [
    "branding_asset_manifest.json",
    "channel_brand_inference.json",
    "resolve_channel_premium_template.json",
    "episode01_premium_opening_preview.json",
    "episode_template_rollout.json",
]

VOICE_CATALOG_ASSETS = [
    "microsoft_spanish_voices.json",
    "microsoft_spanish_voices.csv",
    "microsoft_spanish_voice_roles.json",
]


def load_settings(root_dir: Path) -> dict:
    settings_path = root_dir / "APP TO DaVinci" / "config" / "pipeline-settings.json"
    return json.loads(settings_path.read_text(encoding="utf-8"))


def resolve_setting_path(root_dir: Path, setting_value: str, fallback_relative: str = "") -> Path:
    value = (setting_value or fallback_relative).strip()
    path = Path(value)
    return path if path.is_absolute() else root_dir / path


def detect_active_markdown(root_dir: Path) -> Path:
    md_dir = root_dir / "MD TO YOUTUBE"
    markdowns = sorted(p for p in md_dir.glob("*.md") if p.is_file())
    if not markdowns:
        raise SystemExit(f"No hay markdowns en {md_dir}")
    if len(markdowns) > 1:
        names = ", ".join(p.name for p in markdowns)
        raise SystemExit(
            "Se encontró más de un markdown en MD TO YOUTUBE y el flujo actual permite solo uno activo. "
            f"Detectados: {names}"
        )
    return markdowns[0]


def derive_series_title(markdown_path: Path) -> str:
    stem = markdown_path.stem.strip()
    parts = [part.strip() for part in re.split(r"\s+-\s+", stem) if part.strip()]
    if len(parts) >= 2:
        return parts[0]
    return stem


def safe_copy(source: Path, target: Path):
    if not source.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True


def safe_move(source: Path, target: Path):
    if not source.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    shutil.move(str(source), str(target))
    return True


def create_project_structure(project_dir: Path):
    for relative in PROJECT_SUBDIRS:
        (project_dir / relative).mkdir(parents=True, exist_ok=True)


def create_episode_structure(project_dir: Path, episode_name: str) -> Path:
    episode_dir = project_dir / "04-episodes" / episode_name
    for relative in EPISODE_SUBDIRS:
        (episode_dir / relative).mkdir(parents=True, exist_ok=True)
    return episode_dir


def seed_shared_assets(project_dir: Path, settings: dict, root_dir: Path):
    app_dir = root_dir / "APP TO DaVinci"
    branding_dir = resolve_setting_path(root_dir, settings.get("branding_dir", ""), "APP TO DaVinci\\assets\\BRANDING")
    shared_assets = project_dir / "03-shared-assets"
    branding_target = shared_assets / "branding"
    voice_target = shared_assets / "voice-catalog"
    pipeline_specs = shared_assets / "pipeline-specs"
    branding_target.mkdir(parents=True, exist_ok=True)
    voice_target.mkdir(parents=True, exist_ok=True)
    pipeline_specs.mkdir(parents=True, exist_ok=True)

    if branding_dir.exists():
        for item in branding_dir.iterdir():
            if item.is_file():
                safe_copy(item, branding_target / item.name)

    for name in VOICE_CATALOG_ASSETS:
        source = app_dir / "assets" / name
        if source.exists():
            safe_copy(source, voice_target / source.name)

    for name in PIPELINE_TEMPLATE_ASSETS:
        source = app_dir / "assets" / name
        if source.exists():
            safe_copy(source, pipeline_specs / source.name)

    for name in PIPELINE_SCRIPT_ASSETS:
        source = app_dir / "pipeline" / name
        if source.exists():
            safe_copy(source, pipeline_specs / source.name)


def discover_legacy_episodes(series_title: str, settings: dict, root_dir: Path) -> list[Path]:
    title_gate = settings.get("legacy_seed_series_title", "").strip()
    if title_gate and series_title != title_gate:
        return []
    legacy_source_root = settings.get("legacy_source_root", "").strip()
    if not legacy_source_root:
        return []
    legacy_root = resolve_setting_path(root_dir, legacy_source_root)
    if not legacy_root.exists():
        return []
    episodes = []
    for child in sorted(legacy_root.glob("Episodio *")):
        if child.is_dir() and (child / f"{child.name}.md").exists():
            episodes.append(child)
    return episodes


def seed_episode_from_legacy(source_episode_dir: Path, target_episode_dir: Path):
    copied = []
    for source_pattern, target_pattern in LIGHTWEIGHT_COPY_RULES:
        source = source_episode_dir / source_pattern.format(episode=source_episode_dir.name)
        target = target_episode_dir / target_pattern.format(episode=source_episode_dir.name)
        if safe_copy(source, target):
            copied.append(str(target.relative_to(target_episode_dir)))

    manifest = {
        "episode": source_episode_dir.name,
        "legacy_source": str(source_episode_dir),
        "copied_lightweight_assets": copied,
        "media_copied": False,
    }
    (target_episode_dir / "script" / "episode-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def write_project_manifest(
    project_dir: Path,
    source_markdown_name: str,
    source_markdown_origin: str,
    source_markdown_target: str,
    series_title: str,
    seeded_episodes: list[dict],
):
    manifest = {
        "series_title": series_title,
        "source_markdown_name": source_markdown_name,
        "source_markdown_origin": source_markdown_origin,
        "source_markdown_target": source_markdown_target,
        "resolve_project_name": Path(source_markdown_name).stem,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "project_structure": PROJECT_SUBDIRS,
        "episode_count_seeded": len(seeded_episodes),
        "episodes": seeded_episodes,
    }
    manifest_path = project_dir / "00-admin" / "project-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def write_project_readme(project_dir: Path, active_markdown: Path, series_title: str):
    content = "\n".join(
        [
            f"# {series_title}",
            "",
            "## Origen del proyecto",
            "",
            f"- Markdown activo: `{active_markdown.name}`",
            f"- Proyecto Resolve previsto: `{active_markdown.stem}`",
            "",
            "## Estructura",
            "",
            "- `00-admin`: manifiestos y estado operativo",
            "- `01-source`: documento maestro de entrada",
            "- `02-series-outline`: taxonomía editorial y episodización",
            "- `03-shared-assets`: branding, voces y plantillas",
            "- `04-episodes`: carpetas operativas por episodio",
            "- `05-resolve`: integración con DaVinci Resolve",
            "- `06-renders`: renders intermedios y masters",
            "- `07-delivery`: entregables finales",
            "",
            "## Política de ejecución",
            "",
            "- Un solo markdown activo por ejecución.",
            "- La app reusable vive en `APP TO DaVinci`.",
            "- Los artefactos del proyecto viven solo dentro de esta carpeta de `FINALS PROJECTS`.",
        ]
    )
    (project_dir / "00-admin" / "README.md").write_text(content + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Materializa un proyecto audiovisual desde la raíz DaVinci Projects.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--force", action="store_true", help="Permite reescribir manifiestos y volver a sembrar la estructura.")
    args = parser.parse_args()

    root_dir = args.root.resolve()
    settings = load_settings(root_dir)
    active_markdown = detect_active_markdown(root_dir)
    series_title = derive_series_title(active_markdown)
    project_dir = root_dir / "FINALS PROJECTS" / series_title

    if project_dir.exists() and not args.force:
        raise SystemExit(f"El proyecto ya existe en {project_dir}. Usa --force para resembrarlo.")

    create_project_structure(project_dir)
    markdown_origin = str(active_markdown)
    markdown_target = project_dir / "01-source" / active_markdown.name
    safe_move(active_markdown, markdown_target)
    seed_shared_assets(project_dir, settings, root_dir)

    seeded_episodes = []
    for legacy_episode_dir in discover_legacy_episodes(series_title, settings, root_dir):
        episode_dir = create_episode_structure(project_dir, legacy_episode_dir.name)
        seeded_episodes.append(seed_episode_from_legacy(legacy_episode_dir, episode_dir))

    write_project_manifest(
        project_dir,
        markdown_target.name,
        markdown_origin,
        str(markdown_target),
        series_title,
        seeded_episodes,
    )
    write_project_readme(project_dir, markdown_target, series_title)

    outline_dir = project_dir / "02-series-outline"
    outline_dir.mkdir(parents=True, exist_ok=True)
    (outline_dir / "series-source-reference.txt").write_text(
        f"{markdown_target.name}\n",
        encoding="utf-8",
    )

    resolve_dir = project_dir / "05-resolve"
    resolve_dir.mkdir(parents=True, exist_ok=True)
    (resolve_dir / "resolve-project-name.txt").write_text(markdown_target.stem + "\n", encoding="utf-8")

    print(
        f"OK|PROJECT_DIR={project_dir}|MARKDOWN={markdown_target.name}|SERIES={series_title}|EPISODES={len(seeded_episodes)}"
    )


if __name__ == "__main__":
    main()
