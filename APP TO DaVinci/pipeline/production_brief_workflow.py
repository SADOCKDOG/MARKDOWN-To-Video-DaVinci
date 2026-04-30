import json
from datetime import datetime, timezone
from pathlib import Path


QUESTION_FLOW = [
    {
        "id": "render-languages",
        "block": "Idiomas y voces",
        "prompt": "Que idiomas deben renderizarse para el proyecto.",
        "field_path": ["language_and_voices", "render_languages"],
        "choices": ["es", "es,en"],
    },
    {
        "id": "subtitle-languages",
        "block": "Idiomas y voces",
        "prompt": "Que idiomas deben incluirse como subtitulos.",
        "field_path": ["language_and_voices", "subtitle_languages"],
        "choices": ["es", "es,en", "ninguno"],
    },
    {
        "id": "voice-strategy",
        "block": "Idiomas y voces",
        "prompt": "Que estrategia de voces debe usarse en el runtime.",
        "field_path": ["language_and_voices", "voice_strategy"],
        "choices": ["multilingual-edge", "spanish-native-edge"],
    },
    {
        "id": "voice-narration-main",
        "block": "Idiomas y voces",
        "prompt": "Que perfil de voz debe narrar el cuerpo principal.",
        "field_path": ["language_and_voices", "roles", "narration_main"],
        "choices": ["male-multilingual", "male-neutral"],
    },
    {
        "id": "voice-titles-cards",
        "block": "Idiomas y voces",
        "prompt": "Que perfil de voz debe usarse para titulos y cartelas.",
        "field_path": ["language_and_voices", "roles", "titles_cards"],
        "choices": ["female-clear", "female-neutral"],
    },
    {
        "id": "voice-cta",
        "block": "Idiomas y voces",
        "prompt": "Que perfil de voz debe usarse para CTA y bumper.",
        "field_path": ["language_and_voices", "roles", "cta"],
        "choices": ["male-cta", "female-cta"],
    },
    {
        "id": "voice-institutional",
        "block": "Idiomas y voces",
        "prompt": "Que perfil de voz debe usarse para elementos institucionales.",
        "field_path": ["language_and_voices", "roles", "institutional"],
        "choices": ["female-institutional", "male-institutional"],
    },
    {
        "id": "background-music",
        "block": "Musica y atmosfera",
        "prompt": "Como debe resolverse la musica de fondo.",
        "field_path": ["music_and_sound", "background_music"],
        "choices": ["ambient-score", "hybrid-cinematic", "minimal-pulse"],
    },
    {
        "id": "music-style",
        "block": "Musica y atmosfera",
        "prompt": "Que estilo musical debe dominar el proyecto.",
        "field_path": ["music_and_sound", "music_style"],
        "choices": ["documental-cientifico", "sci-fi-reflexivo", "tecnologico-premium"],
    },
    {
        "id": "music-intensity",
        "block": "Musica y atmosfera",
        "prompt": "Que intensidad musical debe mantenerse durante el montaje.",
        "field_path": ["music_and_sound", "music_intensity"],
        "choices": ["baja y elegante", "media y envolvente", "alta y protagonista", "variable segun momento"],
    },
    {
        "id": "sound-design-notes",
        "block": "Musica y atmosfera",
        "prompt": "Que notas de atmosfera o sound design deben respetarse.",
        "field_path": ["music_and_sound", "sound_design_notes"],
        "choices": ["diseno sonoro sutil con texturas espaciales", "diseno sonoro limpio con acentos tecnologicos"],
    },
    {
        "id": "cinematic-style",
        "block": "Estilo cinematografico y textos",
        "prompt": "Que estilo cinematografico debe guiar el proyecto.",
        "field_path": ["visual_direction", "cinematic_style"],
        "choices": ["documental-premium", "sci-fi-editorial", "ensayo-visual-cinematico"],
    },
    {
        "id": "text-style",
        "block": "Estilo cinematografico y textos",
        "prompt": "Que estilo de textos en pantalla debe aplicarse.",
        "field_path": ["visual_direction", "text_style"],
        "choices": ["sobrio-premium", "cientifico-minimalista", "futurista-legible"],
    },
    {
        "id": "transition-style",
        "block": "Transiciones, FX y color",
        "prompt": "Que estilo de transiciones debe dominar la pieza.",
        "field_path": ["visual_direction", "transition_style"],
        "choices": ["cortes-limpios-con-fades", "transiciones-cinematicas-suaves", "digitales-sutiles"],
    },
    {
        "id": "fx-density",
        "block": "Transiciones, FX y color",
        "prompt": "Que densidad de efectos debe permitirse.",
        "field_path": ["visual_direction", "fx_density"],
        "choices": ["baja", "media", "media-controlada"],
    },
    {
        "id": "futurism-level",
        "block": "Transiciones, FX y color",
        "prompt": "Cuanto futurismo visual debe respirarse en el proyecto.",
        "field_path": ["visual_direction", "futurism_level"],
        "choices": ["sutil", "medio", "alto-controlado"],
    },
    {
        "id": "color-look",
        "block": "Transiciones, FX y color",
        "prompt": "Que look de color debe dominar en DaVinci.",
        "field_path": ["davinci_finish", "color_look"],
        "choices": ["teal-copper-cinematic", "cold-science-premium", "neutral-high-end"],
    },
    {
        "id": "contrast-profile",
        "block": "Transiciones, FX y color",
        "prompt": "Que perfil de contraste debe usarse.",
        "field_path": ["davinci_finish", "contrast_profile"],
        "choices": ["suave-premium", "equilibrado", "alto-contraste-controlado"],
    },
    {
        "id": "texture-profile",
        "block": "Transiciones, FX y color",
        "prompt": "Que perfil de textura o nitidez debe aplicarse.",
        "field_path": ["davinci_finish", "texture_profile"],
        "choices": ["limpio-cinematico", "organico-digital", "nitido-premium"],
    },
    {
        "id": "resolution",
        "block": "Resolucion, codec y entrega",
        "prompt": "Con que resolucion debe terminarse el proyecto.",
        "field_path": ["davinci_finish", "resolution"],
        "choices": ["1080p Full HD", "1440p", "4K UHD"],
    },
    {
        "id": "delivery-codec",
        "block": "Resolucion, codec y entrega",
        "prompt": "Que codec final debe usarse.",
        "field_path": ["davinci_finish", "delivery_codec"],
        "choices": ["MP4 H.264", "MP4 H.265", "MOV master de alta calidad"],
    },
    {
        "id": "delivery-target",
        "block": "Resolucion, codec y entrega",
        "prompt": "Cual es el destino de entrega principal.",
        "field_path": ["davinci_finish", "delivery_target"],
        "choices": ["YouTube principal", "Master archivo y YouTube", "Entrega premium para revision"],
    },
]


def _normalize_lines(value: str) -> str:
    cleaned = [line.rstrip() for line in str(value or "").splitlines()]
    return "\n".join(cleaned).strip()


def _get_nested(payload: dict, field_path: list[str]):
    current = payload
    for key in field_path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _ensure_nested(payload: dict, field_path: list[str]):
    current = payload
    for key in field_path[:-1]:
        if not isinstance(current.get(key), dict):
            current[key] = {}
        current = current[key]


def _is_answered(value) -> bool:
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, str):
        normalized = _normalize_lines(value).lower()
        return bool(normalized and normalized != "pending")
    return value is not None


def _serialize_answer(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return _normalize_lines(value)
    return value


def ensure_brief_shape(brief: dict) -> dict:
    for section in [
        ["project_identity"],
        ["approval"],
        ["language_and_voices"],
        ["language_and_voices", "roles"],
        ["music_and_sound"],
        ["visual_direction"],
        ["davinci_finish"],
        ["implementation_state"],
        ["guided_brief"],
    ]:
        _ensure_nested(brief, section + ["_placeholder"])
        _get_nested(brief, section).pop("_placeholder", None)
    return brief


def sync_brief_state(brief: dict) -> dict:
    ensure_brief_shape(brief)
    now = datetime.now(timezone.utc).isoformat()
    questions = []
    pending_ids = []

    for question in QUESTION_FLOW:
        answer = _serialize_answer(_get_nested(brief, question["field_path"]))
        status = "answered" if _is_answered(answer) else "pending"
        if status == "pending":
            pending_ids.append(question["id"])
        questions.append(
            {
                "id": question["id"],
                "block": question["block"],
                "prompt": question["prompt"],
                "field_path": ".".join(question["field_path"]),
                "choices": question["choices"],
                "answer": answer,
                "status": status,
            }
        )

    guided_brief = brief["guided_brief"]
    guided_brief["total_questions"] = len(questions)
    guided_brief["answered_questions"] = len(questions) - len(pending_ids)
    guided_brief["pending_question_ids"] = pending_ids
    guided_brief["next_question_id"] = pending_ids[0] if pending_ids else ""
    guided_brief["questions"] = questions
    guided_brief["last_synced_utc"] = now

    implementation_state = brief["implementation_state"]
    implementation_state["brief_completed"] = not pending_ids
    implementation_state["ready_for_render_plan"] = not pending_ids
    implementation_state["last_updated_utc"] = now

    brief["brief_status"] = "awaiting_guided_questions" if pending_ids else "approved_brief"
    return brief


def build_questionnaire_payload(project: str, brief: dict) -> dict:
    guided = brief.get("guided_brief", {})
    next_question_id = guided.get("next_question_id", "")
    next_question = next((item for item in guided.get("questions", []) if item["id"] == next_question_id), None)
    return {
        "project": project,
        "brief_status": brief.get("brief_status", ""),
        "answered_questions": guided.get("answered_questions", 0),
        "total_questions": guided.get("total_questions", 0),
        "next_question": next_question,
        "questions": guided.get("questions", []),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }


def write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sync_brief_files(project_dir: Path, project: str, brief: dict) -> tuple[dict, Path]:
    synced = sync_brief_state(brief)
    admin_dir = project_dir / "00-admin"
    questionnaire_path = admin_dir / "guided-brief-questionnaire.json"
    payload = build_questionnaire_payload(project, synced)
    write_json(questionnaire_path, payload)
    synced["guided_brief"]["questionnaire_reference"] = str(questionnaire_path)
    return synced, questionnaire_path
