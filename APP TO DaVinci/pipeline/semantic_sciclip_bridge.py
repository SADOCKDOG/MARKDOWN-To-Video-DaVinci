import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib.parse import quote

import requests
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from semantic_video_planner import (
    CATEGORY_HINTS,
    ABSTRACT_TERMS,
    ClipCandidate,
    EPISODES,
    ROOT,
    create_segments,
    normalize_text,
    rank_segments,
    resolve_episode_dir,
    resolve_stock_root,
    write_outputs,
)

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
DEFAULT_SOURCES = ["pexels_v", "pixabay_v", "nasa_v", "nasa_svs", "archive_v", "coverr", "wikimedia_v"]
MP4_SOURCES = {"pexels_v", "pixabay_v", "nasa_v", "nasa_svs", "archive_v", "coverr"}
STOPWORDS = {
    "a", "al", "algo", "ante", "asi", "aun", "aunque", "bajo", "cada", "casi", "como", "con",
    "contra", "cual", "cuando", "de", "del", "desde", "donde", "dos", "el", "ella", "ellas", "ello",
    "ellos", "en", "entre", "era", "eran", "eres", "es", "esa", "esas", "ese", "eso", "esos", "esta",
    "estaba", "estado", "estamos", "estan", "estar", "estas", "este", "esto", "estos", "fue", "fueron",
    "ha", "hay", "hasta", "hoy", "la", "las", "le", "les", "lo", "los", "mas", "me", "mi", "mientras",
    "muy", "nada", "ni", "no", "nos", "o", "otra", "otro", "para", "pero", "por", "porque", "que", "quien",
    "se", "ser", "si", "sin", "sobre", "son", "su", "sus", "tambien", "te", "tiene", "tienen", "todo", "todos",
    "tras", "tu", "un", "una", "uno", "unos", "ya", "y",
}

PHRASE_TRANSLATIONS = [
    ("vida espejo", "mirror life molecular chirality laboratory"),
    ("ia espejo", "mirror artificial intelligence digital reflection interface"),
    ("humano aumentado", "human augmentation prosthetics cyborg"),
    ("agujero negro", "black hole space simulation galaxy"),
    ("agujeros negros", "black holes space simulation galaxy"),
    ("agujero blanco", "white hole cosmology simulation"),
    ("agujeros blancos", "white holes cosmology simulation"),
    ("rebote cosmologico", "cosmic bounce early universe simulation"),
    ("universo espejo", "mirror universe cosmology symmetry"),
    ("espejo cognitivo", "human mind reflection consciousness silhouette"),
    ("astronomia interior", "stargazing inner world consciousness galaxy"),
    ("codigo del universo", "information code data universe visualization"),
    ("geopolitica del computo", "semiconductor supply chain datacenter geopolitics"),
    ("tecno sapiens", "future human technology city artificial intelligence"),
    ("tecno-sapiens", "future human technology city artificial intelligence"),
]

TOKEN_TRANSLATIONS = {
    "ia": "artificial intelligence",
    "inteligencia": "intelligence",
    "artificial": "artificial",
    "espejo": "mirror",
    "vida": "life",
    "quiralidad": "chirality molecule chemistry",
    "moleculas": "molecules chemistry laboratory",
    "molecula": "molecule chemistry laboratory",
    "atomos": "atoms particles laboratory",
    "atomo": "atom particle laboratory",
    "consciencia": "consciousness human mind silhouette",
    "conciencia": "consciousness human mind silhouette",
    "emergencia": "emergence complexity abstract system",
    "antimateria": "antimatter particle accelerator space",
    "cosmologico": "cosmology universe",
    "cosmologia": "cosmology universe",
    "universo": "universe galaxy space",
    "universos": "universes galaxy space",
    "negro": "black",
    "blanco": "white",
    "agujero": "hole",
    "agujeros": "holes",
    "informacion": "information data code",
    "lenguaje": "language communication code",
    "codigo": "code data network",
    "exocortex": "brain computer interface augmented human",
    "exocortext": "brain computer interface augmented human",
    "cerebro": "brain neural medical",
    "humano": "human people portrait",
    "humana": "human people portrait",
    "aumentado": "augmented future prosthetics",
    "chip": "chip semiconductor hardware",
    "chips": "chips semiconductor hardware",
    "computo": "computing datacenter servers",
    "hardware": "hardware electronics chips",
    "geopolitica": "geopolitics supply chain industry",
    "astronomia": "astronomy telescope galaxy stars",
    "interior": "interior silhouette introspection",
    "sintetica": "synthetic biology laboratory",
    "genetica": "genetics dna laboratory",
}

EPISODE_EXPANSIONS = {
    "Episodio 01 - Vida espejo y quiralidad": [
        "science laboratory microscope chirality",
        "molecules chemistry laboratory",
    ],
    "Episodio 02 - IA espejo": [
        "artificial intelligence robot interface",
        "human face screen code",
    ],
    "Episodio 03 - Humano aumentado y exocórtex": [
        "brain computer interface prosthetics",
        "augmented human neural technology",
    ],
    "Episodio 04 - Átomos, emergencia y consciencia": [
        "atoms particles laboratory abstract",
        "consciousness silhouette abstract light",
    ],
    "Episodio 05 - Antimateria y universos espejo": [
        "antimatter particle accelerator",
        "mirror universe galaxy",
    ],
    "Episodio 06 - Agujeros negros, agujeros blancos y rebote cosmológico": [
        "black hole galaxy",
        "white hole cosmology",
        "cosmic bounce universe",
    ],
    "Episodio 07 - Información, lenguaje y código del universo": [
        "data code network communication",
        "information signal abstract screen",
    ],
    "Episodio 08 - Tecno-sapiens": [
        "future human city robots",
        "technology society people street",
    ],
    "Episodio 09 - Geopolítica del cómputo": [
        "semiconductor factory datacenter",
        "supply chain chips industry",
    ],
    "Episodio 10 - Espejo cognitivo y astronomía interior": [
        "silhouette stars galaxy telescope",
        "astronomy universe abstract light",
    ],
}

SOURCE_META = {
    "pexels_v": {"name": "Pexels Videos", "license": "Pexels License", "priority": 0.11},
    "pixabay_v": {"name": "Pixabay Videos", "license": "Pixabay License", "priority": 0.1},
    "nasa_v": {"name": "NASA Media", "license": "Public Domain (NASA)", "priority": 0.14},
    "nasa_svs": {"name": "NASA SVS", "license": "Public Domain (NASA SVS)", "priority": 0.15},
    "archive_v": {"name": "Internet Archive", "license": "Public Domain / CC", "priority": 0.06},
    "coverr": {"name": "Coverr", "license": "Coverr License", "priority": 0.07},
    "wikimedia_v": {"name": "Wikimedia Commons", "license": "CC / Public Domain", "priority": 0.04},
}

SECRETS_CANDIDATES = [
    Path(__file__).resolve().parents[1] / "SciClip" / ".streamlit" / "secrets.toml",
    Path.home() / ".streamlit" / "secrets.toml",
]


@dataclass
class SearchResult:
    source: str
    title: str
    description: str
    download_url: str
    page_url: str
    duration: float | None
    width: int
    height: int
    quality: str
    author: str
    license_short: str
    query: str
    inferred_category: str

    @property
    def resolution_label(self) -> str:
        if self.height:
            return f"{self.height}p"
        if self.quality:
            return self.quality
        return "unknown"

    @property
    def search_text(self) -> str:
        base = f"{self.query} {self.title} {self.description} {self.author} {self.inferred_category}"
        return normalize_text(base)


def clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", str(text or ""))


def load_secrets() -> Dict[str, str]:
    secrets: Dict[str, str] = {}
    if tomllib is None:
        return secrets
    for candidate in SECRETS_CANDIDATES:
        if not candidate.exists():
            continue
        data = tomllib.loads(candidate.read_text(encoding="utf-8"))
        for key in [
            "PEXELS_API_KEY",
            "PIXABAY_API_KEY",
            "NASA_API_KEY",
            "UNSPLASH_ACCESS_KEY",
            "FLICKR_API_KEY",
        ]:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                secrets[key] = value.strip()
        if secrets:
            break
    return secrets


def get_key(name: str, secrets: Dict[str, str], default: str = "") -> str:
    value = os.environ.get(name) or secrets.get(name) or default
    return value.strip()


def safe_get_json(url: str, *, headers=None, params=None, timeout: int = 15):
    try:
        merged_headers = {"User-Agent": UA, "Accept": "application/json, text/plain, */*"}
        if headers:
            merged_headers.update(headers)
        response = requests.get(url, headers=merged_headers, params=params, timeout=timeout)
        if response.status_code != 200:
            return None
        return response.json()
    except Exception:
        return None


def is_accessible(url: str, timeout: int = 8) -> bool:
    if not url:
        return False
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        if response.status_code in (401, 403):
            return False
        if 200 <= response.status_code < 400:
            return True
        if response.status_code in (405, 501):
            probe = requests.get(url, timeout=timeout, stream=True)
            return 200 <= probe.status_code < 400
    except Exception:
        return False
    return False


def ffprobe_duration(path: Path) -> float:
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


def infer_category(text: str, source: str = "") -> str:
    words = set(normalize_text(text).split())
    if words & {"dna", "helix", "microscope", "microscopy", "laboratory", "lab", "molecule", "molecules", "protein", "proteins"}:
        return "science"
    best_category = "abstract"
    best_score = 0
    for category, hints in CATEGORY_HINTS.items():
        score = len(words & hints)
        if score > best_score:
            best_score = score
            best_category = category
    if best_score == 0 and source in {"nasa_v", "nasa_svs"}:
        return "space"
    if best_score == 0 and source in {"pexels_v", "pixabay_v", "coverr"}:
        return "people"
    return best_category


def normalize_query_text(text: str) -> str:
    normalized = normalize_text(text)
    for source, target in PHRASE_TRANSLATIONS:
        normalized = normalized.replace(source, target)
    tokens = []
    for token in normalized.split():
        if len(token) < 3 or token in STOPWORDS:
            continue
        tokens.extend(TOKEN_TRANSLATIONS.get(token, token).split())
    unique = []
    seen = set()
    for token in tokens:
        if token in STOPWORDS or len(token) < 3 or token in seen:
            continue
        seen.add(token)
        unique.append(token)
    return " ".join(unique)


def compact_search_query(text: str, max_words: int = 4) -> str:
    generic = {"stock", "footage", "cinematic", "background", "episode", "episodio", "cartela", "transicion"}
    words = []
    seen = set()
    for word in normalize_text(text).split():
        if word in STOPWORDS or word in generic or len(word) < 3 or word in seen:
            continue
        seen.add(word)
        words.append(word)
    return " ".join(words[:max_words])


def build_query_variants(segment: dict, episode_name: str) -> List[str]:
    heading = segment["heading"]
    text = segment["text"]
    heading_terms = normalize_query_text(heading)
    text_terms = normalize_query_text(text)
    variants = []
    if segment["type"] == "heading":
        variants.append(f"{heading_terms} cinematic abstract background")
    else:
        short_terms = " ".join(text_terms.split()[:8])
        variants.append(f"{heading_terms} {short_terms}".strip())
        variants.append(f"{short_terms} stock footage".strip())
    variants.extend(EPISODE_EXPANSIONS.get(episode_name, []))
    cleaned = []
    seen = set()
    for variant in variants:
        compact = compact_search_query(variant)
        if len(compact.split()) < 2:
            continue
        if compact in seen:
            continue
        seen.add(compact)
        cleaned.append(compact)
    return cleaned[:3]


def query_priority(segment: dict) -> float:
    richness = len([word for word in normalize_text(segment["text"]).split() if word not in STOPWORDS and len(word) > 3])
    base = min(3.0, richness / 6.0)
    if segment["type"] == "heading":
        return 2.6 + base
    return base + min(2.0, segment["duration"] / 6.0)


def select_query_jobs(segments: List[dict], episode_name: str, limit: int) -> List[dict]:
    headings = [segment for segment in segments if segment["type"] == "heading"]
    bodies_by_block: Dict[int, List[dict]] = {}
    for segment in segments:
        if segment["type"] != "body":
            continue
        bodies_by_block.setdefault(segment["block_index"], []).append(segment)
    chosen = list(headings)
    for block_segments in bodies_by_block.values():
        block_segments.sort(key=query_priority, reverse=True)
        chosen.extend(block_segments[:2])
    chosen.sort(key=query_priority, reverse=True)

    jobs = []
    seen_queries = set()
    for segment in chosen:
        for variant in build_query_variants(segment, episode_name):
            key = normalize_text(variant)
            if key in seen_queries:
                continue
            seen_queries.add(key)
            jobs.append(
                {
                    "segment_id": segment["segment_id"],
                    "heading": segment["heading"],
                    "type": segment["type"],
                    "query": variant,
                    "priority": round(query_priority(segment), 3),
                }
            )
            if len(jobs) >= limit:
                return jobs
    return jobs


def build_similarity_matrix(segment_queries: List[str], candidate_texts: List[str]):
    all_texts = segment_queries + candidate_texts
    word_vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    char_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1)
    word_matrix = word_vectorizer.fit_transform(all_texts)
    char_matrix = char_vectorizer.fit_transform(all_texts)
    matrix = hstack([word_matrix, char_matrix])
    return matrix[: len(segment_queries)], matrix[len(segment_queries) :]


def build_result(
    source: str,
    query: str,
    title: str,
    description: str,
    download_url: str,
    page_url: str,
    *,
    duration=None,
    width=0,
    height=0,
    quality="HD",
    author="",
    license_short="",
) -> SearchResult:
    inferred = infer_category(f"{title} {description} {query}", source=source)
    return SearchResult(
        source=source,
        title=title[:140],
        description=clean_html(description)[:240],
        download_url=download_url,
        page_url=page_url,
        duration=float(duration) if duration else None,
        width=int(width or 0),
        height=int(height or 0),
        quality=quality,
        author=author[:80],
        license_short=license_short or SOURCE_META.get(source, {}).get("license", ""),
        query=query,
        inferred_category=inferred,
    )


def search_pexels_videos(query: str, per_page: int, keys: Dict[str, str]) -> List[SearchResult]:
    api_key = get_key("PEXELS_API_KEY", keys)
    if not api_key:
        return []
    payload = safe_get_json(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": api_key},
        params={"query": query, "per_page": min(per_page, 40), "page": 1},
    )
    if not payload:
        return []
    results = []
    for video in payload.get("videos", []):
        files = sorted(video.get("video_files", []), key=lambda item: item.get("height", 0), reverse=True)
        if not files:
            continue
        best = files[0]
        if not str(best.get("link", "")).lower().endswith(".mp4"):
            continue
        results.append(
            build_result(
                "pexels_v",
                query,
                f"Pexels #{video['id']}",
                query,
                best.get("link", ""),
                video.get("url", ""),
                duration=video.get("duration"),
                width=best.get("width", 0),
                height=best.get("height", 0),
                quality="4K" if best.get("height", 0) >= 2160 else ("HD" if best.get("height", 0) >= 720 else "SD"),
                author=video.get("user", {}).get("name", ""),
            )
        )
    return results


def search_pixabay_videos(query: str, per_page: int, keys: Dict[str, str]) -> List[SearchResult]:
    api_key = get_key("PIXABAY_API_KEY", keys)
    if not api_key:
        return []
    payload = safe_get_json(
        "https://pixabay.com/api/videos/",
        params={"key": api_key, "q": query, "per_page": min(per_page, 20), "page": 1, "safesearch": "true"},
    )
    if not payload:
        return []
    results = []
    for video in payload.get("hits", []):
        variants = video.get("videos", {})
        best = None
        for label in ["large", "medium", "small", "tiny"]:
            variant = variants.get(label)
            if variant and str(variant.get("url", "")).lower().endswith(".mp4"):
                best = variant
                break
        if not best:
            continue
        results.append(
            build_result(
                "pixabay_v",
                query,
                f"Pixabay #{video['id']}",
                video.get("tags", query),
                best.get("url", ""),
                video.get("pageURL", ""),
                duration=video.get("duration"),
                width=best.get("width", 0),
                height=best.get("height", 0),
                quality="4K" if best.get("height", 0) >= 2160 else ("HD" if best.get("height", 0) >= 720 else "SD"),
                author=video.get("user", ""),
            )
        )
    return results


def search_nasa_videos(query: str, per_page: int, _keys: Dict[str, str]) -> List[SearchResult]:
    payload = safe_get_json(
        "https://images-api.nasa.gov/search",
        params={"q": query, "media_type": "video", "page_size": min(per_page, 20)},
        timeout=20,
    )
    if not payload or "collection" not in payload:
        return []
    results = []
    for item in payload["collection"].get("items", [])[:per_page]:
        data = item.get("data", [{}])[0]
        nasa_id = data.get("nasa_id", "")
        assets = safe_get_json(f"https://images-api.nasa.gov/asset/{nasa_id}", timeout=12)
        if not assets or "collection" not in assets:
            continue
        mp4s = [asset.get("href", "") for asset in assets["collection"].get("items", []) if str(asset.get("href", "")).lower().endswith(".mp4")]
        if not mp4s:
            continue
        download_url = next((url for url in mp4s if "~orig" in url.lower()), mp4s[0])
        results.append(
            build_result(
                "nasa_v",
                query,
                data.get("title", "NASA Video"),
                data.get("description", ""),
                download_url,
                f"https://images.nasa.gov/details/{nasa_id}",
                author="NASA",
                quality="HD",
            )
        )
    return results


def search_nasa_svs(query: str, per_page: int, _keys: Dict[str, str]) -> List[SearchResult]:
    results = []
    for variant in [f"{query} visualization", f"{query} simulation", query]:
        payload = safe_get_json(
            "https://images-api.nasa.gov/search",
            params={"q": variant, "media_type": "video", "page_size": min(per_page, 15), "center": "GSFC"},
            timeout=20,
        )
        if not payload or "collection" not in payload:
            continue
        for item in payload["collection"].get("items", [])[:per_page]:
            data = item.get("data", [{}])[0]
            nasa_id = data.get("nasa_id", "")
            assets = safe_get_json(f"https://images-api.nasa.gov/asset/{nasa_id}", timeout=12)
            if not assets or "collection" not in assets:
                continue
            mp4s = [asset.get("href", "") for asset in assets["collection"].get("items", []) if str(asset.get("href", "")).lower().endswith(".mp4")]
            if not mp4s:
                continue
            results.append(
                build_result(
                    "nasa_svs",
                    query,
                    data.get("title", "NASA SVS"),
                    data.get("description", ""),
                    mp4s[0],
                    f"https://images.nasa.gov/details/{nasa_id}",
                    author="NASA GSFC SVS",
                    quality="HD",
                )
            )
        if results:
            break
    unique = {}
    for result in results:
        unique.setdefault(result.download_url, result)
    return list(unique.values())[:per_page]


def search_archive_videos(query: str, per_page: int, _keys: Dict[str, str]) -> List[SearchResult]:
    payload = safe_get_json(
        "https://archive.org/advancedsearch.php",
        params={
            "q": f"({query}) AND mediatype:movies AND (licenseurl:(*publicdomain* OR *cc0*))",
            "fl[]": ["identifier", "title", "description"],
            "rows": min(per_page, 15),
            "page": 1,
            "output": "json",
        },
        timeout=18,
    )
    if not payload or "response" not in payload:
        return []
    results = []
    for doc in payload["response"].get("docs", []):
        identifier = doc.get("identifier", "")
        metadata = safe_get_json(f"https://archive.org/metadata/{identifier}/files", timeout=12)
        if not metadata or "result" not in metadata:
            continue
        mp4s = sorted(
            [item for item in metadata["result"] if str(item.get("name", "")).lower().endswith(".mp4")],
            key=lambda item: int(item.get("size", 0) or 0),
            reverse=True,
        )
        if not mp4s:
            continue
        download_url = f"https://archive.org/download/{identifier}/{mp4s[0]['name']}"
        if not is_accessible(download_url):
            continue
        results.append(
            build_result(
                "archive_v",
                query,
                str(doc.get("title", "Internet Archive Video")),
                str(doc.get("description", "")),
                download_url,
                f"https://archive.org/details/{identifier}",
                author="Internet Archive",
                quality="HD",
            )
        )
    return results


def search_coverr_videos(query: str, per_page: int, _keys: Dict[str, str]) -> List[SearchResult]:
    for endpoint in [
        f"https://api.coverr.co/videos?query={quote(query)}&page_size={min(per_page, 10)}",
        f"https://coverr.co/api/search/{quote(query)}",
    ]:
        payload = safe_get_json(endpoint, timeout=12)
        if not isinstance(payload, dict):
            continue
        hits = payload.get("videos", payload.get("hits", payload.get("results", [])))
        if not isinstance(hits, list):
            continue
        results = []
        for video in hits[:per_page]:
            url = video.get("video_url", "") or video.get("urls", {}).get("mp4", "")
            if not str(url).lower().endswith(".mp4"):
                continue
            results.append(
                build_result(
                    "coverr",
                    query,
                    video.get("title", video.get("name", "Coverr Video")),
                    video.get("description", ""),
                    url,
                    video.get("url", "https://coverr.co"),
                    duration=video.get("duration"),
                    author="Coverr",
                )
            )
        if results:
            return results
    return []


def search_wikimedia_videos(query: str, per_page: int, _keys: Dict[str, str]) -> List[SearchResult]:
    payload = safe_get_json(
        "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"{query} filetype:video",
            "gsrnamespace": "6",
            "gsrlimit": min(per_page, 12),
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": 640,
        },
        timeout=18,
    )
    if not payload or "query" not in payload:
        return []
    results = []
    safe_licenses = ["cc0", "public domain", "cc-by-4", "cc-by-3", "cc-by-2", "cc-by-sa", "pd"]
    for page in payload["query"].get("pages", {}).values():
        info = page.get("imageinfo", [{}])[0]
        if "video" not in info.get("mime", "") and "ogg" not in info.get("mime", "") and "webm" not in info.get("mime", ""):
            continue
        metadata = info.get("extmetadata", {})
        license_short = clean_html(metadata.get("LicenseShortName", {}).get("value", ""))
        if not any(item in license_short.lower() for item in safe_licenses):
            continue
        url = info.get("url", "")
        title = page.get("title", "").replace("File:", "")
        results.append(
            build_result(
                "wikimedia_v",
                query,
                title,
                metadata.get("ImageDescription", {}).get("value", ""),
                url,
                info.get("descriptionurl", ""),
                width=info.get("width", 0),
                height=info.get("height", 0),
                quality="HD" if info.get("height", 0) >= 720 else "SD",
                author=clean_html(metadata.get("Artist", {}).get("value", "")),
                license_short=license_short,
            )
        )
    return results


SEARCH_FUNCTIONS = {
    "pexels_v": search_pexels_videos,
    "pixabay_v": search_pixabay_videos,
    "nasa_v": search_nasa_videos,
    "nasa_svs": search_nasa_svs,
    "archive_v": search_archive_videos,
    "coverr": search_coverr_videos,
    "wikimedia_v": search_wikimedia_videos,
}


def execute_search_jobs(query_jobs: List[dict], sources: List[str], per_source: int, keys: Dict[str, str]) -> Tuple[List[SearchResult], Dict[str, int]]:
    counts = {source: 0 for source in sources}
    tasks = []
    for job in query_jobs:
        for source in sources:
            tasks.append((source, job["query"]))
    results: List[SearchResult] = []
    with ThreadPoolExecutor(max_workers=min(12, max(1, len(tasks)))) as pool:
        future_map = {
            pool.submit(SEARCH_FUNCTIONS[source], query, per_source, keys): (source, query)
            for source, query in tasks
            if source in SEARCH_FUNCTIONS
        }
        for future in as_completed(future_map):
            source, _query = future_map[future]
            try:
                batch = future.result()
            except Exception:
                batch = []
            counts[source] += len(batch)
            results.extend(batch)
    return results, counts


def score_candidates(results: List[SearchResult], segments: List[dict]) -> List[dict]:
    if not results:
        return []
    segment_queries = [normalize_text(segment["query"]) for segment in segments]
    candidate_texts = [result.search_text for result in results]
    segment_matrix, candidate_matrix = build_similarity_matrix(segment_queries, candidate_texts)
    similarities = cosine_similarity(candidate_matrix, segment_matrix)

    scored = []
    for index, result in enumerate(results):
        row = similarities[index]
        top_matches = sorted((float(score) for score in row), reverse=True)[:3]
        max_match = top_matches[0] if top_matches else 0.0
        mean_match = sum(top_matches) / len(top_matches) if top_matches else 0.0
        source_bonus = SOURCE_META.get(result.source, {}).get("priority", 0.0)
        quality_bonus = 0.05 if result.height >= 1080 else (0.03 if result.height >= 720 else 0.0)
        duration_bonus = 0.03 if result.duration and result.duration >= 4.0 else 0.0
        abstract_bonus = 0.025 if result.inferred_category in {"abstract", "double-exposure", "light", "background"} else 0.0
        score = max_match * 0.72 + mean_match * 0.18 + source_bonus + quality_bonus + duration_bonus + abstract_bonus
        scored.append(
            {
                "score": round(score, 5),
                "max_match": round(max_match, 5),
                "mean_match": round(mean_match, 5),
                "result": result,
            }
        )
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored


def select_download_pool(scored: List[dict], clip_target: int, allow_non_mp4: bool) -> List[dict]:
    selected = []
    used_urls = set()
    category_counts: Dict[str, int] = {}
    source_counts: Dict[str, int] = {}
    primary_pass = True
    min_primary_score = 0.18
    index = 0
    while index < len(scored):
        item = scored[index]
        index += 1
        result = item["result"]
        if result.download_url in used_urls:
            continue
        if not allow_non_mp4 and result.source not in MP4_SOURCES and not str(result.download_url).lower().endswith(".mp4"):
            continue
        if not result.download_url.startswith("http"):
            continue
        if primary_pass and item["score"] < min_primary_score:
            if len(selected) >= max(8, clip_target // 3):
                primary_pass = False
            else:
                continue
        category_count = category_counts.get(result.inferred_category, 0)
        source_count = source_counts.get(result.source, 0)
        if category_count >= max(6, math.ceil(clip_target / 4)):
            continue
        if source_count >= max(10, math.ceil(clip_target * 0.75)):
            continue
        selected.append(item)
        used_urls.add(result.download_url)
        category_counts[result.inferred_category] = category_count + 1
        source_counts[result.source] = source_count + 1
        if len(selected) >= clip_target:
            break
    return selected


def download_result(result: SearchResult, destination: Path) -> ClipCandidate:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".part")
    headers = {"User-Agent": UA}
    last_error = None
    for attempt in range(4):
        try:
            with requests.get(result.download_url, headers=headers, timeout=120, stream=True) as response:
                response.raise_for_status()
                with tmp.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            handle.write(chunk)
            if destination.exists():
                destination.unlink()
            tmp.replace(destination)
            duration = ffprobe_duration(destination)
            return ClipCandidate(
                file_name=destination.name,
                file_path=str(destination),
                category=result.inferred_category,
                title=result.title,
                page_url=result.page_url,
                mp4_url=result.download_url,
                duration=duration,
            )
        except Exception as exc:
            last_error = exc
            if tmp.exists():
                tmp.unlink()
            time.sleep(2 + attempt * 2)
    raise RuntimeError(f"download failed for {result.download_url}: {last_error}") from last_error


def write_stock_manifest(episode_dir: Path, selected: List[dict], downloaded: List[ClipCandidate]):
    stock_root = resolve_stock_root(episode_dir)
    stock_root.mkdir(parents=True, exist_ok=True)
    manifest_path = stock_root / "stock-sources-sciclip.md"
    rows = [
        f"# Fuentes de video stock online - {episode_dir.name}",
        "",
        "- Motor: SciClip + puente semántico local.",
        "- Objetivo: descargar un pool más semántico y reutilizable antes del conformado en DaVinci Resolve.",
        "- Nota: este manifiesto convive con `semantic-shot-plan.json`; el plan semántico final usa las rutas reales descargadas.",
        "",
        "| Archivo | Fuente | Categoria | Resolucion | Titulo | Pagina origen | MP4 | Score | Query | Licencia |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    candidates_by_file = {candidate.file_name: candidate for candidate in downloaded}
    for index, item in enumerate(selected, start=1):
        result = item["result"]
        file_name = f"{index:03}.mp4"
        if file_name not in candidates_by_file:
            continue
        title = result.title.replace("|", "/")
        query = result.query.replace("|", "/")
        rows.append(
            f"| {file_name} | {SOURCE_META.get(result.source, {}).get('name', result.source)} | {result.inferred_category} | {result.resolution_label} | {title} | {result.page_url} | {result.download_url} | {item['score']:.4f} | {query} | {result.license_short} |"
        )
    manifest_path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_search_report(episode_dir: Path, query_jobs: List[dict], counts: Dict[str, int], scored: List[dict], selected: List[dict], downloaded: List[ClipCandidate]):
    stock_root = resolve_stock_root(episode_dir)
    stock_root.mkdir(parents=True, exist_ok=True)
    report_path = stock_root / "stock-search-report.json"
    report = {
        "episode": episode_dir.name,
        "queries": query_jobs,
        "source_result_counts": counts,
        "selected_candidates": [
            {
                "file_name": clip.file_name,
                "file_path": clip.file_path,
                "category": clip.category,
                "title": clip.title,
                "page_url": clip.page_url,
                "download_url": clip.mp4_url,
                "duration": clip.duration,
            }
            for clip in downloaded
        ],
        "top_scored_candidates": [
            {
                "score": item["score"],
                "max_match": item["max_match"],
                "mean_match": item["mean_match"],
                "source": item["result"].source,
                "title": item["result"].title,
                "query": item["result"].query,
                "download_url": item["result"].download_url,
                "page_url": item["result"].page_url,
                "category": item["result"].inferred_category,
            }
            for item in scored[:60]
        ],
        "download_pool_size": len(selected),
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def process_episode(
    episode_name: str,
    *,
    sources: List[str],
    keys: Dict[str, str],
    per_source: int,
    query_limit: int,
    clip_target: int,
    dry_run: bool,
    allow_non_mp4: bool,
):
    episode_dir = resolve_episode_dir(episode_name)
    segments = create_segments(episode_dir, episode_name)
    query_jobs = select_query_jobs(segments, episode_name, query_limit)
    results, counts = execute_search_jobs(query_jobs, sources, per_source, keys)
    deduped = {}
    for result in results:
        deduped.setdefault(result.download_url, result)
    scored = score_candidates(list(deduped.values()), segments)
    selected = select_download_pool(scored, clip_target, allow_non_mp4)

    if dry_run:
        write_search_report(episode_dir, query_jobs, counts, scored, selected, [])
        return {
            "episode": episode_name,
            "query_count": len(query_jobs),
            "raw_results": len(results),
            "deduped_results": len(deduped),
            "selected": len(selected),
            "planned": False,
        }

    if not selected:
        raise RuntimeError(f"{episode_name}: no se encontraron candidatos descargables")

    stock_dir = resolve_stock_root(episode_dir) / "sciclip-stock"
    stock_dir.mkdir(parents=True, exist_ok=True)
    if stock_dir.exists():
        for old_file in stock_dir.glob("*.mp4"):
            old_file.unlink()
    downloaded: List[ClipCandidate] = []
    for index, item in enumerate(selected, start=1):
        destination = stock_dir / f"{index:03}.mp4"
        downloaded.append(download_result(item["result"], destination))

    planned = rank_segments(segments, downloaded, episode_name)
    write_outputs(episode_dir, episode_name, planned)
    write_stock_manifest(episode_dir, selected, downloaded)
    write_search_report(episode_dir, query_jobs, counts, scored, selected, downloaded)

    return {
        "episode": episode_name,
        "query_count": len(query_jobs),
        "raw_results": len(results),
        "deduped_results": len(deduped),
        "selected": len(downloaded),
        "planned": True,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Puente semántico stock online -> DaVinci Resolve.")
    parser.add_argument("--episode", choices=EPISODES, help="Procesa un episodio concreto.")
    parser.add_argument("--all", action="store_true", help="Procesa toda la serie.")
    parser.add_argument("--sources", default=",".join(DEFAULT_SOURCES), help="Fuentes separadas por comas.")
    parser.add_argument("--per-source", type=int, default=6, help="Resultados por fuente y consulta.")
    parser.add_argument("--query-limit", type=int, default=24, help="Número máximo de consultas semánticas compactas.")
    parser.add_argument("--clips", type=int, default=36, help="Tamaño objetivo del pool descargado.")
    parser.add_argument("--dry-run", action="store_true", help="Busca y puntúa sin descargar ni replanificar.")
    parser.add_argument("--allow-non-mp4", action="store_true", help="Permite seleccionar fuentes no MP4.")
    args = parser.parse_args()
    if not args.episode and not args.all:
        parser.error("Usa --episode o --all.")
    return args


def main():
    args = parse_args()
    secrets = load_secrets()
    sources = [source.strip() for source in args.sources.split(",") if source.strip()]
    episodes = EPISODES if args.all else [args.episode]
    summary = []
    for episode_name in episodes:
        result = process_episode(
            episode_name,
            sources=sources,
            keys=secrets,
            per_source=args.per_source,
            query_limit=args.query_limit,
            clip_target=args.clips,
            dry_run=args.dry_run,
            allow_non_mp4=args.allow_non_mp4,
        )
        summary.append(result)
        print(
            f"{episode_name}|QUERIES={result['query_count']}|RAW={result['raw_results']}|DEDUPED={result['deduped_results']}|SELECTED={result['selected']}|PLANNED={result['planned']}"
        )
    if not summary:
        sys.exit(1)


if __name__ == "__main__":
    main()
