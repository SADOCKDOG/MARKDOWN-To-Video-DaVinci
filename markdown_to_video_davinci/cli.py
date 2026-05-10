from __future__ import annotations

import argparse
import json
from pathlib import Path

from .builder import build_project, copy_project_template


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="markdown-to-video-davinci",
        description="Convierte guiones Markdown en manifiestos y shotlists para video.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ------------------------------------------------------------------
    # Legacy commands (unchanged)
    # ------------------------------------------------------------------
    init_parser = subparsers.add_parser(
        "init-project", help="Crea la estructura base de un proyecto."
    )
    init_parser.add_argument("project_dir", help="Ruta del proyecto a inicializar.")

    build_parser_cmd = subparsers.add_parser(
        "build", help="Genera prompts, manifiestos y shotlist (modo legacy)."
    )
    build_parser_cmd.add_argument("project_dir", help="Ruta del proyecto.")
    build_parser_cmd.add_argument(
        "--markdown",
        help=(
            "Ruta del Markdown a procesar. "
            "Si se omite, usa el primer .md encontrado en input\\markdown."
        ),
    )

    # ------------------------------------------------------------------
    # Stage 1 — compile-literary
    # ------------------------------------------------------------------
    compile_literary_cmd = subparsers.add_parser(
        "compile-literary",
        help=(
            "Etapa 1: convierte un guion literario Markdown en un borrador "
            "de guion tecnico YAML en input/technical/."
        ),
    )
    compile_literary_cmd.add_argument("project_dir", help="Ruta del proyecto.")
    compile_literary_cmd.add_argument(
        "--markdown",
        help=(
            "Ruta del Markdown literario. "
            "Si se omite, usa el primer .md en input/literary/ o input/markdown/."
        ),
    )
    compile_literary_cmd.add_argument(
        "--episode-id",
        dest="episode_id",
        help="Identificador del episodio (slug). Por defecto, el nombre del archivo .md.",
    )

    # ------------------------------------------------------------------
    # Stage 2 — build-technical / breakdown
    # ------------------------------------------------------------------
    build_technical_cmd = subparsers.add_parser(
        "build-technical",
        help=(
            "Etapa 2: convierte el guion tecnico YAML en el manifiesto "
            "canonico JSON (output/manifests/<id>.canonical.json)."
        ),
    )
    build_technical_cmd.add_argument("project_dir", help="Ruta del proyecto.")
    build_technical_cmd.add_argument(
        "--technical",
        help=(
            "Ruta del YAML tecnico. "
            "Si se omite, usa el primer .yaml encontrado en input/technical/."
        ),
    )

    # 'breakdown' is an alias for 'build-technical'
    breakdown_cmd = subparsers.add_parser(
        "breakdown",
        help="Alias de build-technical.",
    )
    breakdown_cmd.add_argument("project_dir", help="Ruta del proyecto.")
    breakdown_cmd.add_argument(
        "--technical",
        help="Ruta del YAML tecnico.",
    )

    # ------------------------------------------------------------------
    # Stage 3 — generate-assets
    # ------------------------------------------------------------------
    generate_assets_cmd = subparsers.add_parser(
        "generate-assets",
        help=(
            "Etapa 3: genera los manifiestos de jobs de imagen, voz y clip "
            "a partir del canonico JSON."
        ),
    )
    generate_assets_cmd.add_argument("project_dir", help="Ruta del proyecto.")
    generate_assets_cmd.add_argument(
        "--canonical",
        help=(
            "Ruta del JSON canonico. "
            "Si se omite, usa el primer .canonical.json en output/manifests/."
        ),
    )
    generate_assets_cmd.add_argument(
        "--image-provider",
        dest="image_provider",
        default="stability",
        help="Proveedor de imagen (stability | openvino). Por defecto: stability.",
    )
    generate_assets_cmd.add_argument(
        "--tts-provider",
        dest="tts_provider",
        default="local",
        help="Proveedor de TTS (local). Por defecto: local.",
    )

    # ------------------------------------------------------------------
    # Stage 4 — prepare-resolve
    # ------------------------------------------------------------------
    prepare_resolve_cmd = subparsers.add_parser(
        "prepare-resolve",
        help=(
            "Etapa 4: genera el paquete Resolve JSON y el CSV de shotlist "
            "a partir del canonico JSON."
        ),
    )
    prepare_resolve_cmd.add_argument("project_dir", help="Ruta del proyecto.")
    prepare_resolve_cmd.add_argument(
        "--canonical",
        help="Ruta del JSON canonico.",
    )

    # ------------------------------------------------------------------
    # Stage 5 — review-pack
    # ------------------------------------------------------------------
    review_pack_cmd = subparsers.add_parser(
        "review-pack",
        help=(
            "Etapa 5: genera o actualiza el manifiesto de revision humana "
            "(output/review/<id>.review.json)."
        ),
    )
    review_pack_cmd.add_argument("project_dir", help="Ruta del proyecto.")
    review_pack_cmd.add_argument(
        "--canonical",
        help="Ruta del JSON canonico.",
    )

    # ------------------------------------------------------------------
    # Stage 6a — run-images
    # ------------------------------------------------------------------
    run_images_cmd = subparsers.add_parser(
        "run-images",
        help=(
            "Etapa 6a: ejecuta los jobs de imagen planificados del registro "
            "de assets usando el proveedor indicado (stability | openvino)."
        ),
    )
    run_images_cmd.add_argument("project_dir", help="Ruta del proyecto.")
    run_images_cmd.add_argument(
        "--registry",
        help=(
            "Ruta del JSON del registro de assets. "
            "Si se omite, usa el primero encontrado en output/manifests/."
        ),
    )
    run_images_cmd.add_argument(
        "--image-provider",
        dest="image_provider",
        default="stability",
        help="Proveedor de imagen (stability | openvino). Por defecto: stability.",
    )
    run_images_cmd.add_argument(
        "--model-dir",
        dest="model_dir",
        help="Directorio del modelo OpenVINO IR (solo para --image-provider openvino).",
    )

    # ------------------------------------------------------------------
    # Stage 6b — run-voice
    # ------------------------------------------------------------------
    run_voice_cmd = subparsers.add_parser(
        "run-voice",
        help=(
            "Etapa 6b: ejecuta los jobs de voz planificados del registro "
            "de assets usando el proveedor indicado (local | elevenlabs)."
        ),
    )
    run_voice_cmd.add_argument("project_dir", help="Ruta del proyecto.")
    run_voice_cmd.add_argument(
        "--registry",
        help="Ruta del JSON del registro de assets.",
    )
    run_voice_cmd.add_argument(
        "--tts-provider",
        dest="tts_provider",
        default="local",
        help="Proveedor TTS (local | elevenlabs). Por defecto: local.",
    )
    run_voice_cmd.add_argument(
        "--voice-id",
        dest="voice_id",
        help="Voice ID de ElevenLabs (solo para --tts-provider elevenlabs).",
    )

    # ------------------------------------------------------------------
    # Stage 6c — run-clips
    # ------------------------------------------------------------------
    run_clips_cmd = subparsers.add_parser(
        "run-clips",
        help=(
            "Etapa 6c: ejecuta los jobs de clip planificados del registro "
            "de assets ensamblando cada still + audio via FFmpeg."
        ),
    )
    run_clips_cmd.add_argument("project_dir", help="Ruta del proyecto.")
    run_clips_cmd.add_argument(
        "--registry",
        help="Ruta del JSON del registro de assets.",
    )
    run_clips_cmd.add_argument(
        "--ffmpeg-bin",
        dest="ffmpeg_bin",
        default="ffmpeg",
        help="Ruta o nombre del ejecutable ffmpeg. Por defecto: ffmpeg.",
    )

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    repository_dir = Path(__file__).resolve().parent.parent
    project_dir = Path(args.project_dir).resolve()

    # -- Legacy: init-project -----------------------------------------------
    if args.command == "init-project":
        copy_project_template(project_dir, repository_dir)
        print(
            json.dumps(
                {"initialized_project": str(project_dir)}, ensure_ascii=False, indent=2
            )
        )
        return

    # -- Legacy: build -------------------------------------------------------
    if args.command == "build":
        markdown_path = Path(args.markdown).resolve() if args.markdown else None
        summary = build_project(project_dir, markdown_path)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    # -- Stage 1: compile-literary -------------------------------------------
    if args.command == "compile-literary":
        from .pipeline.literary import compile_literary

        markdown_path = _resolve_markdown(project_dir, getattr(args, "markdown", None))
        out_path = compile_literary(
            project_dir,
            markdown_path,
            episode_id=getattr(args, "episode_id", None),
        )
        print(
            json.dumps(
                {"technical_yaml": str(out_path), "source_markdown": str(markdown_path)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    # -- Stage 2: build-technical / breakdown --------------------------------
    if args.command in ("build-technical", "breakdown"):
        from .pipeline.breakdown import build_canonical

        technical_path = _resolve_technical(project_dir, getattr(args, "technical", None))
        canonical_path = build_canonical(project_dir, technical_path)
        print(
            json.dumps(
                {
                    "canonical_json": str(canonical_path),
                    "source_technical": str(technical_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    # -- Stage 3: generate-assets -------------------------------------------
    if args.command == "generate-assets":
        import dataclasses

        from .models.canonical import CanonicalEpisode
        from .pipeline.assets import build_asset_registry

        canonical_path = _resolve_canonical(project_dir, getattr(args, "canonical", None))
        episode = _load_canonical(canonical_path)
        registry_path = build_asset_registry(
            project_dir,
            episode,
            image_provider=args.image_provider,
            tts_provider=args.tts_provider,
        )
        print(
            json.dumps(
                {
                    "asset_registry": str(registry_path),
                    "canonical_json": str(canonical_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    # -- Stage 4: prepare-resolve -------------------------------------------
    if args.command == "prepare-resolve":
        from .models.canonical import CanonicalEpisode
        from .pipeline.resolve_prep import build_resolve_package

        canonical_path = _resolve_canonical(project_dir, getattr(args, "canonical", None))
        episode = _load_canonical(canonical_path)
        package_path = build_resolve_package(project_dir, episode)
        print(
            json.dumps(
                {
                    "resolve_package": str(package_path),
                    "canonical_json": str(canonical_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    # -- Stage 5: review-pack -----------------------------------------------
    if args.command == "review-pack":
        from .models.canonical import CanonicalEpisode
        from .pipeline.review import build_review_manifest

        canonical_path = _resolve_canonical(project_dir, getattr(args, "canonical", None))
        episode = _load_canonical(canonical_path)
        manifest_path = build_review_manifest(project_dir, episode)
        print(
            json.dumps(
                {
                    "review_manifest": str(manifest_path),
                    "canonical_json": str(canonical_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    # -- Stage 6a: run-images -----------------------------------------------
    if args.command == "run-images":
        from .pipeline.run_assets import run_image_jobs

        kwargs = {}
        if getattr(args, "model_dir", None):
            kwargs["model_dir"] = args.model_dir
        registry_path = run_image_jobs(
            project_dir,
            image_provider_name=args.image_provider,
            registry_path=getattr(args, "registry", None),
            **kwargs,
        )
        print(
            json.dumps(
                {"asset_registry": str(registry_path), "image_provider": args.image_provider},
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    # -- Stage 6b: run-voice ------------------------------------------------
    if args.command == "run-voice":
        from .pipeline.run_assets import run_voice_jobs

        kwargs = {}
        if getattr(args, "voice_id", None):
            kwargs["voice_id"] = args.voice_id
        registry_path = run_voice_jobs(
            project_dir,
            tts_provider_name=args.tts_provider,
            registry_path=getattr(args, "registry", None),
            **kwargs,
        )
        print(
            json.dumps(
                {"asset_registry": str(registry_path), "tts_provider": args.tts_provider},
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    # -- Stage 6c: run-clips ------------------------------------------------
    if args.command == "run-clips":
        from .pipeline.run_assets import run_clip_jobs

        registry_path = run_clip_jobs(
            project_dir,
            ffmpeg_bin=args.ffmpeg_bin,
            registry_path=getattr(args, "registry", None),
        )
        print(
            json.dumps(
                {"asset_registry": str(registry_path), "clip_runner": "ffmpeg"},
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    raise ValueError(f"Comando no soportado: {args.command}")


# ---------------------------------------------------------------------------
# Path resolution helpers
# ---------------------------------------------------------------------------


def _resolve_markdown(project_dir: Path, explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    # Try input/literary first, then fall back to input/markdown
    for subdir in ("literary", "markdown"):
        candidates = sorted((project_dir / "input" / subdir).glob("*.md"))
        if candidates:
            return candidates[0]
    raise FileNotFoundError(
        f"No se encontro ningun archivo Markdown en {project_dir}/input/literary/ "
        f"ni en {project_dir}/input/markdown/."
    )


def _resolve_technical(project_dir: Path, explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    candidates = sorted((project_dir / "input" / "technical").glob("*.yaml"))
    if not candidates:
        raise FileNotFoundError(
            f"No se encontro ningun archivo YAML en {project_dir}/input/technical/. "
            "Ejecuta primero: compile-literary."
        )
    return candidates[0]


def _resolve_canonical(project_dir: Path, explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    candidates = sorted((project_dir / "output" / "manifests").glob("*.canonical.json"))
    if not candidates:
        raise FileNotFoundError(
            f"No se encontro ningun .canonical.json en {project_dir}/output/manifests/. "
            "Ejecuta primero: build-technical."
        )
    return candidates[0]


def _load_canonical(canonical_path: Path):
    import json

    from .models.canonical import CanonicalEpisode

    data = json.loads(canonical_path.read_text(encoding="utf-8"))
    return CanonicalEpisode.from_dict(data)


if __name__ == "__main__":
    main()
