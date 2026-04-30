import csv
import json
import math
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List

from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


ROOT = Path(os.environ.get("VIDA_ESPEJO_ROOT", str(Path.cwd())))
EPISODES = [
    "Episodio 01 - Vida espejo y quiralidad",
    "Episodio 02 - IA espejo",
    "Episodio 03 - Humano aumentado y exocórtex",
    "Episodio 04 - Átomos, emergencia y consciencia",
    "Episodio 05 - Antimateria y universos espejo",
    "Episodio 06 - Agujeros negros, agujeros blancos y rebote cosmológico",
    "Episodio 07 - Información, lenguaje y código del universo",
    "Episodio 08 - Tecno-sapiens",
    "Episodio 09 - Geopolítica del cómputo",
    "Episodio 10 - Espejo cognitivo y astronomía interior",
]


def resolve_episode_dir(episode_name: str) -> Path:
    nested = ROOT / "04-episodes" / episode_name
    if nested.exists():
        return nested
    return ROOT / episode_name


def resolve_script_path(episode_dir: Path, episode_name: str) -> Path:
    candidates = [
        episode_dir / f"{episode_name}.md",
        episode_dir / "script" / f"{episode_name}.md",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def resolve_stock_root(episode_dir: Path) -> Path:
    nested = episode_dir / "video-stock"
    if nested.exists():
        return nested
    return episode_dir / "videos"


def resolve_semantic_root(episode_dir: Path) -> Path:
    nested = episode_dir / "semantic-plan"
    if nested.exists():
        return nested
    return episode_dir / "videos"


CATEGORY_HINTS = {
    "science": {"ciencia", "cientifico", "científica", "laboratorio", "molécula", "molecular", "proteína", "genética", "quiralidad", "bio", "microscopio", "célula"},
    "medical": {"cerebro", "neural", "neurona", "medicina", "médico", "clínico", "rehabilitación", "salud", "biología", "farmacología", "psico", "cuerpo"},
    "technology": {"ia", "inteligencia", "algoritmo", "modelo", "digital", "tecnología", "tecnologico", "tecnológica", "datos", "software", "automatización"},
    "tech": {"chip", "cómputo", "computo", "servidor", "red", "código", "hardware", "silicio", "procesador", "sistema"},
    "computer": {"ordenador", "pantalla", "interfaz", "código", "programa", "máquina", "memoria", "información"},
    "business-tech": {"industria", "empresa", "infraestructura", "suministro", "fábrica", "mercado", "negocio", "capital", "producción"},
    "business": {"empresa", "economía", "mercado", "comercio", "corporativo", "finanzas", "geopolítica"},
    "industry": {"fábrica", "industrial", "manufactura", "cadena", "producción", "logística", "oblea"},
    "city": {"ciudad", "urbano", "edificio", "tráfico", "red eléctrica", "infraestructura", "movilidad"},
    "people": {"humano", "persona", "sociedad", "cultura", "cuerpo", "mente", "observador"},
    "road": {"camino", "trayectoria", "ruta", "tránsito", "viaje", "desplazamiento"},
    "transport": {"transporte", "circulación", "movimiento", "logística", "vehículo"},
    "space": {"cosmos", "universo", "galaxia", "big bang", "agujero negro", "astronomía", "estrella", "astro", "cósmico"},
    "sky": {"cielo", "nube", "firmamento", "atmósfera", "celeste", "altura"},
    "cloud": {"nube", "cielo", "vapor", "atmósfera", "paisaje"},
    "earth": {"tierra", "planeta", "mundo", "paisaje", "naturaleza", "entorno", "planeta"},
    "water": {"agua", "océano", "mar", "río", "flujo"},
    "sea": {"mar", "olas", "océano", "costa"},
    "forest": {"bosque", "árbol", "selva", "natural"},
    "sun": {"sol", "luz", "amanecer", "atardecer", "energía"},
    "sunset": {"atardecer", "crepúsculo", "ocaso"},
    "double-exposure": {"metáfora", "simbólico", "interior", "conciencia", "pensamiento", "espejo", "abstracto"},
    "abstract": {"emergencia", "consciencia", "información", "lenguaje", "metáfora", "abstracto", "concepto", "idea"},
    "light": {"luz", "señal", "brillo", "destello", "energía"},
    "background": {"fondo", "atmósfera", "transición", "entorno"},
    "smoke": {"niebla", "humo", "indefinición", "frontera", "misterio"},
    "music": {"ritmo", "sincronía", "señal", "vibración"},
    "lifestyle": {"cotidiano", "vida diaria", "gesto", "persona"},
    "night": {"noche", "oscuridad", "misterio", "sombra"},
    "street": {"calle", "urbano", "peatón", "movimiento"},
    "nature": {"naturaleza", "vida", "ecosistema", "paisaje"},
}

ABSTRACT_TERMS = {
    "conciencia", "consciencia", "información", "código", "lenguaje", "metáfora", "idea",
    "identidad", "percepción", "emergencia", "hipótesis", "filosóficamente", "interior",
}


@dataclass
class ClipCandidate:
    file_name: str
    file_path: str
    category: str
    title: str
    page_url: str
    mp4_url: str
    duration: float

    @property
    def search_text(self) -> str:
        return normalize_text(f"{self.category} {self.title} {self.page_url}")


def run_ffprobe(path: Path) -> float:
    return float(
        subprocess.check_output(
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
            text=True,
        ).strip()
    )


def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_sentences(text: str) -> List[str]:
    raw = re.split(r"(?<=[\.\!\?\:])\s+|\n{2,}", text.strip())
    cleaned = [segment.strip() for segment in raw if segment.strip()]
    merged = []
    buffer = ""
    for segment in cleaned:
        if not buffer:
            buffer = segment
        elif len(buffer) < 110:
            buffer += " " + segment
        else:
            merged.append(buffer)
            buffer = segment
    if buffer:
        merged.append(buffer)
    return merged


def clean_body(lines: List[str]) -> str:
    output = []
    for line in lines:
        s = line.strip()
        if not s or s == "---":
            continue
        s = re.sub(r"^[-*]\s+", "", s)
        s = re.sub(r"^\d+\.\s+", "", s)
        s = s.replace("**", "").replace("`", "")
        output.append(s)
    return "\n\n".join(output).strip()


def extract_blocks(md_path: Path):
    text = md_path.read_text(encoding="utf-8").split("## Apéndice audiovisual bilingüe")[0]
    blocks = []
    current_title = None
    current_body = []
    current_level = 1
    for line in text.splitlines():
        match = re.match(r"^(#{1,3})\s+(.*)$", line)
        if match:
            if current_title is not None:
                blocks.append((current_level, current_title.strip(), clean_body(current_body)))
            current_level = len(match.group(1))
            current_title = match.group(2).strip()
            current_body = []
        elif current_title is not None:
            current_body.append(line)
    if current_title is not None:
        blocks.append((current_level, current_title.strip(), clean_body(current_body)))
    return blocks


def parse_stock_manifest(episode_dir: Path) -> List[ClipCandidate]:
    stock_root = resolve_stock_root(episode_dir)
    manifest = stock_root / "stock-sources.md"
    if not manifest.exists():
        manifest = stock_root / "stock-sources-sciclip.md"
    lines = manifest.read_text(encoding="utf-8").splitlines()
    clips = []
    pattern = re.compile(r"^\|\s*(\d+\.mp4)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|")
    for line in lines:
        match = pattern.match(line)
        if not match:
            continue
        file_name = match.group(1).strip()
        category = match.group(2).strip()
        title = match.group(4).strip()
        page_url = match.group(5).strip()
        mp4_url = match.group(6).strip()
        file_path = stock_root / file_name
        if not file_path.exists():
            file_path = stock_root / "sciclip-stock" / file_name
        clips.append(
            ClipCandidate(
                file_name=file_name,
                file_path=str(file_path),
                category=category,
                title=title,
                page_url=page_url,
                mp4_url=mp4_url,
                duration=run_ffprobe(file_path),
            )
        )
    return clips


def category_boost(query: str, category: str) -> float:
    words = set(normalize_text(query).split())
    hints = CATEGORY_HINTS.get(category, set())
    if not hints:
        return 0.0
    overlap = len(words & hints)
    boost = min(0.18, overlap * 0.03)
    if words & ABSTRACT_TERMS and category in {"abstract", "double-exposure", "light", "background", "smoke"}:
        boost += 0.05
    return boost


def diversity_penalty(file_name: str, selected_recent: List[str]) -> float:
    if file_name not in selected_recent:
        return 0.0
    distance = len(selected_recent) - 1 - selected_recent[::-1].index(file_name)
    return max(0.06, 0.18 - min(distance, 10) * 0.012)


def build_vectors(queries: List[str], clips: List[ClipCandidate]):
    clip_texts = [clip.search_text for clip in clips]
    all_texts = queries + clip_texts
    word_vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    char_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1)
    word_matrix = word_vectorizer.fit_transform(all_texts)
    char_matrix = char_vectorizer.fit_transform(all_texts)
    matrix = hstack([word_matrix, char_matrix])
    return matrix[: len(queries)], matrix[len(queries) :]


def estimate_sentence_durations(sentences: List[str], total_duration: float) -> List[float]:
    if not sentences:
        return []
    weights = [max(18, len(sentence)) for sentence in sentences]
    weight_sum = sum(weights)
    raw = [total_duration * weight / weight_sum for weight in weights]
    minimum = 2.8
    adjusted = [max(minimum, value) for value in raw]
    factor = total_duration / sum(adjusted)
    return [value * factor for value in adjusted]


def create_segments(episode_dir: Path, episode_name: str):
    blocks = extract_blocks(resolve_script_path(episode_dir, episode_name))
    segments = []
    cursor = 0.0
    for idx, (_, heading, body) in enumerate(blocks, start=1):
        block_audio = episode_dir / "audio" / "es" / "blocks" / f"{idx:02}.mp3"
        female_audio = episode_dir / "audio" / "es" / "headings-female" / f"{idx:02}.mp3"
        block_duration = run_ffprobe(block_audio)
        heading_duration = min(block_duration, run_ffprobe(female_audio) + 0.35)
        body_duration = max(0.8, block_duration - heading_duration)
        segments.append(
            {
                "segment_id": f"{idx:02}-00",
                "type": "heading",
                "block_index": idx,
                "heading": heading,
                "text": heading,
                "start": round(cursor, 3),
                "duration": round(heading_duration, 3),
                "query": f"{episode_name} {heading} cartela transicion cinematografica",
            }
        )
        cursor += heading_duration
        sentences = split_sentences(body)
        for sentence_index, (sentence, duration) in enumerate(zip(sentences, estimate_sentence_durations(sentences, body_duration)), start=1):
            segments.append(
                {
                    "segment_id": f"{idx:02}-{sentence_index:02}",
                    "type": "body",
                    "block_index": idx,
                    "heading": heading,
                    "text": sentence,
                    "start": round(cursor, 3),
                    "duration": round(duration, 3),
                    "query": f"{episode_name} {heading} {sentence}",
                }
            )
            cursor += duration
    return segments


def rank_segments(segments, clips: List[ClipCandidate], episode_name: str):
    queries = [normalize_text(segment["query"]) for segment in segments]
    query_matrix, clip_matrix = build_vectors(queries, clips)
    selected_recent = []
    all_scores = cosine_similarity(query_matrix, clip_matrix)
    planned = []
    for row_index, segment in enumerate(segments):
        best_choice = None
        for clip_index, clip in enumerate(clips):
            score = float(all_scores[row_index, clip_index])
            score += category_boost(segment["query"], clip.category)
            if segment["type"] == "heading" and clip.category in {"background", "light", "double-exposure", "abstract", "smoke"}:
                score += 0.08
            score -= diversity_penalty(clip.file_name, selected_recent)
            required_duration = max(2.0, min(segment["duration"] + 0.15, clip.duration))
            if clip.duration < required_duration:
                score -= 0.08
            if best_choice is None or score > best_choice["score"]:
                best_choice = {
                    "clip": clip,
                    "score": score,
                    "required_duration": required_duration,
                }
        clip = best_choice["clip"]
        selected_recent.append(clip.file_name)
        if len(selected_recent) > 12:
            selected_recent.pop(0)
        planned.append(
            {
                **segment,
                "clip_file": clip.file_name,
                "clip_path": clip.file_path,
                "clip_category": clip.category,
                "clip_title": clip.title,
                "clip_source_page": clip.page_url,
                "clip_duration": round(clip.duration, 3),
                "recommended_in": 0.0,
                "recommended_out": round(min(clip.duration, best_choice["required_duration"]), 3),
                "score": round(best_choice["score"], 4),
            }
        )
    return planned


def write_outputs(episode_dir: Path, episode_name: str, planned_segments):
    semantic_root = resolve_semantic_root(episode_dir)
    semantic_root.mkdir(parents=True, exist_ok=True)
    json_path = semantic_root / "semantic-shot-plan.json"
    csv_path = semantic_root / "semantic-shot-plan.csv"
    md_path = semantic_root / "semantic-shot-plan.md"

    json_path.write_text(
        json.dumps(
            {
                "episode": episode_name,
                "timeline_seconds": round(sum(segment["duration"] for segment in planned_segments), 3),
                "segment_count": len(planned_segments),
                "segments": planned_segments,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "segment_id",
                "type",
                "block_index",
                "heading",
                "start",
                "duration",
                "text",
                "clip_file",
                "clip_category",
                "clip_title",
                "clip_path",
                "clip_source_page",
                "clip_duration",
                "recommended_in",
                "recommended_out",
                "score",
                "query",
            ],
        )
        writer.writeheader()
        writer.writerows(planned_segments)

    lines = [
        f"# Plan semántico de vídeo - {episode_name}",
        "",
        "- Objetivo: alinear cada unidad narrativa con un clip de stock más próximo semánticamente usando ranking local.",
        "- Uso recomendado: revisión del premontaje y conformado fino en DaVinci Resolve.",
        "",
        "| Segmento | Inicio | Duración | Tipo | Texto | Clip sugerido | Categoría | Score |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for segment in planned_segments:
        text = segment["text"].replace("|", "/")
        clip_title = segment["clip_title"].replace("|", "/")
        lines.append(
            f"| {segment['segment_id']} | {segment['start']:.2f}s | {segment['duration']:.2f}s | {segment['type']} | {text} | {segment['clip_file']} - {clip_title} | {segment['clip_category']} | {segment['score']:.3f} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    results = []
    for episode_name in EPISODES:
        episode_dir = resolve_episode_dir(episode_name)
        clips = parse_stock_manifest(episode_dir)
        segments = create_segments(episode_dir, episode_name)
        planned = rank_segments(segments, clips, episode_name)
        write_outputs(episode_dir, episode_name, planned)
        results.append((episode_name, len(segments), len(clips)))
    for episode_name, segment_count, clip_count in results:
        print(f"{episode_name}|SEGMENTS={segment_count}|CLIPS={clip_count}|PLAN=OK")


if __name__ == "__main__":
    main()
