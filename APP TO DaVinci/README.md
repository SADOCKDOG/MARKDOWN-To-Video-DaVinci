# APP TO DaVinci

Motor reusable del pipeline audiovisual para convertir un proyecto editorial Markdown en un flujo reproducible de brief, runtime, stock, audio, plan semántico, DaVinci Resolve y entrega final.

## Entradas principales

- `run-project.ps1`: materializa un proyecto desde la raíz `DaVinci Projects`.
- `run-semantic-stock.ps1`: ejecuta el bridge semántico de stock sobre un root de episodios.
- `run-resolve-import.ps1`: importa un `semantic-shot-plan.json` a DaVinci Resolve.
- `run-init-production-brief.ps1`: inicializa el briefing creativo de un proyecto ya verificado.
- `run-apply-production-brief.ps1`: convierte el brief aprobado en runtime ejecutable.
- `run-execute-runtime.ps1`: prepara o ejecuta el runtime aprobado sobre el Episodio 01 por defecto.
- `run-execute-selected-episode.ps1`: prepara o ejecuta un episodio concreto usando el runtime aprobado.
- `run-execute-selected-episode.ps1 -FullRegenerate`: ejecuta la cadena completa de voces -> audio -> stock -> plan semántico -> montaje -> render.
- `run-generate-prompt-catalog.ps1`: genera el catálogo de prompts válidos y el siguiente prompt recomendado.

## Novedades ya integradas

- catálogo de voces refreshed con prioridad multilingual real del proveedor TTS;
- regeneración automática de audio por episodio basada en `voice-plan.json`;
- soporte de `-FullRegenerate` para encadenar voz, audio, stock, plan semántico, montaje y render;
- ensamblador semántico global en Resolve: el runtime ya monta por segmentos en timeline editable en DaVinci en lugar de hornear el vídeo base con FFmpeg;
- política global `Resolve-first`: nuevos proyectos, episodios individuales y regeneraciones completas heredan el mismo flujo SciClip + puente semántico local -> importación total en Resolve -> selección/montaje en Resolve -> render final;
- catálogo de prompts operativo por proyecto;
- cuestionario persistente `00-admin\guided-brief-questionnaire.json` para retomar el brief guiado sin perder el estado;
- sincronización automática del estado del brief para activar el runtime solo cuando `production-brief.json` está completo.

## Flujo global de esta fase

La política global vive en `APP TO DaVinci\config\pipeline-settings.json` bajo `global_runtime_policy` y se copia también al `production-brief.json` de cada proyecto nuevo.

Esto fija de forma global que:

1. `SciClip + puente semántico local` busca, deduplica, puntúa y descarga el pool de stock según un perfil dinámico por episodio.
   - Restricción global de stock descargable: **solo `1920x1080` en `16:9`**.
2. `DaVinci Resolve` importa primero el pool completo, la narración, la música y el plan semántico.
3. La selección final de clips, el orden de timeline, textos, look, color, transiciones y FX se resuelven en la fase de ensamblado de Resolve usando los controles del brief.
4. `FFmpeg` queda relegado a soporte de audio/utilidades, no al montaje visual principal.

Este comportamiento aplica a:

- proyectos nuevos inicializados con `run-init-production-brief.ps1`;
- ejecución de episodios seleccionados con `run-execute-selected-episode.ps1`;
- regeneración completa con `run-execute-selected-episode.ps1 -FullRegenerate`.

## Estructura

- `pipeline`: scripts Python reutilizables.
- `config`: configuración base portable.
- `assets`: plantillas, branding de ejemplo y catálogos de voces.
- `assets\BRANDING`: carpeta para poner branding propio del canal antes de materializar proyectos.
- `SciClip`: integración local de stock. **No publicar `SciClip\.streamlit\secrets.toml`.**
- `APPROVAL_FLOW.md`: guía del flujo de aprobación, runtime y regeneración completa.

## Brief guiado

- `run-init-production-brief.ps1` deja creado `00-admin\production-brief.json` y también `00-admin\guided-brief-questionnaire.json`.
- `run-generate-prompt-catalog.ps1` refleja si el brief está en curso, cuál es el prompt para retomarlo y cuál es la siguiente pregunta pendiente.
- `run-apply-production-brief.ps1` resincroniza el brief antes de generar runtime; si faltan respuestas, corta el proceso con el estado actualizado en disco.

## Pack global de titulos Resolve

- `run-install-global-resolve-titles.ps1` genera e instala un pack user-scope de plantillas Fusion en:
  - `C:\Users\<usuario>\AppData\Roaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\Templates\Edit\Titles`
- El pack inicial se instala bajo la carpeta:
  - `Copilot SciFi ES`
- Incluye una variante en espanol para cada familia:
  - `title_cards`
  - `lower_thirds`
  - `documentary_overlays`
- Si solo se quiere generar el pack sin copiarlo al perfil de DaVinci:
  - `run-install-global-resolve-titles.ps1 -BuildOnly`

## Publicación en repositorio

- No incluir proyectos reales dentro de `FINALS PROJECTS`.
- No incluir markdowns activos de trabajo dentro de `MD TO YOUTUBE`.
- No incluir secretos ni claves de APIs.
- Configurar `APP TO DaVinci\config\pipeline-settings.json` con rutas propias si se quiere usar siembra desde una librería legacy externa.
