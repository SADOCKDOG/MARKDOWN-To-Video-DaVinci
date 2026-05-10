"""Pipeline — Ejecucion real de jobs de assets.

Carga el registro de assets guardado en JSON y ejecuta los jobs planificados
usando los proveedores configurados:

- Imagen  → :class:`~markdown_to_video_davinci.integrations.images.ImageProvider`
- Voz     → :class:`~markdown_to_video_davinci.integrations.tts.TTSProvider`
- Clip    → :class:`~markdown_to_video_davinci.integrations.clips.ClipRunner`

Cada funcion devuelve la ruta al registro actualizado con los estados reales
(``generated`` / ``rejected``) escritos de vuelta en el JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..models.assets import AssetRegistry


# ---------------------------------------------------------------------------
# Helpers de carga / guardado
# ---------------------------------------------------------------------------


def _load_registry(registry_path: Path) -> AssetRegistry:
    from ..models.assets import AssetRegistry as _AR

    data = json.loads(registry_path.read_text(encoding="utf-8"))
    return _AR.from_dict(data)


def _save_registry(project_dir: Path, registry: AssetRegistry) -> Path:
    manifests_dir = project_dir / "output" / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    out_path = manifests_dir / f"{registry.episode_id}.asset_registry.json"
    out_path.write_text(
        json.dumps(registry.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path


def _find_registry(project_dir: Path, explicit: Optional[str]) -> Path:
    if explicit:
        return Path(explicit).resolve()
    candidates = sorted(
        (project_dir / "output" / "manifests").glob("*.asset_registry.json")
    )
    if not candidates:
        raise FileNotFoundError(
            f"No se encontro ningun .asset_registry.json en "
            f"{project_dir}/output/manifests/. "
            "Ejecuta primero: generate-assets."
        )
    return candidates[0]


# ---------------------------------------------------------------------------
# Ejecucion de jobs de imagen
# ---------------------------------------------------------------------------


def run_image_jobs(
    project_dir: Path,
    image_provider_name: str = "stability",
    registry_path: Optional[str] = None,
    **provider_kwargs,
) -> Path:
    """Ejecuta los jobs de imagen planificados en el registro de assets.

    Parameters
    ----------
    project_dir:
        Directorio raiz del proyecto.
    image_provider_name:
        Nombre del proveedor (``stability`` o ``openvino``).
    registry_path:
        Ruta al JSON del registro. Si se omite, usa el primero encontrado.
    **provider_kwargs:
        Argumentos extra pasados al constructor del proveedor
        (p.ej. ``api_key``, ``model_dir``).

    Returns
    -------
    Path
        Ruta al registro actualizado.
    """
    registry = _load_registry(_find_registry(project_dir, registry_path))
    provider = _build_image_provider(image_provider_name, **provider_kwargs)
    registry = provider.run_registry(registry)
    return _save_registry(project_dir, registry)


def _build_image_provider(name: str, **kwargs):
    from ..integrations.images import OpenVINOProvider, StabilityProvider

    if name == "stability":
        return StabilityProvider(**{k: v for k, v in kwargs.items() if k in ("api_key", "output_format")})
    if name == "openvino":
        return OpenVINOProvider(**{k: v for k, v in kwargs.items() if k in ("model_dir", "device", "num_inference_steps", "guidance_scale")})
    raise ValueError(f"Proveedor de imagen no soportado: {name!r}. Usa 'stability' o 'openvino'.")


# ---------------------------------------------------------------------------
# Ejecucion de jobs de voz
# ---------------------------------------------------------------------------


def run_voice_jobs(
    project_dir: Path,
    tts_provider_name: str = "local",
    registry_path: Optional[str] = None,
    **provider_kwargs,
) -> Path:
    """Ejecuta los jobs de voz planificados en el registro de assets.

    Parameters
    ----------
    project_dir:
        Directorio raiz del proyecto.
    tts_provider_name:
        Nombre del proveedor (``local`` o ``elevenlabs``).
    registry_path:
        Ruta al JSON del registro. Si se omite, usa el primero encontrado.
    **provider_kwargs:
        Argumentos extra pasados al constructor del proveedor
        (p.ej. ``voice_id``, ``api_key``, ``rate``).

    Returns
    -------
    Path
        Ruta al registro actualizado.
    """
    registry = _load_registry(_find_registry(project_dir, registry_path))
    provider = _build_tts_provider(tts_provider_name, **provider_kwargs)
    registry = provider.run_registry(registry)
    return _save_registry(project_dir, registry)


def _build_tts_provider(name: str, **kwargs):
    from ..integrations.tts import ElevenLabsProvider, LocalTTSProvider

    if name == "local":
        return LocalTTSProvider(**{k: v for k, v in kwargs.items() if k in ("rate", "volume")})
    if name == "elevenlabs":
        return ElevenLabsProvider(**{k: v for k, v in kwargs.items() if k in ("voice_id", "api_key", "model_id", "stability", "similarity_boost")})
    raise ValueError(f"Proveedor TTS no soportado: {name!r}. Usa 'local' o 'elevenlabs'.")


# ---------------------------------------------------------------------------
# Ejecucion de jobs de clip (FFmpeg)
# ---------------------------------------------------------------------------


def run_clip_jobs(
    project_dir: Path,
    ffmpeg_bin: str = "ffmpeg",
    registry_path: Optional[str] = None,
    **runner_kwargs,
) -> Path:
    """Ejecuta los jobs de clip planificados en el registro de assets via FFmpeg.

    Parameters
    ----------
    project_dir:
        Directorio raiz del proyecto.
    ffmpeg_bin:
        Ruta o nombre del ejecutable ``ffmpeg``.
    registry_path:
        Ruta al JSON del registro. Si se omite, usa el primero encontrado.
    **runner_kwargs:
        Argumentos extra pasados a :class:`~markdown_to_video_davinci.integrations.clips.ffmpeg.FFmpegRunner`
        (p.ej. ``video_codec``, ``audio_codec``).

    Returns
    -------
    Path
        Ruta al registro actualizado.
    """
    from ..integrations.clips import FFmpegRunner

    registry = _load_registry(_find_registry(project_dir, registry_path))
    runner = FFmpegRunner(ffmpeg_bin=ffmpeg_bin, **{k: v for k, v in runner_kwargs.items() if k in ("video_codec", "audio_codec", "audio_bitrate", "pix_fmt", "extra_video_args")})
    registry = runner.run_registry(registry)
    return _save_registry(project_dir, registry)
