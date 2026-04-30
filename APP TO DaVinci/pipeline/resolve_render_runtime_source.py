import argparse
import json
import subprocess
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


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return float(result.stdout.strip())


def collect_timeline_bounds(timeline) -> tuple[int, int]:
    starts: list[int] = []
    ends: list[int] = []
    for track_type in ["video", "audio"]:
        track_count = int(timeline.GetTrackCount(track_type) or 0)
        for track_index in range(1, track_count + 1):
            items = timeline.GetItemListInTrack(track_type, track_index) or []
            for item in items:
                starts.append(int(item.GetStart()))
                ends.append(int(item.GetEnd()))
    if not ends:
        fail("La timeline ensamblada no contiene items renderizables.")
    return min(starts or [0]), max(ends)


def main():
    parser = argparse.ArgumentParser(description="Render final desde Resolve usando la timeline ensamblada del runtime.")
    parser.add_argument("--execution-plan", type=Path, required=True)
    args = parser.parse_args()

    plan = load_json(args.execution_plan)
    render_settings = plan["render_settings"]
    assembly = plan["resolve_assembly"]
    path_keys = {
        "final_output",
        "delivery_dir",
        "resolve_output_dir",
        "resolve_render_settings",
        "resolve_style_guide",
    }
    paths = {k: Path(v) for k, v in plan["paths"].items() if k in path_keys}
    output_path = paths["final_output"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    resolve = load_resolve()
    pm = resolve.GetProjectManager()
    project_name = assembly["project_name"]
    timeline_name = assembly["timeline_name"]
    project = find_or_create_project(pm, project_name)

    timeline = find_timeline(project, timeline_name)
    if timeline is None:
        fail(f"No se encontró la timeline ensamblada: {timeline_name}")
    project.SetCurrentTimeline(timeline)
    mark_in, mark_out_exclusive = collect_timeline_bounds(timeline)
    mark_out = max(mark_in, mark_out_exclusive - 1)

    fmt, codec = codec_tuple(render_settings)
    preset_loaded = project.LoadRenderPreset("H.264 Master") if fmt == "mp4" and codec == "H264" else True
    if not preset_loaded:
        fail("No se pudo cargar el preset de render.")
    project.SetCurrentRenderFormatAndCodec(fmt, codec)
    settings = {
        "SelectAllFrames": True,
        "MarkIn": mark_in,
        "MarkOut": mark_out,
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
    output_duration = probe_duration(output_path)
    expected_duration = probe_duration(Path(plan["paths"]["narration_audio"]))
    if output_duration < max(30.0, expected_duration * 0.9):
        fail(
            "El render final salió truncado. "
            f"Duración esperada aprox={expected_duration:.2f}s, salida={output_duration:.2f}s"
        )
    print(f"PROJECT={project_name}|TIMELINE={timeline_name}|OUTPUT={output_path}")


if __name__ == "__main__":
    main()
