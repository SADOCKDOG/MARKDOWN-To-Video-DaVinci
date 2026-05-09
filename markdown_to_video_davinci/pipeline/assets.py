"""Pipeline stage 3 — Canonical JSON → Asset job manifests.

Reads the canonical episode manifest and generates structured job descriptors
for:

- ``output/manifests/<episode_id>.image_jobs.json`` — one image job per shot.
- ``output/manifests/<episode_id>.voice_jobs.json`` — one voice job per
  dialogue cue.
- ``output/manifests/<episode_id>.clip_jobs.json`` — one clip job per shot
  (cross-references image + voice jobs).
- ``output/manifests/<episode_id>.asset_registry.json`` — unified registry.

None of these jobs are executed here; they are consumed by the integration
providers in :mod:`markdown_to_video_davinci.integrations`.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..models.assets import AssetRegistry, ClipJob, ImageJob, VoiceJob
from ..models.canonical import AssetState, CanonicalEpisode
from ..parser import slugify


def build_asset_registry(
    project_dir: Path,
    episode: CanonicalEpisode,
    image_provider: str = "stability",
    tts_provider: str = "local",
) -> Path:
    """Build and write the asset job registry for one episode.

    Parameters
    ----------
    project_dir:
        Root project directory.
    episode:
        The loaded canonical episode.
    image_provider:
        Default image backend tag written into each image job.
    tts_provider:
        Default TTS backend tag written into each voice job.

    Returns
    -------
    Path
        Path to the written asset registry JSON file.
    """
    images_dir = project_dir / "output" / "images"
    audio_dir = project_dir / "output" / "audio"
    clips_dir = project_dir / "output" / "clips"

    registry = AssetRegistry(episode_id=episode.episode_id)

    # Build per-shot image and clip jobs, per-dialogue voice jobs
    for scene in episode.scenes:
        for shot in scene.shots:
            shot_slug = slugify(shot.code)
            job_id = f"{episode.episode_id}-{shot_slug}"

            # Image job
            image_out = str(images_dir / f"{shot_slug}.png")
            image_job = ImageJob(
                job_id=f"img-{job_id}",
                episode_id=episode.episode_id,
                scene_code=scene.code,
                shot_code=shot.code,
                prompt=_build_image_prompt(shot, episode),
                output_path=image_out,
                provider=image_provider,
            )
            registry.image_jobs.append(image_job)

            # Voice jobs (one per dialogue cue)
            audio_paths: list[str] = []
            for idx, cue in enumerate(shot.dialogue, start=1):
                cue_slug = slugify(f"{shot_slug}-cue-{idx:02d}")
                audio_out = str(audio_dir / f"{cue_slug}.wav")
                voice_job = VoiceJob(
                    job_id=f"voice-{cue_slug}",
                    episode_id=episode.episode_id,
                    scene_code=scene.code,
                    shot_code=shot.code,
                    character=cue.character,
                    text=cue.text,
                    output_path=audio_out,
                    provider=tts_provider,
                )
                registry.voice_jobs.append(voice_job)
                audio_paths.append(audio_out)

            # Clip job (base video from still + audio via FFmpeg)
            clip_out = str(clips_dir / f"{shot_slug}.mp4")
            clip_job = ClipJob(
                job_id=f"clip-{job_id}",
                episode_id=episode.episode_id,
                scene_code=scene.code,
                shot_code=shot.code,
                image_path=image_out,
                audio_path=audio_paths[0] if audio_paths else None,
                output_path=clip_out,
                duration_seconds=shot.timing.duration_seconds,
            )
            registry.clip_jobs.append(clip_job)

    return _write_registry(project_dir, registry)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_image_prompt(shot, episode: CanonicalEpisode) -> str:
    """Combine shot visual prompt with quality baseline and character prompts."""
    parts = [shot.visual_prompt, f"Episode visual baseline: {episode.quality_prompt}."]
    for char_name in shot.characters:
        char_slug = slugify(char_name)
        char_data = episode.characters.get(char_slug, {})
        char_prompt = char_data.get("prompt", "")
        if char_prompt:
            parts.append(f"{char_name} reference: {char_prompt}")
    return " ".join(p.strip() for p in parts if p.strip())


def _write_registry(project_dir: Path, registry: AssetRegistry) -> Path:
    manifests_dir = project_dir / "output" / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    out_path = manifests_dir / f"{registry.episode_id}.asset_registry.json"
    out_path.write_text(
        json.dumps(registry.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path
