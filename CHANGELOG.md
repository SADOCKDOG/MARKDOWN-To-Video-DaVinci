# CHANGELOG — MARKDOWN-to-Video-DaVinci

Todos los cambios relevantes de esta aplicacion se documentan en este archivo.
El formato sigue las convenciones de [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).
El versionado sigue [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Documentacion

- README ampliado con una estrategia de validacion end-to-end para v0.2.0.
- Documentado el carril automatizado principal local: OpenVINO + pyttsx3/SAPI + FFmpeg.
- Documentado el carril complementario manual/remoto: SDNext, Stability AI API, ElevenLabs API y DaVinci Resolve.
- Anotados preflight, reanudacion del asset registry y casos de fallo recomendados para pruebas del pipeline.

### Fixed

- `LocalTTSProvider` ya no reutiliza una unica instancia de `pyttsx3` entre jobs consecutivos.
- Corregido un bloqueo en la validacion local end-to-end al sintetizar varios cues de voz en una misma ejecucion.

---

## [0.2.0] — 2026-05-10

### Lo que habia (v0.1.0)

La version inicial implementaba la **capa de orquestacion y planificacion**:
el pipeline producia manifiestos, registros de jobs y paquetes de exportacion,
pero no ejecutaba la generacion real de assets. Los comandos `run-*` no existian.

Componentes presentes en v0.1.0:

| Componente | Estado |
|---|---|
| CLI (`init-project`, `build` legacy) | Operativo |
| CLI (`compile-literary`, `build-technical`, `generate-assets`, `prepare-resolve`, `review-pack`) | Operativo |
| `cli.py` `run-images` / `run-voice` / `run-clips` | **No existia** |
| Parser Markdown | Operativo |
| Builder legacy | Operativo |
| Modelos de datos (canonical, assets, resolve, review) | Operativo |
| Pipeline stages 1–5 | Operativo |
| `pipeline/run_assets.py` | **No existia** |
| Integracion Resolve (CSV + JSON) | Operativo |
| Integracion TTS — local (pyttsx3) | Operativo |
| Integracion TTS — ElevenLabs | **No existia** |
| Integracion imagenes — Stability AI | Operativo (proveedor de planificacion) |
| Integracion imagenes — OpenVINO | Operativo (proveedor de planificacion) |
| Integracion clips — FFmpeg | **No existia** |
| `models/assets.py` `from_dict()` | **No existia** (no era posible rehidratar registros guardados) |
| Schemas YAML | Operativo |
| Plantillas (literary, technical, clasica) | Operativo |
| `requirements.txt` | **No existia** |

### Anadido en v0.2.0

#### Capa de ejecucion real de assets (Etapas 6a / 6b / 6c)

- **`markdown_to_video_davinci/pipeline/run_assets.py`** — nuevo modulo de ejecucion:
  - `run_image_jobs()` — carga el registro, lanza el proveedor de imagen sobre
    cada job en estado `planned` y persiste el estado final (`generated` / `rejected`).
  - `run_voice_jobs()` — igual para los jobs de voz.
  - `run_clip_jobs()` — igual para los jobs de clip (FFmpeg).

#### Nuevas integraciones

- **`integrations/clips/base.py`** — interfaz abstracta `ClipRunner`.
- **`integrations/clips/ffmpeg.py`** — `FFmpegRunner`: ensamblado de still + audio
  en clip MP4 base mediante `ffmpeg -loop 1 -i image -i audio ... -shortest output.mp4`.
- **`integrations/tts/elevenlabs.py`** — `ElevenLabsProvider`: sintesis de voz de
  calidad final via REST API (requiere `ELEVENLABS_API_KEY` y `voice_id`).

#### Rehidratacion del registro de assets

- **`models/assets.py`** — se anadieron metodos `from_dict()` en `ImageJob`,
  `VoiceJob`, `ClipJob` y `AssetRegistry` para cargar y continuar ejecuciones
  a partir de un JSON guardado en disco.

#### Nuevos comandos CLI

- `run-images --image-provider stability|openvino [--model-dir] [--registry]`
- `run-voice --tts-provider local|elevenlabs [--voice-id] [--registry]`
- `run-clips [--ffmpeg-bin] [--registry]`

#### Documentacion y dependencias

- **`README.md`** actualizado: flujo de 8 etapas completo, tablas de salidas
  reales, comandos de ejecucion con variables de entorno y proveedores.
- **`requirements.txt`** creado: `pyyaml`, `requests`, `pyttsx3`; OpenVINO como
  dependencia opcional comentada; nota de instalacion de FFmpeg como herramienta
  de sistema.

### Comparativa de flujo — antes y ahora

```
ANTES (v0.1.0)
  Markdown → [compile-literary] → YAML
           → [build-technical]  → JSON canonico
           → [generate-assets]  → Registro de jobs (planificados, sin ejecutar)
           → [prepare-resolve]  → Paquete Resolve JSON + CSV
           → [review-pack]      → Manifiesto de revision
           → [BLOQUEADO] No habia forma de ejecutar los jobs desde CLI

AHORA (v0.2.0)
  Markdown → [compile-literary] → YAML
           → [build-technical]  → JSON canonico
           → [generate-assets]  → Registro de jobs
           → [prepare-resolve]  → Paquete Resolve JSON + CSV
           → [review-pack]      → Manifiesto de revision
           → [run-images]       → PNG por plano (Stability AI API | OpenVINO local)
           → [run-voice]        → WAV/MP3 por dialogo (pyttsx3 local | ElevenLabs API)
           → [run-clips]        → MP4 base por plano (FFmpeg: still + audio)
           → [DaVinci Resolve]  → Montaje, color, render final
```

### Estadisticas del cambio

| Metrica | Valor |
|---|---|
| Archivos nuevos | 6 (`run_assets.py`, `clips/__init__.py`, `clips/base.py`, `clips/ffmpeg.py`, `tts/elevenlabs.py`, `requirements.txt`) |
| Archivos modificados | 4 (`cli.py`, `models/assets.py`, `pipeline/__init__.py`, `tts/__init__.py`, `README.md`) |
| Lineas insertadas netas | ~700 |
| Nuevos comandos CLI | 3 (`run-images`, `run-voice`, `run-clips`) |
| Nuevos proveedores | 2 (ElevenLabs, FFmpegRunner) |

---

## [0.1.0] — 2026-05-09

### Anadido

Implementacion inicial de la arquitectura de pipeline en 6 etapas:

- Estructura de modulos: `parser`, `builder`, `models`, `pipeline`, `integrations`.
- Modelos de datos tipados: `CanonicalEpisode`, `AssetRegistry`, `ResolvePackage`, `ReviewManifest`.
- Pipeline de planificacion: `compile-literary`, `build-technical`, `generate-assets`,
  `prepare-resolve`, `review-pack`.
- Integraciones de imagen: `StabilityProvider`, `OpenVINOProvider`.
- Integracion TTS local: `LocalTTSProvider` (pyttsx3).
- Integracion Resolve: exportador CSV y exportador JSON rico.
- Schemas YAML de validacion para cada capa del pipeline.
- Plantillas de entrada: literaria, tecnica y clasica.
- CLI completo con subcomandos de las 5 etapas + flujo legacy (`build`).
- `.gitignore` configurado para excluir artefactos generados y datos de proyectos.
