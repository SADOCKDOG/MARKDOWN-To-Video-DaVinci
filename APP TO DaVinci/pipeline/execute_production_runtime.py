import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
import os
from pathlib import Path


DEFAULT_EPISODE = "Episodio 01 - Vida espejo y quiralidad"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fail(message: str):
    raise SystemExit(message)


def load_settings(root_dir: Path) -> dict:
    return load_json(root_dir / "APP TO DaVinci" / "config" / "pipeline-settings.json")


def slugify_episode(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in name.lower())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")


def resolve_headings_markdown(episode_dir: Path) -> Path:
    candidates = [
        episode_dir / "videos" / "on-screen-text-es.md",
        episode_dir / "graphics" / "on-screen-text-es.md",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def collect_stock_clips(episode_dir: Path) -> tuple[str, list[str]]:
    numbered_pattern = re.compile(r"^\d{2,3}\.mp4$", re.IGNORECASE)
    candidates = [
        ("sciclip-stock", episode_dir / "video-stock" / "sciclip-stock", "*.mp4"),
        ("legacy-sciclip-stock", episode_dir / "videos" / "sciclip-stock", "*.mp4"),
        ("project-video-stock", episode_dir / "video-stock", "[0-9][0-9].mp4"),
        ("legacy-videos", episode_dir / "videos", "[0-9][0-9].mp4"),
    ]
    searched: list[str] = []
    for mode, base_dir, pattern in candidates:
        searched.append(str(base_dir))
        if not base_dir.exists():
            continue
        if pattern == "*.mp4":
            clips = sorted(str(path) for path in base_dir.glob(pattern))
        else:
            clips = sorted(str(path) for path in base_dir.glob("*.mp4") if numbered_pattern.match(path.name))
        if clips:
            return mode, clips

    fail("No se encontraron clips válidos en: " + ", ".join(searched))


def find_episode_manifest_entry(project_manifest: dict, episode_name: str) -> dict:
    for item in project_manifest.get("episodes", []):
        if item.get("episode") == episode_name:
            return item
    fail(f"No se encontró el episodio '{episode_name}' en project-manifest.json")


def build_execution_plan(root_dir: Path, project: str, episode_name: str) -> tuple[dict, Path]:
    settings = load_settings(root_dir)
    project_dir = root_dir / "FINALS PROJECTS" / project
    admin_dir = project_dir / "00-admin"
    runtime = load_json(admin_dir / "production-runtime.json")
    brief = load_json(admin_dir / "production-brief.json")
    project_manifest = load_json(admin_dir / "project-manifest.json")
    voice_plan = load_json(Path(runtime["voice_plan_reference"]))
    render_settings = load_json(Path(runtime["resolve_render_reference"]))
    style_guide = load_json(Path(runtime["visual_style_reference"]))

    episode_entry = find_episode_manifest_entry(project_manifest, episode_name)
    episode_dir = Path(episode_entry["legacy_source"])
    stock_mode, stock_clips = collect_stock_clips(episode_dir)
    render_dir = project_dir / "06-renders" / episode_name
    delivery_dir = project_dir / "07-delivery" / episode_name
    resolve_dir = project_dir / "05-resolve"
    semantic_plan = episode_dir / "semantic-plan" / "semantic-shot-plan.json"
    final_output = delivery_dir / "youtube-es-runtime-final.mp4"
    execution_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    timeline_name = f"{episode_name} - semantic-runtime - {execution_stamp}"
    assembly_project_name = f"{render_settings['project_name']} - Runtime Assembly"

    plan = {
        "project": project,
        "episode": episode_name,
        "project_dir": str(project_dir),
        "legacy_episode_dir": str(episode_dir),
        "runtime_references": runtime,
        "render_settings": render_settings,
        "style_guide_reference": str(Path(runtime["visual_style_reference"])),
        "voice_plan_reference": str(Path(runtime["voice_plan_reference"])),
        "voice_plan": voice_plan,
        "brief_snapshot": brief,
        "global_runtime_policy": settings.get("global_runtime_policy", {}),
        "resolve_brief_controls": {
            "text_system": {
                "headings_markdown": str(resolve_headings_markdown(episode_dir)),
                "text_style": brief["visual_direction"]["text_style"],
                "cinematic_style": brief["visual_direction"]["cinematic_style"],
                "transition_style": brief["visual_direction"]["transition_style"],
                "fx_density": brief["visual_direction"]["fx_density"],
                "futurism_level": brief["visual_direction"]["futurism_level"],
            },
            "finish": {
                "color_look": brief["davinci_finish"]["color_look"],
                "contrast_profile": brief["davinci_finish"]["contrast_profile"],
                "texture_profile": brief["davinci_finish"]["texture_profile"],
                "resolution": brief["davinci_finish"]["resolution"],
                "delivery_codec": brief["davinci_finish"]["delivery_codec"],
                "delivery_target": brief["davinci_finish"]["delivery_target"],
            },
            "music_and_sound": brief["music_and_sound"],
            "voice_strategy": brief["language_and_voices"]["voice_strategy"],
        },
        "paths": {
            "headings_markdown": str(resolve_headings_markdown(episode_dir)),
            "semantic_plan": str(semantic_plan),
            "stock_report": str(episode_dir / "video-stock" / "stock-search-report.json"),
            "block_audio_dir": str(episode_dir / "audio" / "es" / "blocks"),
            "narration_audio": str(episode_dir / "audio" / "es" / "youtube-es-full.mp3"),
            "music_audio": str(episode_dir / "audio" / "es" / "music-bg.mp3"),
            "stock_mode": stock_mode,
            "stock_clips": stock_clips,
            "render_dir": str(render_dir),
            "delivery_dir": str(delivery_dir),
            "final_output": str(final_output),
            "resolve_output_dir": str(delivery_dir),
            "resolve_render_settings": str(resolve_dir / "resolve-render-settings.json"),
            "resolve_style_guide": str(resolve_dir / "resolve-style-guide.json"),
            "assembly_report": str(resolve_dir / f"runtime-assembly-{slugify_episode(episode_name)}.json"),
        },
        "resolve_assembly": {
            "project_name": assembly_project_name,
            "timeline_name": timeline_name,
            "fps": render_settings["resolution"]["fps"],
            "resolution_width": render_settings["resolution"]["width"],
            "resolution_height": render_settings["resolution"]["height"],
        },
        "execution_policy": {
            "default_scope": "episode01_only",
            "approved_trigger": "Brief revisado y aprobado, procede con este runtime",
            "visual_assembly_mode": settings.get("global_runtime_policy", {}).get("visual_assembly_mode", "resolve-first"),
            "stock_selection_stage": settings.get("global_runtime_policy", {}).get("stock_selection_stage", "resolve-assembly"),
            "stock_profile_mode": settings.get("global_runtime_policy", {}).get("stock_profile_mode", "dynamic-per-episode"),
            "stock_download_format": settings.get("global_runtime_policy", {}).get("stock_download_format", "1920x1080-16:9"),
            "ffmpeg_role": settings.get("global_runtime_policy", {}).get("ffmpeg_role", "audio-only-support"),
            "generated_utc": datetime.now(timezone.utc).isoformat(),
        },
    }
    plan_path = resolve_dir / f"runtime-execution-plan-{slugify_episode(episode_name)}.json"
    return plan, plan_path


def validate_plan(plan: dict):
    required = [
        plan["paths"]["headings_markdown"],
        plan["paths"]["semantic_plan"],
        plan["paths"]["block_audio_dir"],
        plan["paths"]["narration_audio"],
        plan["paths"]["music_audio"],
    ]
    missing = [path for path in required if not Path(path).exists()]
    clip_paths = plan["paths"].get("stock_clips", [])
    if not clip_paths:
        missing.append("stock_clips")
    else:
        missing.extend(path for path in clip_paths if not Path(path).exists())
    if missing:
        fail("Faltan assets requeridos para ejecutar el runtime: " + ", ".join(missing))


def run_python(script: Path, plan_path: Path):
    subprocess.run([sys.executable, str(script), "--execution-plan", str(plan_path)], check=True)


def run_script(script: Path, args: list[str], env_overrides: dict[str, str] | None = None):
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    subprocess.run([sys.executable, str(script), *args], check=True, env=env)


def main():
    parser = argparse.ArgumentParser(description="Prepara o ejecuta el runtime aprobado del proyecto.")
    parser.add_argument("--root", type=Path, required=True, help="Raíz DaVinci Projects")
    parser.add_argument("--project", required=True, help="Nombre de la carpeta del proyecto en FINALS PROJECTS")
    parser.add_argument("--episode", default=DEFAULT_EPISODE, help="Episodio objetivo")
    parser.add_argument("--prepare-only", action="store_true", help="Solo prepara y valida el runtime execution plan.")
    parser.add_argument("--regenerate-audio", action="store_true", help="Regenera los audios del episodio antes de montar.")
    parser.add_argument("--refresh-stock", action="store_true", help="Refresca stock online y replanificación semántica del episodio.")
    parser.add_argument("--refresh-voice-catalog", action="store_true", help="Actualiza el catálogo multilingual y reaplica el brief.")
    parser.add_argument("--full-regenerate", action="store_true", help="Ejecuta catálogo de voces, audio y stock antes del render.")
    args = parser.parse_args()

    root_dir = args.root.resolve()
    app_dir = root_dir / "APP TO DaVinci" / "pipeline"
    should_refresh_voices = args.refresh_voice_catalog or args.full_regenerate
    should_regenerate_audio = args.regenerate_audio or args.full_regenerate
    should_refresh_stock = args.refresh_stock or args.full_regenerate

    if should_refresh_voices:
        run_script(app_dir / "refresh_spanish_voice_catalog.py", ["--root", str(root_dir), "--project", args.project])
        run_script(app_dir / "apply_production_brief.py", ["--root", str(root_dir), "--project", args.project])

    if should_regenerate_audio:
        run_script(app_dir / "generate_episode_audio.py", ["--root", str(root_dir), "--project", args.project, "--episode", args.episode])

    if should_refresh_stock:
        project_manifest = load_json(root_dir / "FINALS PROJECTS" / args.project / "00-admin" / "project-manifest.json")
        episode_entry = find_episode_manifest_entry(project_manifest, args.episode)
        legacy_root = str(Path(episode_entry["legacy_source"]).parent)
        run_script(
            app_dir / "semantic_sciclip_bridge.py",
            ["--episode", args.episode],
            env_overrides={"VIDA_ESPEJO_ROOT": legacy_root},
        )

    plan, plan_path = build_execution_plan(root_dir, args.project, args.episode)
    music_audio = Path(plan["paths"]["music_audio"])
    if not music_audio.exists():
        run_script(app_dir / "generate_episode_music_bed.py", ["--root", str(root_dir), "--project", args.project, "--episode", args.episode])

    plan, plan_path = build_execution_plan(root_dir, args.project, args.episode)
    validate_plan(plan)
    write_json(plan_path, plan)

    if args.prepare_only:
        print(f"OK|PLAN={plan_path}|MODE=prepare-only")
        return

    run_python(app_dir / "resolve_assemble_semantic_timeline.py", plan_path)
    run_python(app_dir / "resolve_render_runtime_source.py", plan_path)
    print(f"OK|PLAN={plan_path}|FINAL={plan['paths']['final_output']}")


if __name__ == "__main__":
    main()
