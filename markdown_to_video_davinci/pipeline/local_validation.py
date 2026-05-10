
from __future__ import annotations

import contextlib
import importlib.util
import json
import shutil
import wave
from collections import Counter
from pathlib import Path

from ..builder import copy_project_template
from ..models.assets import AssetRegistry
from .assets import build_asset_registry
from .breakdown import build_canonical
from .literary import compile_literary
from .resolve_prep import build_resolve_package
from .review import build_review_manifest
from .run_assets import run_clip_jobs, run_image_jobs, run_voice_jobs


def validate_local_pipeline(
    project_dir: Path,
    repository_dir: Path,
    model_dir: Path,
    markdown_path: Path | None = None,
    technical_path: Path | None = None,
    ffmpeg_bin: str = "ffmpeg",
    image_width: int = 256,
    image_height: int = 256,
    episode_id: str | None = None,
) -> dict[str, object]:
    project_dir = project_dir.resolve()
    model_dir = model_dir.resolve()
    preflight = _run_preflight(project_dir, model_dir, ffmpeg_bin)

    copy_project_template(project_dir, repository_dir)

    resolved_markdown = markdown_path.resolve() if markdown_path else _resolve_markdown(project_dir)
    compiled_technical = compile_literary(project_dir, resolved_markdown, episode_id=episode_id)

    resolved_technical = (
        technical_path.resolve()
        if technical_path
        else _resolve_default_technical(project_dir, compiled_technical)
    )

    canonical_path = build_canonical(project_dir, resolved_technical)
    canonical = _load_json(canonical_path)
    canonical_episode = _load_canonical_episode(canonical_path)

    registry_path = build_asset_registry(
        project_dir,
        canonical_episode,
        image_provider="openvino",
        tts_provider="local",
    )
    _resize_registry_images(registry_path, image_width, image_height)

    resolve_path = build_resolve_package(project_dir, canonical_episode)
    review_path = build_review_manifest(project_dir, canonical_episode)

    registry_path = run_image_jobs(
        project_dir,
        image_provider_name="openvino",
        registry_path=str(registry_path),
        model_dir=str(model_dir),
    )
    registry_path = run_voice_jobs(
        project_dir,
        tts_provider_name="local",
        registry_path=str(registry_path),
    )
    registry_path = run_clip_jobs(
        project_dir,
        ffmpeg_bin=ffmpeg_bin,
        registry_path=str(registry_path),
    )

    registry_after_first_pass = _load_registry(registry_path)
    first_pass_counts = _registry_counts(registry_after_first_pass)

    registry_path = run_voice_jobs(
        project_dir,
        tts_provider_name="local",
        registry_path=str(registry_path),
    )
    registry_path = run_clip_jobs(
        project_dir,
        ffmpeg_bin=ffmpeg_bin,
        registry_path=str(registry_path),
    )

    final_registry = _load_registry(registry_path)
    final_counts = _registry_counts(final_registry)

    return {
        "project_dir": str(project_dir),
        "preflight": preflight,
        "source_markdown": str(resolved_markdown),
        "compiled_technical": str(compiled_technical),
        "technical_yaml": str(resolved_technical),
        "canonical_json": str(canonical_path),
        "asset_registry": str(registry_path),
        "resolve_package": str(resolve_path),
        "review_manifest": str(review_path),
        "image_resolution": {"width": image_width, "height": image_height},
        "canonical_counts": {
            "scene_count": len(canonical.get("scenes", [])),
            "character_count": len(canonical.get("characters", {})),
        },
        "first_pass_counts": first_pass_counts,
        "final_counts": final_counts,
        "outputs": _output_summary(project_dir),
    }


def _run_preflight(project_dir: Path, model_dir: Path, ffmpeg_bin: str) -> dict[str, object]:
    checks = {
        "project_dir_writable": _ensure_writable(project_dir),
        "ffmpeg": _check_ffmpeg(ffmpeg_bin),
        "model_dir": model_dir.exists() and model_dir.is_dir(),
        "dependencies": {
            "pyyaml": _has_module("yaml"),
            "requests": _has_module("requests"),
            "pyttsx3": _has_module("pyttsx3"),
            "openvino_genai": _has_module("openvino_genai"),
            "numpy": _has_module("numpy"),
            "PIL": _has_module("PIL"),
        },
    }

    missing = [name for name, ok in checks["dependencies"].items() if not ok]
    if not checks["ffmpeg"]:
        raise RuntimeError(
            f"FFmpeg no esta disponible con '{ffmpeg_bin}'. Instala FFmpeg o pasa --ffmpeg-bin."
        )
    if not checks["model_dir"]:
        raise RuntimeError(
            f"No existe un directorio de modelo OpenVINO valido en: {model_dir}"
        )
    if missing:
        raise RuntimeError(
            "Faltan dependencias locales para la validacion OpenVINO/local: "
            + ", ".join(missing)
        )
    return checks


def _ensure_writable(project_dir: Path) -> bool:
    project_dir.mkdir(parents=True, exist_ok=True)
    probe = project_dir / ".write_probe"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()
    return True


def _check_ffmpeg(ffmpeg_bin: str) -> bool:
    return Path(ffmpeg_bin).exists() or shutil.which(ffmpeg_bin) is not None


def _has_module(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _resolve_markdown(project_dir: Path) -> Path:
    for subdir in ("literary", "markdown"):
        candidates = sorted((project_dir / "input" / subdir).glob("*.md"))
        if candidates:
            return candidates[0]
    raise FileNotFoundError(
        f"No se encontro ningun Markdown en {project_dir}\\input\\literary ni input\\markdown."
    )


def _resolve_default_technical(project_dir: Path, compiled_technical: Path) -> Path:
    stable_fixture = project_dir / "input" / "technical" / "technical_episode_template.yaml"
    if stable_fixture.exists():
        return stable_fixture
    return compiled_technical


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_canonical_episode(canonical_path: Path):
    from ..models.canonical import CanonicalEpisode

    return CanonicalEpisode.from_dict(_load_json(canonical_path))


def _load_registry(registry_path: Path) -> AssetRegistry:
    return AssetRegistry.from_dict(_load_json(registry_path))


def _resize_registry_images(registry_path: Path, width: int, height: int) -> None:
    payload = _load_json(registry_path)
    for job in payload.get("image_jobs", []):
        job["width"] = width
        job["height"] = height
    registry_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _registry_counts(registry: AssetRegistry) -> dict[str, dict[str, int]]:
    return {
        "image_jobs": dict(Counter(job.state.value for job in registry.image_jobs)),
        "voice_jobs": dict(Counter(job.state.value for job in registry.voice_jobs)),
        "clip_jobs": dict(Counter(job.state.value for job in registry.clip_jobs)),
    }


def _output_summary(project_dir: Path) -> dict[str, object]:
    images = sorted((project_dir / "output" / "images").glob("*.png"))
    audio = sorted((project_dir / "output" / "audio").glob("*.wav"))
    clips = sorted((project_dir / "output" / "clips").glob("*.mp4"))
    return {
        "images": _summarize_files(images),
        "audio": _summarize_audio(audio),
        "clips": _summarize_files(clips),
    }


def _summarize_files(files: list[Path]) -> dict[str, object]:
    summary: dict[str, object] = {"count": len(files)}
    if files:
        summary["first_file"] = str(files[0])
        summary["first_size"] = files[0].stat().st_size
    return summary


def _summarize_audio(files: list[Path]) -> dict[str, object]:
    summary = _summarize_files(files)
    if files:
        with contextlib.closing(wave.open(str(files[0]), "rb")) as handle:
            summary["first_duration_seconds"] = round(
                handle.getnframes() / float(handle.getframerate()),
                2,
            )
    return summary
