from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class CharacterPrompt:
    name: str
    prompt: str


@dataclass(frozen=True)
class SceneSection:
    code: str
    title: str
    visual_summary: str
    visual_prompt: str
    characters: list[str]


@dataclass(frozen=True)
class EpisodePackage:
    quality_prompt: str
    characters: dict[str, CharacterPrompt]
    scenes: list[SceneSection]


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_value = ascii_value.lower()
    ascii_value = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return re.sub(r"-{2,}", "-", ascii_value)


def normalize_inline_text(value: str) -> str:
    return " ".join(line.strip() for line in value.strip().splitlines() if line.strip())


def extract_text_block(value: str) -> str:
    fenced_match = re.search(r"```(?:text)?\s*(.*?)```", value, re.DOTALL | re.IGNORECASE)
    if fenced_match:
        return normalize_inline_text(fenced_match.group(1))
    return normalize_inline_text(value)


def split_h1_sections(markdown_text: str) -> list[tuple[str, str]]:
    lines = markdown_text.splitlines()
    sections: list[tuple[str, str]] = []
    current_heading: str | None = None
    current_body: list[str] = []

    for line in lines:
        if line.startswith("# "):
            if current_heading is not None:
                sections.append((current_heading, "\n".join(current_body).strip()))
            current_heading = line[2:].strip()
            current_body = []
            continue
        if current_heading is not None:
            current_body.append(line)

    if current_heading is not None:
        sections.append((current_heading, "\n".join(current_body).strip()))

    return sections


def split_h2_sections(section_body: str) -> dict[str, str]:
    lines = section_body.splitlines()
    sections: dict[str, list[str]] = {}
    current_heading: str | None = None

    for line in lines:
        heading_match = re.match(r"^##\s+(.+?)\s*$", line)
        if heading_match:
            current_heading = heading_match.group(1).strip()
            sections.setdefault(current_heading, [])
            continue
        if current_heading is not None:
            sections[current_heading].append(line)

    return {heading: "\n".join(content).strip() for heading, content in sections.items()}


def extract_quality_prompt(markdown_text: str) -> str:
    heading_match = re.search(
        r"^##\s+Calidad visual\s*$([\s\S]*?)(?=^##\s+|\Z)",
        markdown_text,
        re.MULTILINE | re.IGNORECASE,
    )
    if not heading_match:
        raise ValueError("No se encontro la seccion '## Calidad visual'.")

    quality_prompt = extract_text_block(heading_match.group(1))
    if not quality_prompt:
        raise ValueError("La seccion '## Calidad visual' esta vacia.")
    return quality_prompt


def normalize_character_heading(heading: str) -> str:
    match = re.match(r"^PERSONAJE\s*[-—:]\s*(.+)$", heading, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return heading.strip()


def parse_character_list(value: str) -> list[str]:
    if not value.strip():
        return []

    bullet_matches = [
        line.strip()[1:].strip()
        for line in value.splitlines()
        if line.strip().startswith(("-", "*"))
    ]
    items = bullet_matches or [item.strip() for item in re.split(r",|;", value) if item.strip()]
    return [item for item in items if item]


def parse_scene_heading(heading: str) -> tuple[str, str]:
    match = re.match(r"^(ESCENA\s+(?:\d{1,3}|FINAL))(?:\s*[-—:]\s*(.+))?$", heading, re.IGNORECASE)
    if not match:
        raise ValueError(f"Encabezado de escena no valido: {heading!r}")
    code = match.group(1).upper()
    title = (match.group(2) or code).strip()
    return code, title


def parse_episode(markdown_text: str) -> EpisodePackage:
    quality_prompt = extract_quality_prompt(markdown_text)
    characters: dict[str, CharacterPrompt] = {}
    scenes: list[SceneSection] = []

    for heading, body in split_h1_sections(markdown_text):
        normalized_heading = heading.strip()
        subsection_map = split_h2_sections(body)

        if normalized_heading.upper().startswith("ESCENA "):
            code, title = parse_scene_heading(normalized_heading)
            visual_summary = normalize_inline_text(subsection_map.get("Visual", ""))
            visual_prompt = extract_text_block(subsection_map.get("Prompt Visual", ""))
            characters_in_scene = parse_character_list(subsection_map.get("Personajes", ""))

            if not visual_summary:
                raise ValueError(f"La escena {code} no tiene seccion '## Visual'.")
            if not visual_prompt:
                raise ValueError(f"La escena {code} no tiene seccion '## Prompt Visual'.")

            scenes.append(
                SceneSection(
                    code=code,
                    title=title,
                    visual_summary=visual_summary,
                    visual_prompt=visual_prompt,
                    characters=characters_in_scene,
                )
            )
            continue

        prompt_block = subsection_map.get("Prompt IA")
        if prompt_block:
            name = normalize_character_heading(normalized_heading)
            key = slugify(name)
            characters[key] = CharacterPrompt(name=name, prompt=extract_text_block(prompt_block))

    if not scenes:
        raise ValueError("No se encontraron escenas en el Markdown.")

    return EpisodePackage(quality_prompt=quality_prompt, characters=characters, scenes=scenes)
