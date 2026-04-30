import argparse
import asyncio
import csv
import json
from pathlib import Path

import edge_tts


PREFERRED_MULTILINGUAL = {
    "male": [
        "es-ES-TristanMultilingualNeural",
        "en-US-AndrewMultilingualNeural",
        "en-US-BrianMultilingualNeural",
        "en-AU-WilliamMultilingualNeural",
    ],
    "female": [
        "es-ES-XimenaMultilingualNeural",
        "es-CL-IsidoraMultilingualNeural",
        "es-ES-ArabellaMultilingualNeural",
        "es-ES-XimenaNeural",
        "en-US-AvaMultilingualNeural",
        "en-US-EmmaMultilingualNeural",
        "fr-FR-VivienneMultilingualNeural",
    ],
}

PREFERRED_NAME_HINTS = {
    "male": ["tristan"],
    "female": ["ximena", "isidora", "arabella"],
}


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "ShortName",
        "FriendlyName",
        "Locale",
        "Gender",
        "Status",
        "IsMultilingual",
        "SupportsSpanishRuntime",
        "VoicePersonalities",
        "ContentCategories",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def enrich_voice(voice: dict) -> dict:
    tag = voice.get("VoiceTag", {})
    short_name = voice.get("ShortName", "")
    is_multilingual = "Multilingual" in short_name or "multilingual" in json.dumps(voice, ensure_ascii=False)
    supports_spanish = short_name in set(PREFERRED_MULTILINGUAL["male"] + PREFERRED_MULTILINGUAL["female"]) or str(
        voice.get("Locale", "")
    ).startswith("es-")
    enriched = dict(voice)
    enriched["IsMultilingual"] = bool(is_multilingual)
    enriched["SupportsSpanishRuntime"] = bool(supports_spanish)
    enriched["VoicePersonalities"] = tag.get("VoicePersonalities", [])
    enriched["ContentCategories"] = tag.get("ContentCategories", [])
    return enriched


def role_entry(voice: dict) -> dict:
    return {
        "ShortName": voice.get("ShortName", ""),
        "FriendlyName": voice.get("FriendlyName", ""),
        "Locale": voice.get("Locale", ""),
        "Gender": voice.get("Gender", ""),
        "IsMultilingual": voice.get("IsMultilingual", False),
        "SupportsSpanishRuntime": voice.get("SupportsSpanishRuntime", False),
    }


def preferred_hint_matches(voices_by_name: dict, gender: str) -> list[dict]:
    selected = []
    hints = PREFERRED_NAME_HINTS[gender]
    for voice in voices_by_name.values():
        haystack = json.dumps(
            {
                "ShortName": voice.get("ShortName", ""),
                "FriendlyName": voice.get("FriendlyName", ""),
                "Name": voice.get("Name", ""),
            },
            ensure_ascii=False,
        ).lower()
        if voice.get("Gender", "").lower() == gender and any(hint in haystack for hint in hints):
            selected.append(role_entry(voice))
    selected.sort(key=lambda voice: (0 if voice.get("IsMultilingual") else 1, voice.get("ShortName", "")))
    return selected


def role_candidates(voices_by_name: dict, preferred_names: list[str], gender: str) -> list[dict]:
    selected = []
    used = set()
    for option in preferred_hint_matches(voices_by_name, gender):
        short_name = option["ShortName"]
        if short_name not in used:
            selected.append(option)
            used.add(short_name)

    for short_name in preferred_names:
        voice = voices_by_name.get(short_name)
        if voice:
            selected.append(role_entry(voice))
            used.add(short_name)

    fallback = [
        voice
        for voice in voices_by_name.values()
        if voice.get("Gender", "").lower() == gender
        and voice.get("SupportsSpanishRuntime")
        and voice.get("ShortName") not in used
    ]
    fallback.sort(
        key=lambda voice: (
            0 if voice.get("IsMultilingual") else 1,
            0 if str(voice.get("Locale", "")).startswith("es-") else 1,
            str(voice.get("FriendlyName", "")),
        )
    )
    selected.extend(role_entry(voice) for voice in fallback)
    return selected


def write_role_map(path: Path, voices_by_name: dict):
    role_map = {
        "available_count": len(voices_by_name),
        "roles": {
            "multilingual_male_spanish": role_candidates(voices_by_name, PREFERRED_MULTILINGUAL["male"], "male"),
            "multilingual_female_spanish": role_candidates(voices_by_name, PREFERRED_MULTILINGUAL["female"], "female"),
            "narration_male_primary": role_candidates(voices_by_name, PREFERRED_MULTILINGUAL["male"], "male"),
            "narration_female_primary": role_candidates(voices_by_name, PREFERRED_MULTILINGUAL["female"], "female"),
            "title_cards_female": role_candidates(voices_by_name, PREFERRED_MULTILINGUAL["female"], "female"),
            "cta_female": role_candidates(voices_by_name, PREFERRED_MULTILINGUAL["female"], "female"),
            "cta_male": role_candidates(voices_by_name, PREFERRED_MULTILINGUAL["male"], "male"),
            "institutional_lower_thirds": role_candidates(voices_by_name, PREFERRED_MULTILINGUAL["male"], "male")
            + role_candidates(voices_by_name, PREFERRED_MULTILINGUAL["female"], "female"),
            "experimental_alt_female": role_candidates(voices_by_name, ["fr-FR-VivienneMultilingualNeural"], "female"),
            "experimental_alt_male": role_candidates(voices_by_name, ["en-AU-WilliamMultilingualNeural"], "male"),
        },
    }
    write_json(path, role_map)


async def main_async(root: Path, project: str | None):
    voices = await edge_tts.list_voices()
    allowed = set(PREFERRED_MULTILINGUAL["male"] + PREFERRED_MULTILINGUAL["female"])
    filtered = [
        enrich_voice(voice)
        for voice in voices
        if str(voice.get("Locale", "")).startswith("es-") or voice.get("ShortName", "") in allowed
    ]
    filtered.sort(
        key=lambda voice: (
            0 if voice.get("IsMultilingual") else 1,
            0 if voice.get("SupportsSpanishRuntime") else 1,
            str(voice.get("Locale", "")),
            str(voice.get("Gender", "")),
            str(voice.get("ShortName", "")),
        )
    )

    app_assets = root / "APP TO DaVinci" / "assets"
    json_path = app_assets / "microsoft_spanish_voices.json"
    csv_path = app_assets / "microsoft_spanish_voices.csv"
    roles_path = app_assets / "microsoft_spanish_voice_roles.json"

    write_json(json_path, filtered)
    write_csv(
        csv_path,
        [
            {
                "ShortName": voice.get("ShortName", ""),
                "FriendlyName": voice.get("FriendlyName", ""),
                "Locale": voice.get("Locale", ""),
                "Gender": voice.get("Gender", ""),
                "Status": voice.get("Status", ""),
                "IsMultilingual": voice.get("IsMultilingual", False),
                "SupportsSpanishRuntime": voice.get("SupportsSpanishRuntime", False),
                "VoicePersonalities": ", ".join(voice.get("VoicePersonalities", [])),
                "ContentCategories": ", ".join(voice.get("ContentCategories", [])),
            }
            for voice in filtered
        ],
    )
    write_role_map(roles_path, {voice["ShortName"]: voice for voice in filtered})

    if project:
        project_voice_dir = root / "FINALS PROJECTS" / project / "03-shared-assets" / "voice-catalog"
        write_json(project_voice_dir / "microsoft_spanish_voices.json", filtered)
        write_csv(
            project_voice_dir / "microsoft_spanish_voices.csv",
            [
                {
                    "ShortName": voice.get("ShortName", ""),
                    "FriendlyName": voice.get("FriendlyName", ""),
                    "Locale": voice.get("Locale", ""),
                    "Gender": voice.get("Gender", ""),
                    "Status": voice.get("Status", ""),
                    "IsMultilingual": voice.get("IsMultilingual", False),
                    "SupportsSpanishRuntime": voice.get("SupportsSpanishRuntime", False),
                    "VoicePersonalities": ", ".join(voice.get("VoicePersonalities", [])),
                    "ContentCategories": ", ".join(voice.get("ContentCategories", [])),
                }
                for voice in filtered
            ],
        )
        write_role_map(project_voice_dir / "microsoft_spanish_voice_roles.json", {voice["ShortName"]: voice for voice in filtered})

    preferred = {
        "male": PREFERRED_MULTILINGUAL["male"][0],
        "female": PREFERRED_MULTILINGUAL["female"][0],
    }
    print(f"OK|VOICE_COUNT={len(filtered)}|MALE={preferred['male']}|FEMALE={preferred['female']}")


def main():
    parser = argparse.ArgumentParser(description="Refresca el catálogo de voces españolas y multilingual usadas por el runtime.")
    parser.add_argument("--root", type=Path, required=True, help="Raíz DaVinci Projects")
    parser.add_argument("--project", help="Proyecto actual para copiar también el catálogo a 03-shared-assets\\voice-catalog")
    args = parser.parse_args()
    asyncio.run(main_async(args.root.resolve(), args.project))


if __name__ == "__main__":
    main()
