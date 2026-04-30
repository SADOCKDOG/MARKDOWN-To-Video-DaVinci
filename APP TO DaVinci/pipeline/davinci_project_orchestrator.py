import argparse
import json
import math
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

DEFAULT_SOURCE_EPISODES = [
    "Episodio 01 - Vida espejo y quiralidad",
    "Episodio 02 - IA espejo",
    "Episodio 03 - Humano aumentado y exocórtex",
    "Episodio 04 - Átomos, emergencia y consciencia",
    "Episodio 05 - Antimateria y universos espejo",
    "Episodio 06 - Agujeros negros, agujeros blancos y rebote cosmológico",
    "Episodio 07 - Información, lenguaje y código del universo",
    "Episodio 08 - Tecno-sapiens",
    "Episodio 09 - Geopolítica del cómputo",
    "Episodio 10 - Espejo cognitivo y astronomía interior",
]

SPEAKER_MARKER = re.compile(r"^\\--\s*(.+?)\s*--\s*$")


def load_settings(root_dir: Path) -> dict:
    settings_path = root_dir / "APP TO DaVinci" / "config" / "pipeline-settings.json"
    return json.loads(settings_path.read_text(encoding="utf-8"))


def resolve_setting_path(root_dir: Path, setting_value: str, fallback_relative: str = "") -> Path:
    value = (setting_value or fallback_relative).strip()
    path = Path(value)
    return path if path.is_absolute() else root_dir / path


def write_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict | list):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def derive_markdown_theme(markdown_path: Path, series_title: str) -> str:
    stem = markdown_path.stem.strip()
    parts = [part.strip() for part in re.split(r"\s+-\s+", stem) if part.strip()]
    if len(parts) >= 2:
        return normalize_inline_text(" - ".join(parts[1:]))
    return series_title


def normalize_inline_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_block_text(text: str) -> str:
    normalized_lines = [line.rstrip() for line in (text or "").splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(normalized_lines).strip())


def summarize_prompt(text: str, index: int) -> str:
    base = normalize_inline_text((text or "").replace("\n", " "))
    if not base:
        return f"Bloque {index:02}"
    parts = re.split(r"[?!\.]", base, maxsplit=1)
    candidate = parts[0].strip(" ¿?¡!.,:;")
    if not candidate:
        candidate = base.strip(" ¿?¡!.,:;")
    words = candidate.split()
    if len(words) > 8:
        candidate = " ".join(words[:8])
    if not candidate:
        return f"Bloque {index:02}"
    return candidate[0].upper() + candidate[1:]


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


def parse_dialogue_turns(markdown_path: Path) -> list[dict]:
    turns: list[dict] = []
    current_speaker = ""
    current_lines: list[str] = []

    def flush():
        nonlocal current_speaker, current_lines
        content = normalize_block_text("\n".join(current_lines))
        if current_speaker and content:
            turns.append({"speaker": current_speaker, "content": content})
        current_lines = []

    for raw_line in markdown_path.read_text(encoding="utf-8").splitlines():
        match = SPEAKER_MARKER.match(raw_line.strip())
        if match:
            flush()
            current_speaker = normalize_inline_text(match.group(1))
            continue
        current_lines.append(raw_line)
    flush()
    return turns


def build_source_exchanges(markdown_path: Path) -> list[dict]:
    turns = parse_dialogue_turns(markdown_path)
    if not turns:
        body = normalize_block_text(markdown_path.read_text(encoding="utf-8"))
        return [{"prompt": markdown_path.stem, "response": body}]

    exchanges: list[dict] = []
    current_prompt = ""
    current_response: list[str] = []

    def flush():
        nonlocal current_prompt, current_response
        if current_prompt or current_response:
            exchanges.append(
                {
                    "prompt": normalize_block_text(current_prompt),
                    "response": normalize_block_text("\n\n".join(part for part in current_response if part.strip())),
                }
            )
        current_prompt = ""
        current_response = []

    for turn in turns:
        speaker = normalize_inline_text(turn["speaker"]).lower()
        content = normalize_block_text(turn["content"])
        if not content:
            continue
        if "david" in speaker:
            if current_prompt or current_response:
                flush()
            current_prompt = content
        elif "gemini" in speaker:
            if current_prompt:
                current_response.append(content)
        elif current_prompt:
            current_response.append(content)

    flush()
    return [exchange for exchange in exchanges if exchange["prompt"] or exchange["response"]]


def derive_episode_titles(exchange_count: int, markdown_path: Path, series_title: str) -> list[str]:
    if exchange_count <= 1:
        theme = derive_markdown_theme(markdown_path, series_title)
        return [f"Episodio 01 - {theme}"]
    desired = max(1, min(len(DEFAULT_SOURCE_EPISODES), math.ceil(exchange_count / 9)))
    return DEFAULT_SOURCE_EPISODES[:desired]


def chunk_source_exchanges(exchanges: list[dict], episode_titles: list[str]) -> list[tuple[str, list[dict]]]:
    if not exchanges:
        return []
    chunk_size = math.ceil(len(exchanges) / len(episode_titles))
    chunks: list[tuple[str, list[dict]]] = []
    for index, episode_title in enumerate(episode_titles):
        start = index * chunk_size
        end = min(len(exchanges), (index + 1) * chunk_size)
        if start >= len(exchanges):
            break
        chunk = exchanges[start:end]
        if chunk:
            chunks.append((episode_title, chunk))
    return chunks


def build_episode_script(episode_name: str, source_markdown_name: str, exchanges: list[dict]) -> tuple[str, list[str]]:
    headings: list[str] = []
    lines = [
        f"# {episode_name}",
        "",
        f"> Fuente editorial: `{source_markdown_name}`",
        "",
    ]
    for index, exchange in enumerate(exchanges, start=1):
        heading = summarize_prompt(exchange["prompt"], index)
        headings.append(heading)
        lines.extend([f"## {heading}", ""])
        if exchange["prompt"]:
            lines.extend([f"Pregunta detonante: {exchange['prompt']}", ""])
        body = exchange["response"] or exchange["prompt"]
        if body:
            lines.extend([body, ""])
    return "\n".join(lines).strip() + "\n", headings


def build_edit_manifest(episode_name: str, headings: list[str]) -> str:
    lines = [
        f"# Edit manifest - {episode_name}",
        "",
        "## Bloques narrativos",
        "",
    ]
    for index, heading in enumerate(headings, start=1):
        lines.append(f"{index}. {heading}")
    return "\n".join(lines).strip() + "\n"


def seed_episode_from_source(
    markdown_path: Path,
    target_episode_dir: Path,
    episode_name: str,
    exchanges: list[dict],
) -> dict:
    script_content, headings = build_episode_script(episode_name, markdown_path.name, exchanges)
    outline_md = "\n".join(f"- {heading}" for heading in headings).strip() + ("\n" if headings else "")
    edit_manifest = build_edit_manifest(episode_name, headings)

    write_text(target_episode_dir / f"{episode_name}.md", script_content)
    write_text(target_episode_dir / "script" / f"{episode_name}.md", script_content)
    write_text(target_episode_dir / "videos" / "on-screen-text-es.md", outline_md)
    write_text(target_episode_dir / "graphics" / "on-screen-text-es.md", outline_md)
    write_text(target_episode_dir / "videos" / "edit-manifest.md", edit_manifest)
    write_text(target_episode_dir / "graphics" / "edit-manifest.md", edit_manifest)

    manifest = {
        "episode": episode_name,
        "legacy_source": str(target_episode_dir),
        "source_type": "generated_from_source_markdown",
        "source_markdown": str(markdown_path),
        "script_path": str(target_episode_dir / "script" / f"{episode_name}.md"),
        "headings_path": str(target_episode_dir / "graphics" / "on-screen-text-es.md"),
        "block_count": len(headings),
        "media_copied": False,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(target_episode_dir / "script" / "episode-manifest.json", manifest)
    return manifest


def seed_episodes_from_source(markdown_path: Path, project_dir: Path, series_title: str) -> list[dict]:
    exchanges = build_source_exchanges(markdown_path)
    if not exchanges:
        return []

    seeded_episodes: list[dict] = []
    episode_titles = derive_episode_titles(len(exchanges), markdown_path, series_title)
    for episode_name, chunk in chunk_source_exchanges(exchanges, episode_titles):
        episode_dir = create_episode_structure(project_dir, episode_name)
        seeded_episodes.append(seed_episode_from_source(markdown_path, episode_dir, episode_name, chunk))
    return seeded_episodes


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


def write_series_outline(project_dir: Path, source_markdown_name: str, seeded_episodes: list[dict]):
    outline_dir = project_dir / "02-series-outline"
    outline_dir.mkdir(parents=True, exist_ok=True)
    write_text(outline_dir / "series-source-reference.txt", f"{source_markdown_name}\n")

    markdown_lines = [
        "# Outline de serie",
        "",
        f"- Fuente editorial: `{source_markdown_name}`",
        f"- Episodios materializados: `{len(seeded_episodes)}`",
        "",
        "| Episodio | Tipo de fuente | Bloques |",
        "|---|---|---:|",
    ]
    for episode in seeded_episodes:
        markdown_lines.append(
            f"| {episode['episode']} | {episode.get('source_type', 'legacy_seed')} | {episode.get('block_count', 0)} |"
        )
    write_text(outline_dir / "series-outline.md", "\n".join(markdown_lines) + "\n")
    write_json(
        outline_dir / "series-outline.json",
        {
            "source_markdown_name": source_markdown_name,
            "episode_count": len(seeded_episodes),
            "episodes": seeded_episodes,
        },
    )


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
            "- El siguiente paso recomendado se obtiene desde `00-admin\\prompt-catalog.md`.",
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
    legacy_episodes = discover_legacy_episodes(series_title, settings, root_dir)
    for legacy_episode_dir in legacy_episodes:
        episode_dir = create_episode_structure(project_dir, legacy_episode_dir.name)
        seeded_episodes.append(seed_episode_from_legacy(legacy_episode_dir, episode_dir))
    if not seeded_episodes:
        seeded_episodes = seed_episodes_from_source(markdown_target, project_dir, series_title)

    write_project_manifest(
        project_dir,
        markdown_target.name,
        markdown_origin,
        str(markdown_target),
        series_title,
        seeded_episodes,
    )
    write_project_readme(project_dir, markdown_target, series_title)
    write_series_outline(project_dir, markdown_target.name, seeded_episodes)

    resolve_dir = project_dir / "05-resolve"
    resolve_dir.mkdir(parents=True, exist_ok=True)
    (resolve_dir / "resolve-project-name.txt").write_text(markdown_target.stem + "\n", encoding="utf-8")

    print(
        f"OK|PROJECT_DIR={project_dir}|MARKDOWN={markdown_target.name}|SERIES={series_title}|EPISODES={len(seeded_episodes)}"
    )


if __name__ == "__main__":
    main()
