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


def slugify_episode(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in name.lower())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")


def collect_stock_clips(legacy_dir: Path) -> tuple[str, list[str]]:
    sciclip_dir = legacy_dir / "videos" / "sciclip-stock"
    if sciclip_dir.exists():
        clips = sorted(str(path) for path in sciclip_dir.glob("*.mp4"))
        if clips:
            return "sciclip-stock", clips

    videos_dir = legacy_dir / "videos"
    numbered = []
    pattern = re.compile(r"^\d{2,3}\.mp4$", re.IGNORECASE)
    for path in videos_dir.glob("*.mp4"):
        if pattern.match(path.name):
            numbered.append(str(path))
    numbered.sort()
    if numbered:
        return "legacy-videos", numbered

    fail(f"No se encontraron clips válidos en {sciclip_dir} ni en {videos_dir}")


def find_episode_manifest_entry(project_manifest: dict, episode_name: str) -> dict:
    for item in project_manifest.get("episodes", []):
        if item.get("episode") == episode_name:
            return item
    fail(f"No se encontró el episodio '{episode_name}' en project-manifest.json")


def build_execution_plan(root_dir: Path, project: str, episode_name: str) -> tuple[dict, Path]:
    project_dir = root_dir / "FINALS PROJECTS" / project
    admin_dir = project_dir / "00-admin"
    runtime = load_json(admin_dir / "production-runtime.json")
    brief = load_json(admin_dir / "production-brief.json")
    project_manifest = load_json(admin_dir / "project-manifest.json")
    voice_plan = load_json(Path(runtime["voice_plan_reference"]))
    render_settings = load_json(Path(runtime["resolve_render_reference"]))
    style_guide = load_json(Path(runtime["visual_style_reference"]))

    episode_entry = find_episode_manifest_entry(project_manifest, episode_name)
    legacy_dir = Path(episode_entry["legacy_source"])
    stock_mode, stock_clips = collect_stock_clips(legacy_dir)
    render_dir = project_dir / "06-renders" / episode_name
    delivery_dir = project_dir / "07-delivery" / episode_name
    resolve_dir = project_dir / "05-resolve"

    source_output = render_dir / "youtube-es-runtime-source.mp4"
    final_output = delivery_dir / "youtube-es-runtime-final.mp4"

    plan = {
        "project": project,
        "episode": episode_name,
        "project_dir": str(project_dir),
        "legacy_episode_dir": str(legacy_dir),
        "runtime_references": runtime,
        "render_settings": render_settings,
        "style_guide_reference": str(Path(runtime["visual_style_reference"])),
        "voice_plan_reference": str(Path(runtime["voice_plan_reference"])),
        "voice_plan": voice_plan,
        "brief_snapshot": brief,
        "paths": {
            "headings_markdown": str(legacy_dir / "videos" / "on-screen-text-es.md"),
            "block_audio_dir": str(legacy_dir / "audio" / "es" / "blocks"),
            "narration_audio": str(legacy_dir / "audio" / "es" / "youtube-es-full.mp3"),
            "music_audio": str(legacy_dir / "audio" / "es" / "music-bg.mp3"),
            "stock_mode": stock_mode,
            "stock_clips": stock_clips,
            "render_dir": str(render_dir),
            "delivery_dir": str(delivery_dir),
            "source_output": str(source_output),
            "final_output": str(final_output),
            "ass_output": str(render_dir / "headings-runtime.ass"),
            "resolve_output_dir": str(delivery_dir),
            "resolve_render_settings": str(resolve_dir / "resolve-render-settings.json"),
            "resolve_style_guide": str(resolve_dir / "resolve-style-guide.json"),
        },
        "execution_policy": {
            "default_scope": "episode01_only",
            "approved_trigger": "Brief revisado y aprobado, procede con este runtime",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
        },
    }
    plan_path = resolve_dir / f"runtime-execution-plan-{slugify_episode(episode_name)}.json"
    return plan, plan_path


def validate_plan(plan: dict):
    required = [
        plan["paths"]["headings_markdown"],
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
    validate_plan(plan)
    write_json(plan_path, plan)

    if args.prepare_only:
        print(f"OK|PLAN={plan_path}|MODE=prepare-only")
        return

    run_python(app_dir / "render_runtime_source_clip.py", plan_path)
    run_python(app_dir / "resolve_render_runtime_source.py", plan_path)
    print(f"OK|PLAN={plan_path}|FINAL={plan['paths']['final_output']}")


if __name__ == "__main__":
    main()
