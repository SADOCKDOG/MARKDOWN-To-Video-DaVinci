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
- catálogo de prompts operativo por proyecto.

## Estructura

- `pipeline`: scripts Python reutilizables.
- `config`: configuración base portable.
- `assets`: plantillas, branding de ejemplo y catálogos de voces.
- `assets\BRANDING`: carpeta para poner branding propio del canal antes de materializar proyectos.
- `SciClip`: integración local de stock. **No publicar `SciClip\.streamlit\secrets.toml`.**
- `APPROVAL_FLOW.md`: guía del flujo de aprobación, runtime y regeneración completa.

## Publicación en repositorio

- No incluir proyectos reales dentro de `FINALS PROJECTS`.
- No incluir markdowns activos de trabajo dentro de `MD TO YOUTUBE`.
- No incluir secretos ni claves de APIs.
- Configurar `APP TO DaVinci\config\pipeline-settings.json` con rutas propias si se quiere usar siembra desde una librería legacy externa.
