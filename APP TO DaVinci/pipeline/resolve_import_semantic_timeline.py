import json
import os
import platform
import sys
from pathlib import Path


def fail(message: str):
    raise SystemExit(message)


def candidate_module_paths():
    paths = []
    env_paths = [
        os.environ.get("RESOLVE_SCRIPT_API"),
        os.environ.get("RESOLVE_SCRIPT_LIB"),
        os.environ.get("PYTHONPATH"),
    ]
    for value in env_paths:
        if not value:
            continue
        for part in str(value).split(os.pathsep):
            if part:
                paths.append(Path(part))

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
            "Ejecuta este script desde el entorno de scripting de DaVinci Resolve o con la API correctamente instalada. "
            f"Detalle: {exc}. "
            f"Rutas comprobadas: {checked}"
        )
    resolve = dvr_script.scriptapp("Resolve")
    if resolve is None:
        fail("No se pudo conectar con DaVinci Resolve.")
    return resolve


def frames_from_seconds(seconds: float, fps: float) -> int:
    return int(round(seconds * fps))


def import_media_items(media_pool, clip_paths):
    imported = media_pool.ImportMedia(clip_paths)
    if not imported:
        fail("Resolve no importó los clips del plan semántico.")
    mapping = {}
    for item in imported:
        file_path = item.GetClipProperty("File Path")
        mapping[file_path] = item
    return mapping


def open_or_create_project(project_manager, project_name: str):
    project = project_manager.LoadProject(project_name)
    if project is not None:
        return project
    project = project_manager.CreateProject(project_name)
    if project is None:
        fail(f"No se pudo crear ni cargar el proyecto '{project_name}'.")
    return project


def ensure_media_subfolders(media_pool, folder_names):
    root_folder = media_pool.GetRootFolder()
    existing = {folder.GetName(): folder for folder in root_folder.GetSubFolderList()}
    for name in folder_names:
        if name in existing:
            continue
        media_pool.AddSubFolder(root_folder, name)


def main():
    if len(sys.argv) < 2:
        fail("Uso: python resolve_import_semantic_timeline.py <ruta-plan-json> [fps] [project_name]")

    plan_path = Path(sys.argv[1])
    fps = float(sys.argv[2]) if len(sys.argv) > 2 else 24.0
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    episode_name = plan["episode"]
    segments = plan["segments"]
    project_name = sys.argv[3] if len(sys.argv) > 3 else f"VidaEspejo Pilot - {episode_name}"

    resolve = load_resolve()
    project_manager = resolve.GetProjectManager()
    project = open_or_create_project(project_manager, project_name)

    media_pool = project.GetMediaPool()
    ensure_media_subfolders(media_pool, ["stock-video", "audio-es", "plans"])
    clip_paths = sorted({segment["clip_path"] for segment in segments})
    media_items = import_media_items(media_pool, clip_paths)

    timeline_name = f"{episode_name} - semantic-auto"
    timeline = media_pool.CreateEmptyTimeline(timeline_name)
    if timeline is None:
        fail("No se pudo crear la timeline en DaVinci Resolve.")
    project.SetCurrentTimeline(timeline)

    append_items = []
    for segment in segments:
        media_item = media_items.get(segment["clip_path"])
        if media_item is None:
            continue
        append_items.append(
            {
                "mediaPoolItem": media_item,
                "startFrame": frames_from_seconds(segment["recommended_in"], fps),
                "endFrame": frames_from_seconds(segment["recommended_out"], fps),
                "recordFrame": frames_from_seconds(segment["start"], fps),
                "trackIndex": 1,
            }
        )

    result = media_pool.AppendToTimeline(append_items)
    if not result:
        fail("Resolve no pudo añadir los clips a la timeline.")

    print(f"PROJECT={project_name}|TIMELINE={timeline_name}")


if __name__ == "__main__":
    main()
