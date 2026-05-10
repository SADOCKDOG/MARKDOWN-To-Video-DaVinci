"""Pipeline stage 5 — Review manifest generation and gate.

Creates or updates a human-review manifest in
``output/review/<episode_id>.review.json``.  The manifest lists every shot
with a ``pending`` status and a checklist of QC flags.  A human editor fills
this in (or a future automation step updates it) before calling
:func:`assert_ready_to_render`.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..models.canonical import CanonicalEpisode
from ..models.review import RenderIntent, ReviewManifest, ReviewStatus, ShotReview


def build_review_manifest(
    project_dir: Path,
    episode: CanonicalEpisode,
    render_intent: RenderIntent | None = None,
    existing_manifest: ReviewManifest | None = None,
) -> Path:
    """Create or refresh the review manifest for an episode.

    If ``existing_manifest`` is provided, shot entries that already have a
    non-``pending`` status are preserved (so human edits survive a re-run).

    Parameters
    ----------
    project_dir:
        Root project directory.
    episode:
        The loaded canonical episode.
    render_intent:
        Render format / platform intent. Defaults to YouTube 1080p24.
    existing_manifest:
        Previously saved review manifest (if any).

    Returns
    -------
    Path
        Path to the written review manifest JSON file.
    """
    intent = render_intent or RenderIntent()
    existing_shots: dict[str, ShotReview] = {}
    if existing_manifest:
        existing_shots = {s.shot_code: s for s in existing_manifest.shots}

    shot_reviews: list[ShotReview] = []
    for scene in episode.scenes:
        for shot in scene.shots:
            if shot.code in existing_shots:
                shot_reviews.append(existing_shots[shot.code])
            else:
                shot_reviews.append(
                    ShotReview(
                        shot_code=shot.code,
                        scene_code=scene.code,
                        status=ReviewStatus.PENDING,
                        missing_assets=_detect_missing_assets(project_dir, shot),
                    )
                )

    manifest = ReviewManifest(
        episode_id=episode.episode_id,
        render_intent=intent,
        shots=shot_reviews,
    )
    manifest.overall_status = _compute_overall_status(manifest)
    return _write_manifest(project_dir, manifest)


def assert_ready_to_render(manifest_path: Path) -> None:
    """Raise :exc:`RuntimeError` if the review manifest is not fully approved.

    Call this before kicking off the final render to enforce the human review
    gate.
    """
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = ReviewManifest(
        episode_id=data["episode_id"],
        schema_version=data.get("schema_version", "1.0"),
        overall_status=ReviewStatus(data.get("overall_status", "pending")),
        render_intent=RenderIntent(**data.get("render_intent", {})),
        shots=[
            ShotReview(
                shot_code=s["shot_code"],
                scene_code=s["scene_code"],
                status=ReviewStatus(s.get("status", "pending")),
                continuity_ok=s.get("continuity_ok"),
                lipsync_ok=s.get("lipsync_ok"),
                subtitle_ok=s.get("subtitle_ok"),
                loudness_ok=s.get("loudness_ok"),
                missing_assets=s.get("missing_assets", []),
                notes=s.get("notes", ""),
            )
            for s in data.get("shots", [])
        ],
    )
    if not manifest.is_ready_to_render():
        pending = [s.shot_code for s in manifest.shots if s.status != ReviewStatus.APPROVED]
        raise RuntimeError(
            f"Episode {manifest.episode_id} is not ready to render. "
            f"Shots not yet approved: {pending}"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _detect_missing_assets(project_dir: Path, shot) -> list[str]:
    from ..parser import slugify

    missing: list[str] = []
    shot_slug = slugify(shot.code)
    image_path = project_dir / "output" / "images" / f"{shot_slug}.png"
    if not image_path.exists():
        missing.append(str(image_path))
    for idx, cue in enumerate(shot.dialogue, start=1):
        cue_slug = slugify(f"{shot_slug}-cue-{idx:02d}")
        audio_path = project_dir / "output" / "audio" / f"{cue_slug}.wav"
        if not audio_path.exists():
            missing.append(str(audio_path))
    return missing


def _compute_overall_status(manifest: ReviewManifest) -> ReviewStatus:
    statuses = {s.status for s in manifest.shots}
    if not statuses:
        return ReviewStatus.PENDING
    if statuses == {ReviewStatus.APPROVED}:
        return ReviewStatus.APPROVED
    if ReviewStatus.REJECTED in statuses:
        return ReviewStatus.NEEDS_REVISION
    return ReviewStatus.PENDING


def _write_manifest(project_dir: Path, manifest: ReviewManifest) -> Path:
    review_dir = project_dir / "output" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    out_path = review_dir / f"{manifest.episode_id}.review.json"
    out_path.write_text(
        json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path
