import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


RESOLUTION_MAP = {
    "1080p Full HD": {"width": 1920, "height": 1080, "fps": 24},
    "1440p": {"width": 2560, "height": 1440, "fps": 24},
    "4K UHD": {"width": 3840, "height": 2160, "fps": 24},
}

DELIVERY_CODEC_MAP = {
    "MP4 H.264": {"container": "mp4", "video_codec": "H.264", "audio_codec": "AAC"},
    "MP4 H.265": {"container": "mp4", "video_codec": "H.265", "audio_codec": "AAC"},
    "MOV master de alta calidad": {"container": "mov", "video_codec": "ProRes", "audio_codec": "PCM"},
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def choose_voice(voice_roles: dict, role_key: str, requested_label: str) -> dict:
    options = voice_roles["roles"].get(role_key, [])
    if not options:
        raise SystemExit(f"No hay opciones de voz para el rol {role_key}")

    requested = requested_label.lower()
    prefer_male = requested.startswith("male")
    prefer_female = requested.startswith("female")
    if prefer_male:
        male_options = [option for option in options if option.get("Gender", "").lower() == "male"]
        if male_options:
            return male_options[0]
    if prefer_female:
        female_options = [option for option in options if option.get("Gender", "").lower() == "female"]
        if female_options:
            return female_options[0]
    return options[0]


def build_voice_plan(brief: dict, voice_roles: dict) -> dict:
    roles = brief["language_and_voices"]["roles"]
    return {
        "strategy": brief["language_and_voices"]["voice_strategy"],
        "render_languages": brief["language_and_voices"]["render_languages"],
        "subtitle_languages": brief["language_and_voices"]["subtitle_languages"],
        "selected_voices": {
            "narration_main": choose_voice(voice_roles, "narration_male_primary", roles["narration_main"]),
            "titles_cards": choose_voice(voice_roles, "title_cards_female", roles["titles_cards"]),
            "cta": choose_voice(voice_roles, "cta_male", roles["cta"]),
            "institutional": choose_voice(voice_roles, "institutional_lower_thirds", roles["institutional"]),
        },
    }


def build_resolve_render_settings(brief: dict, template: dict) -> dict:
    resolution_name = brief["davinci_finish"]["resolution"]
    resolution = RESOLUTION_MAP.get(resolution_name, RESOLUTION_MAP["1080p Full HD"])
    codec = DELIVERY_CODEC_MAP.get(brief["davinci_finish"]["delivery_codec"], DELIVERY_CODEC_MAP["MP4 H.264"])
    return {
        "project_name": brief["project_identity"]["resolve_project_name"],
        "resolution_name": resolution_name,
        "resolution": resolution,
        "delivery": {
            **codec,
            "target": brief["davinci_finish"]["delivery_target"],
        },
        "timeline_architecture": template["timeline_architecture"],
        "color_direction": {
            "look": brief["davinci_finish"]["color_look"],
            "contrast": brief["davinci_finish"]["contrast_profile"],
            "texture": brief["davinci_finish"]["texture_profile"],
        },
    }


def build_visual_style(brief: dict, template: dict) -> dict:
    opening_flow = json.loads(json.dumps(template["opening_flow"]))
    for segment in opening_flow.get("sequence", []):
        if segment.get("segment") == "subscribe-bumper":
            segment["voice_role"] = "cta"
        elif segment.get("segment") == "episode-intro":
            segment["voice_role"] = "titles_cards"

    return {
        "channel_identity": template["channel_identity"],
        "branding_assets": template["official_assets_usage"],
        "opening_flow": opening_flow,
        "motion_graphics_system": template["motion_graphics_system"],
        "brief_visual_direction": brief["visual_direction"],
        "brief_music_direction": brief["music_and_sound"],
        "effective_voice_roles": {
            "subscribe_bumper": "cta",
            "episode_intro": "titles_cards",
            "narration_main": "narration_main",
            "institutional_lower_thirds": "institutional",
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Convierte production-brief.json en configuración ejecutable del proyecto.")
    parser.add_argument("--root", type=Path, required=True, help="Raíz DaVinci Projects")
    parser.add_argument("--project", required=True, help="Nombre de carpeta del proyecto dentro de FINALS PROJECTS")
    args = parser.parse_args()

    root_dir = args.root.resolve()
    app_dir = root_dir / "APP TO DaVinci"
    project_dir = root_dir / "FINALS PROJECTS" / args.project
    admin_dir = project_dir / "00-admin"
    shared_dir = project_dir / "03-shared-assets"
    resolve_dir = project_dir / "05-resolve"

    brief = load_json(admin_dir / "production-brief.json")
    if not brief["implementation_state"]["ready_for_render_plan"]:
        raise SystemExit("El production-brief todavía no está listo para convertirlo en runtime.")

    project_manifest = load_json(admin_dir / "project-manifest.json")
    voice_roles = load_json(app_dir / "assets" / "microsoft_spanish_voice_roles.json")
    voice_catalog = load_json(app_dir / "assets" / "microsoft_spanish_voices.json")
    channel_template = load_json(app_dir / "assets" / "resolve_channel_premium_template.json")

    voice_plan = build_voice_plan(brief, voice_roles)
    resolve_render = build_resolve_render_settings(brief, channel_template)
    visual_style = build_visual_style(brief, channel_template)

    runtime = {
        "project_identity": brief["project_identity"],
        "project_manifest_reference": str(admin_dir / "project-manifest.json"),
        "production_brief_reference": str(admin_dir / "production-brief.json"),
        "voice_plan_reference": str(shared_dir / "voice-plan.json"),
        "resolve_render_reference": str(resolve_dir / "resolve-render-settings.json"),
        "visual_style_reference": str(resolve_dir / "resolve-style-guide.json"),
        "episode_count": project_manifest["episode_count_seeded"],
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }

    write_json(shared_dir / "voice-plan.json", voice_plan)
    write_json(shared_dir / "voice-catalog" / "microsoft_spanish_voices.json", voice_catalog)
    write_json(shared_dir / "voice-catalog" / "microsoft_spanish_voice_roles.json", voice_roles)
    write_csv(
        shared_dir / "voice-catalog" / "microsoft_spanish_voices.csv",
        [
            {
                "ShortName": voice.get("ShortName", ""),
                "FriendlyName": voice.get("FriendlyName", ""),
                "Locale": voice.get("Locale", ""),
                "Gender": voice.get("Gender", ""),
                "Status": voice.get("Status", ""),
                "IsMultilingual": voice.get("IsMultilingual", False),
                "SupportsSpanishRuntime": voice.get("SupportsSpanishRuntime", False),
            }
            for voice in voice_catalog
        ],
        ["ShortName", "FriendlyName", "Locale", "Gender", "Status", "IsMultilingual", "SupportsSpanishRuntime"],
    )
    write_json(resolve_dir / "resolve-render-settings.json", resolve_render)
    write_json(resolve_dir / "resolve-style-guide.json", visual_style)
    write_json(admin_dir / "production-runtime.json", runtime)

    brief["implementation_state"]["runtime_generated"] = True
    brief["implementation_state"]["runtime_generated_utc"] = runtime["generated_utc"]
    brief["implementation_state"]["runtime_files"] = {
        "voice_plan": str(shared_dir / "voice-plan.json"),
        "resolve_render_settings": str(resolve_dir / "resolve-render-settings.json"),
        "resolve_style_guide": str(resolve_dir / "resolve-style-guide.json"),
        "production_runtime": str(admin_dir / "production-runtime.json"),
    }
    brief["implementation_state"]["last_updated_utc"] = runtime["generated_utc"]
    write_json(admin_dir / "production-brief.json", brief)

    print(
        f"OK|PROJECT={args.project}|VOICE_PLAN={shared_dir / 'voice-plan.json'}|RENDER={resolve_dir / 'resolve-render-settings.json'}"
    )


if __name__ == "__main__":
    main()
