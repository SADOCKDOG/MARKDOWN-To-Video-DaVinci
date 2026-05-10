"""ElevenLabs TTS provider.

Sintetiza dialogos usando la API REST de ElevenLabs y guarda el audio en
formato MP3 (o WAV si el endpoint lo soporta).

Requirements
------------
``pip install requests``

Environment variable
--------------------
``ELEVENLABS_API_KEY`` — tu API key de ElevenLabs.

Uso
---
>>> from markdown_to_video_davinci.integrations.tts.elevenlabs import ElevenLabsProvider
>>> provider = ElevenLabsProvider(voice_id="21m00Tcm4TlvDq8ikWAM")
>>> updated_job = provider.synthesise(job)

Seleccion de voz
----------------
Puedes buscar voice_ids disponibles en https://api.elevenlabs.io/v1/voices
o con el panel de ElevenLabs.  Si no se especifica voice_id se usa el
endpoint ``/v1/text-to-speech/<voice_id>`` con la voz por defecto.

La respuesta es audio MP3 que se guarda con la extension ``.mp3``.
Si ``job.output_path`` termina en ``.wav``, el archivo se guarda igualmente
como MP3 (ElevenLabs no devuelve WAV nativo en el endpoint basico), pero
se usa la ruta indicada para que el resto del pipeline localice el archivo.
"""

from __future__ import annotations

import os
from pathlib import Path

from ...models.assets import VoiceJob
from ...models.canonical import AssetState
from .base import TTSProvider


class ElevenLabsProvider(TTSProvider):
    """Sintesis de voz de calidad final via ElevenLabs REST API."""

    API_BASE = "https://api.elevenlabs.io/v1"
    DEFAULT_MODEL = "eleven_multilingual_v2"

    def __init__(
        self,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        api_key: str | None = None,
        model_id: str = DEFAULT_MODEL,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
    ) -> None:
        self._voice_id = voice_id
        self._api_key = api_key or os.environ.get("ELEVENLABS_API_KEY", "")
        self._model_id = model_id
        self._stability = stability
        self._similarity_boost = similarity_boost

    def synthesise(self, job: VoiceJob) -> VoiceJob:
        try:
            import requests
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "El paquete 'requests' es necesario para ElevenLabsProvider. "
                "Instalalo con: pip install requests"
            ) from exc

        if not self._api_key:
            raise RuntimeError(
                "ELEVENLABS_API_KEY no esta configurada. "
                "Exportala como variable de entorno o pasa api_key= a ElevenLabsProvider."
            )

        url = f"{self.API_BASE}/text-to-speech/{self._voice_id}"
        payload = {
            "text": job.text,
            "model_id": self._model_id,
            "voice_settings": {
                "stability": self._stability,
                "similarity_boost": self._similarity_boost,
            },
        }
        headers = {
            "xi-api-key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }

        response = requests.post(url, json=payload, headers=headers, timeout=120)

        if response.status_code != 200:
            job.state = AssetState.REJECTED
            return job

        out_path = Path(job.output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(response.content)

        if out_path.exists() and out_path.stat().st_size > 0:
            job.state = AssetState.GENERATED
        else:
            job.state = AssetState.REJECTED
        return job
