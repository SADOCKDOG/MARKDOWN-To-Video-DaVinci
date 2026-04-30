import argparse
import json
import sys
import time
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(message: str):
    raise SystemExit(message)


def load_resolve():
    module_paths = [
        Path(r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"),
        Path(r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Developer\Scripting\Modules"),
        Path(r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Fusion\Modules"),
    ]
    for path in module_paths:
        if path.exists() and str(path) not in sys.path:
            sys.path.append(str(path))
    import DaVinciResolveScript as dvr_script  # type: ignore
    resolve = dvr_script.scriptapp("Resolve")
    if resolve is None:
        fail("No se pudo conectar con Resolve.")
    return resolve


def find_or_create_project(pm, name: str):
    project = pm.LoadProject(name)
    if project is not None:
        return project
    project = pm.CreateProject(name)
    if project is None:
        fail(f"No se pudo crear/cargar el proyecto {name}")
    return project


def find_timeline(project, name: str):
    for index in range(1, project.GetTimelineCount() + 1):
        timeline = project.GetTimelineByIndex(index)
        if timeline and timeline.GetName() == name:
            return timeline
    return None


def codec_tuple(render_settings: dict) -> tuple[str, str]:
    delivery = render_settings["delivery"]
    container = delivery["container"]
    codec = delivery["video_codec"]
    if container == "mp4" and codec == "H.264":
        return "mp4", "H264"
    if container == "mp4" and codec == "H.265":
        return "mp4", "H265"
    return "mov", "ProRes"


def main():
    parser = argparse.ArgumentParser(description="Render final desde Resolve usando el master fuente del runtime.")
    parser.add_argument("--execution-plan", type=Path, required=True)
    args = parser.parse_args()

    plan = load_json(args.execution_plan)
    episode_name = plan["episode"]
    render_settings = plan["render_settings"]
    path_keys = {
        "source_output",
        "final_output",
        "delivery_dir",
        "resolve_output_dir",
        "resolve_render_settings",
        "resolve_style_guide",
    }
    paths = {k: Path(v) for k, v in plan["paths"].items() if k in path_keys}
    source_clip = paths["source_output"]
    output_path = paths["final_output"]
    output_path.parent.mkdir(parents=True, exist_ok=True)

    resolve = load_resolve()
    pm = resolve.GetProjectManager()
    project_name = f"{render_settings['project_name']} - Runtime Final - {episode_name}"
    timeline_name = f"{episode_name} - runtime-final-render"
    project = find_or_create_project(pm, project_name)
    media_pool = project.GetMediaPool()

    imported = media_pool.ImportMedia([str(source_clip)])
    if not imported:
        fail("No se pudo importar el clip fuente a Resolve.")
    item = imported[0]

    timeline = find_timeline(project, timeline_name)
    if timeline is None:
        timeline = media_pool.CreateTimelineFromClips(timeline_name, [item])
        if timeline is None:
            fail("No se pudo crear la timeline desde el clip fuente.")
    project.SetCurrentTimeline(timeline)

    fmt, codec = codec_tuple(render_settings)
    preset_loaded = project.LoadRenderPreset("H.264 Master") if fmt == "mp4" and codec == "H264" else True
    if not preset_loaded:
        fail("No se pudo cargar el preset de render.")
    project.SetCurrentRenderFormatAndCodec(fmt, codec)
    settings = {
        "SelectAllFrames": True,
        "TargetDir": str(output_path.parent),
        "CustomName": output_path.stem,
    }
    if not project.SetRenderSettings(settings):
        fail("Resolve rechazó la configuración de render.")
    project.DeleteAllRenderJobs()
    job = project.AddRenderJob()
    if not job:
        fail("No se pudo crear el job de render.")
    if not project.StartRendering():
        fail("No se pudo iniciar el render.")
    while project.IsRenderingInProgress():
        time.sleep(5)
    if not output_path.exists():
        fail(f"No apareció el render final esperado: {output_path}")
    print(f"PROJECT={project_name}|TIMELINE={timeline_name}|OUTPUT={output_path}")


if __name__ == "__main__":
    main()
