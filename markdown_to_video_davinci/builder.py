from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from .parser import EpisodePackage, SceneSection, parse_episode, slugify


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def relative_to(base_dir: Path, target: Path) -> str:
    return str(target.relative_to(base_dir))


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def create_project_structure(project_dir: Path) -> dict[str, Path]:
    input_dir = ensure_directory(project_dir / "input")
    output_dir = ensure_directory(project_dir / "output")
    paths = {
        # --- legacy paths (unchanged) ---
        "project": ensure_directory(project_dir),
        "input": input_dir,
        "avatars": ensure_directory(input_dir / "avatars"),
        "markdown": ensure_directory(input_dir / "markdown"),
        "output": output_dir,
        "davinci": ensure_directory(output_dir / "davinci"),
        "images": ensure_directory(output_dir / "images"),
        "manifests": ensure_directory(output_dir / "manifests"),
        "prompts": ensure_directory(output_dir / "prompts"),
        "requests": ensure_directory(output_dir / "requests"),
        # --- new pipeline paths ---
        "literary": ensure_directory(input_dir / "literary"),
        "technical": ensure_directory(input_dir / "technical"),
        "audio": ensure_directory(output_dir / "audio"),
        "clips": ensure_directory(output_dir / "clips"),
        "subtitles": ensure_directory(output_dir / "subtitles"),
        "review": ensure_directory(output_dir / "review"),
        "logs": ensure_directory(output_dir / "logs"),
    }
    return paths


def copy_project_template(project_dir: Path, repository_dir: Path) -> None:
    paths = create_project_structure(project_dir)
    templates_dir = repository_dir / "templates"

    # Legacy episode template
    template_markdown = templates_dir / "episode_template.md"
    destination_markdown = paths["markdown"] / "episode_template.md"
    if template_markdown.exists() and not destination_markdown.exists():
        shutil.copyfile(template_markdown, destination_markdown)

    # Literary episode template → input/literary/
    literary_template = templates_dir / "literary_episode_template.md"
    destination_literary = paths["literary"] / "literary_episode_template.md"
    if literary_template.exists() and not destination_literary.exists():
        shutil.copyfile(literary_template, destination_literary)

    # Technical YAML template → input/technical/
    technical_template = templates_dir / "technical_episode_template.yaml"
    destination_technical = paths["technical"] / "technical_episode_template.yaml"
    if technical_template.exists() and not destination_technical.exists():
        shutil.copyfile(technical_template, destination_technical)


def find_markdown_file(project_dir: Path) -> Path:
    markdown_dir = project_dir / "input" / "markdown"
    candidates = sorted(markdown_dir.glob("*.md"))
    if not candidates:
        raise FileNotFoundError(
            f"No se encontro ningun archivo Markdown en {markdown_dir}. "
            "Usa init-project o copia un .md a input\\markdown."
        )
    return candidates[0]


def build_avatar_manifest(project_dir: Path, episode: EpisodePackage) -> dict[str, dict]:
    avatars_dir = project_dir / "input" / "avatars"
    all_files = [path for path in avatars_dir.iterdir() if path.is_file()] if avatars_dir.exists() else []
    manifest: dict[str, dict] = {}

    for character in episode.characters.values():
        character_slug = slugify(character.name)
        candidates = [
            path
            for path in all_files
            if character_slug in slugify(path.stem) or slugify(path.stem) in character_slug
        ]
        ordered = sorted(candidates, key=lambda path: path.name.lower())
        manifest[character_slug] = {
            "character": character.name,
            "primary_reference": relative_to(project_dir, ordered[0]) if ordered else None,
            "reference_candidates": [relative_to(project_dir, path) for path in ordered],
        }

    return manifest


def build_combined_prompt(
    scene: SceneSection,
    quality_prompt: str,
    character_prompts: dict[str, str],
) -> str:
    prompt_parts = [scene.visual_prompt, f"Episode visual baseline: {quality_prompt}."]
    for character_name in scene.characters:
        prompt = character_prompts.get(slugify(character_name))
        if prompt:
            prompt_parts.append(f"{character_name} reference: {prompt}")
    return " ".join(part.strip() for part in prompt_parts if part.strip())


def build_scene_requests(
    project_dir: Path,
    episode: EpisodePackage,
    avatar_manifest: dict[str, dict],
) -> list[dict]:
    prompts_dir = project_dir / "output" / "prompts"
    requests_dir = project_dir / "output" / "requests"
    images_dir = project_dir / "output" / "images"

    character_prompts = {
        slug: character.prompt
        for slug, character in episode.characters.items()
    }

    requests: list[dict] = []
    for index, scene in enumerate(episode.scenes, start=1):
        slug_base = f"{index:02d}-{slugify(f'{scene.code} {scene.title}')}"
        prompt_path = prompts_dir / f"{slug_base}.txt"
        request_path = requests_dir / f"{slug_base}.json"
        image_path = images_dir / f"{slug_base}.png"

        combined_prompt = build_combined_prompt(scene, episode.quality_prompt, character_prompts)
        prompt_path.write_text(combined_prompt, encoding="utf-8")

        references = []
        for character_name in scene.characters:
            key = slugify(character_name)
            if key in avatar_manifest:
                references.append(
                    {
                        "character_key": key,
                        "character": avatar_manifest[key]["character"],
                        "primary_reference": avatar_manifest[key]["primary_reference"],
                        "reference_candidates": avatar_manifest[key]["reference_candidates"],
                    }
                )

        request_payload = {
            "index": index,
            "scene_code": scene.code,
            "scene_title": scene.title,
            "slug": slug_base,
            "visual_summary": scene.visual_summary,
            "scene_prompt": scene.visual_prompt,
            "combined_prompt": combined_prompt,
            "characters": scene.characters,
            "avatar_references": references,
            "output_image_path": relative_to(project_dir, image_path),
            "output_prompt_path": relative_to(project_dir, prompt_path),
            "output_request_path": relative_to(project_dir, request_path),
            "davinci": {
                "timeline_track": "V1",
                "duration_seconds": 6,
                "transition_in": "cut",
                "transition_out": "cut",
            },
        }
        write_json(request_path, request_payload)
        requests.append(request_payload)

    return requests


def write_scene_manifest(manifests_dir: Path, scenes: list[SceneSection]) -> None:
    write_json(
        manifests_dir / "scene_manifest.json",
        [
            {
                "scene_code": scene.code,
                "scene_title": scene.title,
                "visual_summary": scene.visual_summary,
                "visual_prompt": scene.visual_prompt,
                "characters": scene.characters,
            }
            for scene in scenes
        ],
    )


def write_davinci_csv(project_dir: Path, requests: list[dict]) -> Path:
    csv_path = project_dir / "output" / "davinci" / "davinci_shotlist.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "scene_index",
                "scene_code",
                "scene_title",
                "duration_seconds",
                "timeline_track",
                "image_path",
                "prompt_path",
                "notes",
            ],
        )
        writer.writeheader()
        for request in requests:
            writer.writerow(
                {
                    "scene_index": request["index"],
                    "scene_code": request["scene_code"],
                    "scene_title": request["scene_title"],
                    "duration_seconds": request["davinci"]["duration_seconds"],
                    "timeline_track": request["davinci"]["timeline_track"],
                    "image_path": request["output_image_path"],
                    "prompt_path": request["output_prompt_path"],
                    "notes": request["visual_summary"],
                }
            )
    return csv_path


def build_project(project_dir: Path, markdown_path: Path | None = None) -> dict[str, object]:
    paths = create_project_structure(project_dir)
    markdown_file = markdown_path or find_markdown_file(project_dir)
    markdown_text = markdown_file.read_text(encoding="utf-8")
    episode = parse_episode(markdown_text)

    avatar_manifest = build_avatar_manifest(project_dir, episode)
    requests = build_scene_requests(project_dir, episode, avatar_manifest)

    write_json(paths["manifests"] / "avatar_manifest.json", avatar_manifest)
    write_scene_manifest(paths["manifests"], episode.scenes)
    write_json(paths["manifests"] / "scene_requests.json", requests)
    csv_path = write_davinci_csv(project_dir, requests)

    summary = {
        "project_dir": str(project_dir),
        "markdown_source": str(markdown_file),
        "scene_count": len(episode.scenes),
        "character_count": len(episode.characters),
        "davinci_shotlist": str(csv_path),
    }
    write_json(paths["manifests"] / "build_summary.json", summary)
    return summary
