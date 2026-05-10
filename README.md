# MARKDOWN-to-Video-DaVinci

Aplicacion base para transformar un guion en Markdown en un paquete de produccion visual completo: guion tecnico, manifiestos canonicos, registros de assets, paquete Resolve y manifiesto de revision humana.

Este repositorio **no contiene datos de proyectos concretos**: no incluye personajes reales de una obra, nombres propios, episodios finales, imagenes generadas, modelos convertidos, renders ni proyectos exportados. Solo publica la **infraestructura de aplicacion** y la **estructura de trabajo**.

## Infraestructura creada en este repositorio

| Componente | Ubicacion | Funcion |
| --- | --- | --- |
| CLI de proyecto | `markdown_to_video_davinci\cli.py` | Inicializa proyectos y ejecuta todas las etapas del pipeline |
| Parser Markdown | `markdown_to_video_davinci\parser.py` | Extrae calidad visual, personajes, escenas y prompts |
| Builder de salidas | `markdown_to_video_davinci\builder.py` | Genera manifiestos JSON, prompts `.txt`, requests por escena y shotlist `.csv` |
| Modelos de datos | `markdown_to_video_davinci\models\` | Contratos tipados: canonico, assets, resolve, revision |
| Pipeline de etapas | `markdown_to_video_davinci\pipeline\` | Orquestadores por etapa: literary, breakdown, assets, resolve_prep, review, run_assets |
| Integracion Resolve | `markdown_to_video_davinci\integrations\resolve\` | Exportador CSV legado + paquete JSON rico |
| Integracion TTS | `markdown_to_video_davinci\integrations\tts\` | Proveedores de voz: local offline (pyttsx3) y ElevenLabs API |
| Integracion imagenes | `markdown_to_video_davinci\integrations\images\` | Proveedores de imagen: Stability AI API y OpenVINO local |
| Integracion clips | `markdown_to_video_davinci\integrations\clips\` | Runner FFmpeg: ensamblado de still + audio en clip MP4 base |
| Schemas | `schemas\` | Definiciones YAML de cada capa del pipeline |
| Plantilla literaria | `templates\literary_episode_template.md` | Guion literario de ejemplo con planos y dialogos |
| Plantilla tecnica | `templates\technical_episode_template.yaml` | Guion tecnico YAML con planos, dialogos y timings |
| Plantilla clasica | `templates\episode_template.md` | Entrada Markdown en formato original (compatibilidad) |
| Reglas de publicacion | `.gitignore` | Excluye salidas, avatares locales y artefactos generados |

## Que resuelve esta aplicacion

1. Estandariza la entrada narrativa en Markdown (guion literario).
2. Genera un borrador de guion tecnico YAML editable por humanos.
3. Convierte ese YAML en un manifiesto canonico normalizado (episodio → escenas → planos → dialogos → timings → recursos).
4. Produce registros de jobs de imagen, voz y clip base para proveedores externos o locales.
5. Genera el paquete Resolve (JSON rico + CSV legado) para ensamblado semi-automatico.
6. Emite el manifiesto de revision humana con checklist de QC por plano.

## Arquitectura del pipeline en 8 etapas

```
Etapa 1 — compile-literary   Markdown literario → YAML tecnico borrador
Etapa 2 — build-technical    YAML tecnico       → JSON canonico
Etapa 3 — generate-assets    JSON canonico      → registros de jobs de imagen/voz/clip
Etapa 4 — prepare-resolve    JSON canonico      → paquete Resolve JSON + CSV
Etapa 5 — review-pack        JSON canonico      → manifiesto de revision humana
Etapa 6a — run-images        Registro de assets → imagenes generadas (Stability AI | OpenVINO)
Etapa 6b — run-voice         Registro de assets → audio sintetizado (local pyttsx3 | ElevenLabs)
Etapa 6c — run-clips         Registro de assets → clips base MP4 (FFmpeg: still + audio)
Etapa 7 — [Human + Resolve]  Revision editorial + render final en DaVinci Resolve
```

## Estructura del proyecto generado

```text
mi_proyecto/
  input/
    avatars/           Referencias visuales de personajes
    literary/          Guiones literarios .md
    markdown/          Guiones clasicos .md (compatibilidad)
    technical/         Guiones tecnicos .yaml (editables)
  output/
    audio/             WAV de dialogos sintetizados
    clips/             Clips base MP4 (still + audio via FFmpeg)
    davinci/           Paquete Resolve JSON + CSV de shotlist
    images/            Imagenes generadas por plano
    logs/              Logs de ejecucion
    manifests/         JSON canonico, registros de assets, resumen de build
    prompts/           Prompts .txt por escena (modo clasico)
    requests/          Requests .json por escena (modo clasico)
    review/            Manifiestos de revision humana
    subtitles/         Archivos SRT por plano
```

## Uso rapido

### Flujo completo (pipeline de 8 etapas)

```powershell
# Inicializar proyecto (copia plantillas a input/literary/ e input/technical/)
python -m markdown_to_video_davinci.cli init-project .\proyecto_demo

# Etapa 1 — Compilar guion literario en YAML tecnico borrador
python -m markdown_to_video_davinci.cli compile-literary .\proyecto_demo

# Editar .\proyecto_demo\input\technical\*.yaml: ajustar planos, dialogos y timings

# Etapa 2 — Generar manifiesto canonico JSON
python -m markdown_to_video_davinci.cli build-technical .\proyecto_demo

# Etapa 3 — Generar registros de jobs de assets (planificacion, no ejecucion)
python -m markdown_to_video_davinci.cli generate-assets .\proyecto_demo

# Etapa 4 — Generar paquete Resolve
python -m markdown_to_video_davinci.cli prepare-resolve .\proyecto_demo

# Etapa 5 — Generar manifiesto de revision humana
python -m markdown_to_video_davinci.cli review-pack .\proyecto_demo

# Etapa 6a — Ejecutar jobs de imagen (Stability AI, requiere STABILITY_API_KEY)
$env:STABILITY_API_KEY="sk-..."
python -m markdown_to_video_davinci.cli run-images .\proyecto_demo --image-provider stability

# Etapa 6a (alternativa local, sin internet, requiere modelo OpenVINO convertido)
python -m markdown_to_video_davinci.cli run-images .\proyecto_demo --image-provider openvino --model-dir .\converted_sdxl

# Etapa 6b — Ejecutar jobs de voz (TTS local offline, no requiere internet)
python -m markdown_to_video_davinci.cli run-voice .\proyecto_demo --tts-provider local

# Etapa 6b (alternativa ElevenLabs, requiere ELEVENLABS_API_KEY)
$env:ELEVENLABS_API_KEY="..."
python -m markdown_to_video_davinci.cli run-voice .\proyecto_demo --tts-provider elevenlabs --voice-id 21m00Tcm4TlvDq8ikWAM

# Etapa 6c — Ejecutar jobs de clip (FFmpeg debe estar en PATH)
python -m markdown_to_video_davinci.cli run-clips .\proyecto_demo
```

### Flujo clasico (compatibilidad total con versiones anteriores)

```powershell
python -m markdown_to_video_davinci.cli init-project .\proyecto_demo
python -m markdown_to_video_davinci.cli build .\proyecto_demo
```

Para compilar un Markdown especifico (modo clasico):

```powershell
python -m markdown_to_video_davinci.cli build .\proyecto_demo --markdown .\proyecto_demo\input\markdown\mi_episodio.md
```

### Validacion local-first reproducible

Para repetir el E2E local completo con un solo comando:

```powershell
python -m markdown_to_video_davinci.cli validate-local .\tmp_validation --model-dir .\converted_openjourney
```

Este comando:

1. ejecuta el preflight local (`pyttsx3`, `openvino_genai`, `numpy`, `Pillow`, `ffmpeg`, modelo IR)
2. inicializa el proyecto si hace falta
3. compila el Markdown literario
4. usa por defecto la fixture tecnica estable `technical_episode_template.yaml`
5. genera canonico, registro de assets, paquete Resolve y manifiesto de revision
6. ejecuta `run-images`, `run-voice` y `run-clips`
7. repite `run-voice` y `run-clips` para comprobar idempotencia basica
8. devuelve un resumen JSON con conteos, estados y artefactos generados

Flags utiles:

- `--model-dir` **obligatorio**
- `--image-width` / `--image-height` para ajustar la resolucion del smoke test local
- `--markdown` para forzar otra entrada literaria
- `--technical` para forzar otro YAML tecnico
- `--episode-id` para fijar el identificador del episodio compilado
- `--ffmpeg-bin` para usar una ruta explicita de FFmpeg

## Formato Markdown esperado

El parser trabaja con una estructura neutral como esta:

````md
## Calidad visual
```text
Cinematic realism, grounded textures, coherent lighting, production-ready continuity.
```

# PERSONAJE - PERSONAJE_A
## Prompt IA
```text
Photorealistic cinematic portrait, expressive face, grounded wardrobe, controlled lighting, high detail.
```

# ESCENA 01 - Apertura
## Visual
Introduccion atmosferica del conflicto principal con una puesta en escena clara y legible.

## Personajes
- PERSONAJE_A
- PERSONAJE_B

## Prompt Visual
```text
Two grounded characters enter the key location at dawn, subtle tension, realistic textures, cinematic framing.
```
````

Tambien se aceptan encabezados de personaje simples como `# PERSONAJE_A` y listas de personajes separadas por comas.

## Salidas que genera

### Modo clasico (`build`)

| Salida | Ruta | Uso |
| --- | --- | --- |
| Manifest de personajes | `output\manifests\avatar_manifest.json` | Relacion entre personajes y referencias visuales disponibles |
| Manifest de escenas | `output\manifests\scene_manifest.json` | Resumen estructurado de escenas y prompts |
| Requests por escena | `output\manifests\scene_requests.json` | Lote tecnico completo para generacion |
| Prompts finales | `output\prompts\*.txt` | Texto listo para motores de imagen |
| Request individual | `output\requests\*.json` | Configuracion aislada por plano o escena |
| Shotlist DaVinci | `output\davinci\davinci_shotlist.csv` | Base de importacion y montaje editorial |
| Resumen de build | `output\manifests\build_summary.json` | Trazabilidad de la compilacion |

### Modo pipeline completo (etapas 1–8)

| Salida | Ruta | Etapa | Uso |
| --- | --- | --- | --- |
| YAML tecnico borrador | `input\technical\<id>.yaml` | 1 `compile-literary` | Guion tecnico editable con planos, dialogos y timings |
| JSON canonico | `output\manifests\<id>.canonical.json` | 2 `build-technical` | Representacion normalizada: episodio → escenas → planos → dialogos → timings → recursos |
| Registro de assets | `output\manifests\<id>.asset_registry.json` | 3 `generate-assets` | Jobs de imagen, voz y clip para proveedores externos o locales |
| Paquete Resolve | `output\davinci\<id>.resolve_package.json` | 4 `prepare-resolve` | Timeline completo: tracks, bins, relink map, audio, subtitulos, marcadores |
| Shotlist Resolve | `output\davinci\<id>.davinci_shotlist.csv` | 4 `prepare-resolve` | CSV legado con timings reales por plano |
| Manifiesto de revision | `output\review\<id>.review.json` | 5 `review-pack` | Checklist de QC humano: continuidad, lipsync, subtitulos, loudness, assets faltantes |
| Imagenes generadas | `output\images\<shot_slug>.png` | 6a `run-images` | PNG por plano generado por Stability AI o OpenVINO |
| Audio sintetizado | `output\audio\<cue_slug>.wav` | 6b `run-voice` | WAV por dialogo sintetizado por pyttsx3 o ElevenLabs |
| Clips base | `output\clips\<shot_slug>.mp4` | 6c `run-clips` | MP4 base (still + audio) ensamblado por FFmpeg |

## Pipeline completo

Este repositorio cubre la **capa de orquestacion y empaquetado** dentro de un pipeline mayor:

1. **Escritura literaria**: el proyecto parte de un guion narrativo en Markdown (`input\literary\`).
2. **Compilacion tecnica**: `compile-literary` genera un YAML tecnico con planos, dialogos y timings en `input\technical\`.
3. **Desglose canonico**: `build-technical` convierte el YAML en el JSON canonico autoritativo.
4. **Generacion de assets**: `generate-assets` produce registros de jobs de imagen, voz y clip para motores externos o locales.
5. **Preparacion Resolve**: `prepare-resolve` genera el paquete Resolve JSON + CSV para ensamblado semi-automatico.
6. **Revision humana y render**: `review-pack` genera la checklist de QC; el editor revisa, aprueba y renderiza en DaVinci Resolve.

## Aplicaciones, APIs y herramientas utilizadas en el pipeline

La aplicacion publicada aqui es el **nucleo reusable**, pero el flujo completo puede conectarse con estas capas externas:

| Capa | Herramienta | Rol en el pipeline | Incluida en este repo |
| --- | --- | --- | --- |
| Orquestacion | Python | Ejecucion de CLI, parser y pipeline de etapas | Si |
| Definicion de contenido | Markdown + YAML | Guion literario y guion tecnico editable | Si |
| Estructura de intercambio | JSON / CSV / TXT | Canonico, registros de assets, paquete Resolve, manifiestos | Si |
| Schemas de validacion | YAML Schema | Documentacion y validacion de cada capa | Si |
| Generacion de imagen local | OpenVINO GenAI | Text-to-image local sobre modelos convertidos | Si (proveedor integrado) |
| Generacion de imagen por API | Stability AI Stable Image API | Generacion remota de imagenes desde prompts | Si (proveedor integrado) |
| UI local de imagen | SDNext u otras WebUI compatibles | Exploracion iterativa, pruebas y ajuste fino | No |
| TTS local | pyttsx3 (SAPI Windows) | Sintesis de voz offline para borradores de audio | Si (proveedor integrado) |
| TTS de calidad | ElevenLabs API | Sintesis de voz de calidad final en multiples idiomas | Si (proveedor integrado) |
| Ensamblado de clips | FFmpeg | Pan/zoom sobre stills + audio para clips base | Si (runner integrado) |
| Experimentacion | Jupyter / Colab | Notebooks de prueba, tuning y validacion visual | No |
| Edicion y conformado | DaVinci Resolve | Ensamblado, ritmo, color, audio y export de video | No |

## Herramientas utilizadas alrededor de esta base

Estas son las piezas que se usaron como entorno de trabajo alrededor de la aplicacion:

| Herramienta | Uso concreto en el flujo |
| --- | --- |
| OpenVINO GenAI | Generacion local de imagenes text-to-image cuando se queria ejecutar inferencia en local sin depender de una WebUI pesada |
| `optimum-cli export openvino` | Conversion de modelos de Hugging Face a formato OpenVINO IR para poder usarlos con OpenVINO GenAI |
| SDNext | Interfaz local para iterar prompts, comparar variantes, ajustar parametros y explorar resultados visuales |
| Stability AI Stable Image API | Generacion remota de imagenes mediante API cuando interesaba un backend externo y parametrizable |
| pyttsx3 / SAPI | TTS local offline para borradores de audio en Windows 11 sin costes de API |
| FFmpeg | Ensamblado de clips base a partir de stills + audio (pan/zoom) antes del paso a Resolve |
| Jupyter Lab / Notebooks | Entorno de pruebas para preparar prompts, lanzar lotes, validar modelos y revisar resultados |
| Google Colab | Ejecucion ocasional de notebooks conectados a API o pruebas de generacion fuera del equipo local |
| DaVinci Resolve | Montaje final: orden de planos, duraciones, continuidad visual, audio, color y render |

## Flujo operativo de referencia

El pipeline completo se resume asi:

1. **Guion literario**: se redacta el episodio en `input\literary\` con escenas, personajes y prompts base.
2. **`compile-literary`**: genera un borrador YAML tecnico en `input\technical\` con planos, dialogos y timings por defecto.
3. **Edicion humana del YAML**: se ajustan planos, se anaden dialogos y se refinan timings.
4. **`build-technical`**: convierte el YAML en el JSON canonico autoritativo.
5. **`generate-assets`**: produce los registros de jobs de imagen, voz y clip (planificacion, sin ejecucion).
6. **`prepare-resolve`**: genera el paquete Resolve JSON + CSV con paths esperados de imagenes y audio.
7. **`review-pack`**: genera el manifiesto de revision con checklist de QC por plano.
8. **`run-images`**: ejecuta los jobs de imagen contra OpenVINO (local) o Stability AI (API).
9. **`run-voice`**: ejecuta los jobs de voz contra pyttsx3 (local offline) o ElevenLabs (API).
10. **`run-clips`**: ejecuta los jobs de clip: FFmpeg combina cada still con su audio para producir un MP4 base.
11. **Revision humana**: el editor rellena el manifiesto, marca planos aprobados y descarta variantes.
12. **Montaje y render en DaVinci Resolve**: se ensamblan los planos con el paquete JSON de referencia, se ajustan transiciones, color, audio y se exporta el video final.

## Como encajan los proveedores en la arquitectura

- **OpenVINO** cubre la rama de generacion de imagen local optimizada para Intel CPU/GPU.
- **SDNext** cubre la rama de exploracion visual interactiva y ajuste fino de prompts.
- **Stability AI API** cubre la rama de generacion remota parametrizable por servicio.
- **pyttsx3 / SAPI** cubre la sintesis de voz local offline sin coste de licencia.
- **ElevenLabs API** cubre la sintesis de voz de calidad final multilingue para la produccion aprobada.
- **FFmpeg** cubre la generacion de clips base ligeros a partir de stills (sin GPU).
- **DaVinci Resolve** consume el resultado curado de cualquiera de esas ramas.
- **Este repositorio** queda entre el guion y esos motores: normaliza la entrada, orquesta las etapas, ejecuta los jobs de assets e integra directamente los proveedores mas habituales.

## Estrategia de validacion end-to-end recomendada

La validacion del pipeline v0.2.0 debe separarse en dos carriles:

1. **Carril automatizado principal local**: valida la ejecucion completa sin depender de APIs remotas.
2. **Carril complementario manual/remoto**: valida exploracion visual, proveedores premium y conformado editorial.

### Carril automatizado principal local

Este es el recorrido recomendado para probar el pipeline completo de extremo a extremo:

```text
init-project
  -> compile-literary
  -> build-technical
  -> generate-assets --image-provider openvino --tts-provider local
  -> prepare-resolve
  -> review-pack
  -> run-images --image-provider openvino --model-dir <openvino_ir_model>
  -> run-voice --tts-provider local
  -> run-clips
```

Objetivos minimos de validacion:

- se crea `input\technical\*.yaml` desde el guion literario
- se genera `*.canonical.json`
- se genera `*.asset_registry.json`
- se generan `*.resolve_package.json` y `*.davinci_shotlist.csv`
- se genera `*.review.json`
- `run-images` produce PNG por plano
- `run-voice` produce WAV por dialogo
- `run-clips` produce MP4 por plano
- el registro de assets persiste estados `generated` o `rejected`

### Preflight obligatorio antes del E2E local

Antes de ejecutar el carril local completo hay que comprobar:

- `pyyaml`, `requests` y `pyttsx3` instalados en el entorno Python
- `ffmpeg` disponible en `PATH`
- `openvino_genai`, `numpy` y `Pillow` disponibles si se usara OpenVINO
- existencia de un directorio de modelo IR convertido para `--model-dir`
- permisos de escritura sobre `output\`

### Carril complementario manual y remoto

Este carril no sustituye al E2E local; lo complementa:

- **SDNext**: revision manual de prompts y ajuste fino interactivo
- **Stability AI API**: smoke tests remotos para la rama de imagen por servicio
- **ElevenLabs API**: smoke tests remotos para voz final multilingue
- **DaVinci Resolve**: importacion manual del paquete Resolve y comprobacion editorial final

### Reanudacion y persistencia

El pipeline debe validarse tambien en escenarios de continuacion:

- relectura de `*.asset_registry.json` desde disco
- re-ejecucion de `run-voice` y `run-clips` sin reprocesar jobs ya `generated`
- persistencia correcta de estados `planned`, `generated` y `rejected`

### Casos de fallo que deben comprobarse

- `run-images --image-provider openvino` sin `openvino_genai`
- `run-images --image-provider openvino` con `--model-dir` invalido
- `run-clips` con `ffmpeg` ausente o incorrecto
- ausencia de imagen o audio esperado antes del ensamblado del clip
- artefactos vacios o corruptos aunque el archivo exista

## Alcance exacto de esta publicacion

**Incluye**:

- la estructura base de proyecto (input/literary, input/technical, output completo)
- la aplicacion Python reusable con pipeline de 5 etapas + modo clasico
- el parser generico de Markdown literario
- el builder de manifests, prompts y shotlist (modo clasico)
- los modelos de datos tipados (canonical, assets, resolve, review)
- los orquestadores de pipeline (literary, breakdown, assets, resolve_prep, review)
- las abstracciones de proveedores de imagen y TTS
- los schemas YAML de cada capa
- plantillas neutras (literaria, tecnica y clasica) sin datos narrativos concretos

**No incluye**:

- nombres de personajes de proyectos reales
- prompts propietarios de una obra concreta
- imagenes generadas o referencias finales
- modelos convertidos o pesos
- notebooks operativos del proyecto original
- renders de video ni timelines exportadas

## Objetivo de esta separacion

La idea es que el repositorio publique solo la **plataforma de produccion** y no el contenido creativo derivado de proyectos concretos. Asi la base queda reutilizable para cualquier nuevo guion, cualquier universo narrativo y cualquier backend de generacion visual compatible.
