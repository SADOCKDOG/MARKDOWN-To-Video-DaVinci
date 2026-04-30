import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

from semantic_video_planner import ClipCandidate, rank_segments


def fail(message: str):
    raise SystemExit(message)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def candidate_module_paths():
    paths = []
    paths.append(Path(sys.executable).parent)
    for env_key in ["RESOLVE_SCRIPT_API", "RESOLVE_SCRIPT_LIB", "PYTHONPATH"]:
        actual = os.environ.get(env_key)
        if not actual:
            continue
        for part in str(actual).split(os.pathsep):
            if part:
                paths.append(Path(part))
    paths.extend(Path(part) for part in sys.path if part)
    if platform.system() == "Windows":
        paths.extend(
            [
                Path(r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"),
                Path(r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Developer\Scripting\Modules"),
                Path(r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Fusion\Modules"),
            ]
        )
    return paths


def load_resolve():
    checked = []
    for path in candidate_module_paths():
        if not path.exists():
            continue
        checked.append(str(path))
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.append(path_str)
    try:
        import DaVinciResolveScript as dvr_script  # type: ignore
    except Exception as exc:  # pragma: no cover
        fail(
            "No se pudo importar DaVinciResolveScript. "
            f"Detalle: {exc}. Rutas comprobadas: {checked}"
        )
    resolve = dvr_script.scriptapp("Resolve")
    if resolve is None:
        fail("No se pudo conectar con DaVinci Resolve.")
    return resolve


def normalize_path(value: str) -> str:
    return str(Path(value).resolve()).lower()


def frames_from_seconds(seconds: float, fps: float) -> int:
    return int(round(seconds * fps))


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


def open_or_create_project(project_manager, project_name: str):
    project = project_manager.LoadProject(project_name)
    if project is not None:
        return project
    project = project_manager.CreateProject(project_name)
    if project is None:
        fail(f"No se pudo crear ni cargar el proyecto '{project_name}'.")
    return project


def find_timeline(project, timeline_name: str):
    for index in range(1, project.GetTimelineCount() + 1):
        timeline = project.GetTimelineByIndex(index)
        if timeline and timeline.GetName() == timeline_name:
            return timeline
    return None


def ensure_media_subfolders(media_pool, folder_names: list[str]):
    root_folder = media_pool.GetRootFolder()
    existing = {folder.GetName(): folder for folder in root_folder.GetSubFolderList()}
    for name in folder_names:
        if name in existing:
            continue
        media_pool.AddSubFolder(root_folder, name)


def import_media_items(media_pool, media_paths: list[str]):
    imported = media_pool.ImportMedia(media_paths)
    if not imported:
        fail("Resolve no importó los media items del ensamblador.")
    mapping = {}
    for item in imported:
        file_path = item.GetClipProperty("File Path")
        if file_path:
            mapping[normalize_path(file_path)] = item
    return mapping


def load_stock_candidates(stock_report_path: Path, fallback_paths: list[str]) -> list[ClipCandidate]:
    if stock_report_path.exists():
        report = load_json(stock_report_path)
        selected = report.get("selected_candidates", [])
        candidates = []
        for item in selected:
            file_path = item.get("file_path")
            if not file_path:
                continue
            candidates.append(
                ClipCandidate(
                    file_name=item.get("file_name", Path(file_path).name),
                    file_path=file_path,
                    category=item.get("category", "abstract"),
                    title=item.get("title", Path(file_path).stem),
                    page_url=item.get("page_url", ""),
                    mp4_url=item.get("download_url", ""),
                    duration=float(item.get("duration") or probe_duration(Path(file_path))),
                )
            )
        if candidates:
            return candidates

    fallback = []
    for value in fallback_paths:
        path = Path(value)
        if not path.exists():
            continue
        fallback.append(
            ClipCandidate(
                file_name=path.name,
                file_path=str(path),
                category="abstract",
                title=path.stem,
                page_url="",
                mp4_url="",
                duration=probe_duration(path),
            )
        )
    return fallback


def set_project_settings(project, render_settings: dict):
    resolution = render_settings["resolution"]
    fps = render_settings["resolution"]["fps"]
    desired = {
        "timelineFrameRate": str(fps),
        "timelinePlaybackFrameRate": str(fps),
        "timelineResolutionWidth": str(resolution["width"]),
        "timelineResolutionHeight": str(resolution["height"]),
        "timelineStartTimecode": "00:00:00:00",
    }
    for key, value in desired.items():
        try:
            project.SetSetting(key, value)
        except Exception:
            continue


def configure_timeline_base(timeline):
    try:
        timeline.SetStartTimecode("00:00:00:00")
    except Exception:
        pass
    try:
        timeline.SetStartFrame(0)
    except Exception:
        pass


def ensure_timeline_tracks(timeline, render_settings: dict):
    architecture = render_settings.get("timeline_architecture", {})
    desired_video = max(1, len(architecture.get("video_tracks", [])))
    desired_audio = max(2, len(architecture.get("audio_tracks", [])))

    while int(timeline.GetTrackCount("video") or 0) < desired_video:
        if not timeline.AddTrack("video"):
            fail("No se pudieron crear las pistas de video requeridas en Resolve.")

    while int(timeline.GetTrackCount("audio") or 0) < desired_audio:
        created = False
        try:
            created = bool(timeline.AddTrack("audio", "stereo"))
        except TypeError:
            created = bool(timeline.AddTrack("audio"))
        if not created:
            fail("No se pudieron crear las pistas de audio requeridas en Resolve.")


def append_items_in_batches(media_pool, items: list[dict], batch_size: int = 40):
    for index in range(0, len(items), batch_size):
        batch = items[index : index + batch_size]
        if not batch:
            continue
        result = media_pool.AppendToTimeline(batch)
        if not result:
            fail(f"Resolve no pudo añadir el batch {index // batch_size + 1} a la timeline.")


def build_video_append_items(segments: list[dict], media_items: dict, fps: float) -> list[dict]:
    items = []
    for segment in segments:
        media_item = media_items.get(normalize_path(segment["clip_path"]))
        if media_item is None:
            continue
        start_frame = frames_from_seconds(segment["recommended_in"], fps)
        end_frame = max(start_frame + 1, frames_from_seconds(segment["recommended_out"], fps))
        record_frame = frames_from_seconds(segment["start"], fps)
        items.append(
            {
                "mediaPoolItem": media_item,
                "startFrame": start_frame,
                "endFrame": end_frame,
                "recordFrame": record_frame,
                "trackIndex": 1,
                "mediaType": 1,
            }
        )
    return items


def build_audio_append_item(media_items: dict, audio_path: Path, fps: float, track_index: int) -> dict:
    media_item = media_items.get(normalize_path(str(audio_path)))
    if media_item is None:
        fail(f"Resolve no importó el audio requerido: {audio_path}")
    duration_frames = max(1, frames_from_seconds(probe_duration(audio_path), fps))
    return {
        "mediaPoolItem": media_item,
        "startFrame": 0,
        "endFrame": duration_frames,
        "recordFrame": 0,
        "trackIndex": track_index,
        "mediaType": 2,
    }


def add_segment_markers(timeline, segments: list[dict], fps: float):
    for segment in segments:
        frame = frames_from_seconds(segment["start"], fps)
        duration = max(1, frames_from_seconds(segment["duration"], fps))
        color = "Blue" if segment["type"] == "heading" else "Cyan"
        note = segment["text"][:900]
        custom_data = json.dumps(
            {
                "segment_id": segment["segment_id"],
                "type": segment["type"],
                "block_index": segment["block_index"],
                "clip_file": segment["clip_file"],
                "clip_path": segment["clip_path"],
                "recommended_in": segment["recommended_in"],
                "recommended_out": segment["recommended_out"],
            },
            ensure_ascii=False,
        )
        try:
            timeline.AddMarker(frame, color, segment["segment_id"], note, duration, custom_data)
        except Exception:
            continue


def main():
    parser = argparse.ArgumentParser(description="Ensambla una timeline editable en Resolve desde semantic-shot-plan.json.")
    parser.add_argument("--execution-plan", type=Path, required=True)
    args = parser.parse_args()

    plan = load_json(args.execution_plan)
    render_settings = plan["render_settings"]
    assembly = plan["resolve_assembly"]
    brief_controls = plan["resolve_brief_controls"]
    semantic_plan = load_json(Path(plan["paths"]["semantic_plan"]))
    source_segments = semantic_plan["segments"]
    fps = float(assembly["fps"])

    stock_candidates = load_stock_candidates(Path(plan["paths"]["stock_report"]), plan["paths"]["stock_clips"])
    if not stock_candidates:
        fail("No hay pool de stock descargado para ensamblar en Resolve.")

    resolve = load_resolve()
    project_manager = resolve.GetProjectManager()
    project = open_or_create_project(project_manager, assembly["project_name"])
    set_project_settings(project, render_settings)

    media_pool = project.GetMediaPool()
    ensure_media_subfolders(media_pool, ["stock-video", "audio-main", "music", "plans"])

    media_paths = sorted(
        {
            *[candidate.file_path for candidate in stock_candidates],
            plan["paths"]["narration_audio"],
            plan["paths"]["music_audio"],
        }
    )
    media_items = import_media_items(media_pool, media_paths)
    assembled_segments = rank_segments(source_segments, stock_candidates, plan["episode"])

    timeline_name = assembly["timeline_name"]
    if find_timeline(project, timeline_name) is not None:
        fail(f"Ya existe una timeline con ese nombre: {timeline_name}")

    timeline = media_pool.CreateEmptyTimeline(timeline_name)
    if timeline is None:
        fail("No se pudo crear la timeline editable en Resolve.")
    project.SetCurrentTimeline(timeline)
    configure_timeline_base(timeline)
    ensure_timeline_tracks(timeline, render_settings)

    video_items = build_video_append_items(assembled_segments, media_items, fps)
    if not video_items:
        fail("No se pudieron construir clips de vídeo para la timeline.")
    append_items_in_batches(media_pool, video_items)

    narration_item = build_audio_append_item(media_items, Path(plan["paths"]["narration_audio"]), fps, 1)
    music_item = build_audio_append_item(media_items, Path(plan["paths"]["music_audio"]), fps, 3)
    append_items_in_batches(media_pool, [narration_item, music_item], batch_size=2)

    add_segment_markers(timeline, assembled_segments, fps)

    report = {
        "project_name": assembly["project_name"],
        "timeline_name": timeline_name,
        "segment_count": len(assembled_segments),
        "video_item_count": len(video_items),
        "stock_pool_count": len(stock_candidates),
        "audio_tracks": {
            "narration_audio": plan["paths"]["narration_audio"],
            "music_audio": plan["paths"]["music_audio"],
        },
        "brief_controls": brief_controls,
        "semantic_plan": plan["paths"]["semantic_plan"],
        "stock_report": plan["paths"]["stock_report"],
        "assembled_segments_preview": assembled_segments[:12],
        "assembled_utc": plan["execution_policy"]["generated_utc"],
    }
    write_json(Path(plan["paths"]["assembly_report"]), report)
    print(
        f"PROJECT={assembly['project_name']}|TIMELINE={timeline_name}|SEGMENTS={len(assembled_segments)}|STOCK_POOL={len(stock_candidates)}|TEXT_STYLE={brief_controls['text_system']['text_style']}"
    )


if __name__ == "__main__":
    main()
