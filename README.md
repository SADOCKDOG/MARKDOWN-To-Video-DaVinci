# MARKDOWN To Video DaVinci

Pipeline reusable para convertir un proyecto editorial en Markdown en un flujo audiovisual con:

1. materialización del proyecto;
2. briefing creativo guiado;
3. runtime aprobado por proyecto;
4. regeneración de audio y stock;
5. plan semántico;
6. integración con DaVinci Resolve;
7. render final.

## Estructura raíz

- `APP TO DaVinci`: motor reusable.
- `MD TO YOUTUBE`: bandeja de entrada con un solo Markdown activo.
- `FINALS PROJECTS`: salida materializada por proyecto. En el repositorio debe permanecer vacía.
- `COPILOT_INSTRUCCIONES_RAIZ.md`: contrato operativo para Copilot CLI.

## Flujo recomendado

1. Copia un Markdown fuente a `MD TO YOUTUBE`.
2. Ejecuta el bootstrap del proyecto.
3. Aprueba entregables y abre el brief guiado.
4. Genera el runtime del proyecto.
5. Ejecuta un episodio concreto.
6. Si necesitas rehacer todo un episodio, usa `-FullRegenerate`.

## Comandos clave

- `APP TO DaVinci\run-project.ps1`
- `APP TO DaVinci\run-init-production-brief.ps1 -Project "<Proyecto>"`
- `APP TO DaVinci\run-apply-production-brief.ps1 -Project "<Proyecto>"`
- `APP TO DaVinci\run-execute-selected-episode.ps1 -Project "<Proyecto>" -Episode "<Episodio>"`
- `APP TO DaVinci\run-execute-selected-episode.ps1 -Project "<Proyecto>" -Episode "<Episodio>" -FullRegenerate`

## Preparación para repositorio

- no incluir proyectos reales dentro de `FINALS PROJECTS`;
- no incluir markdowns de trabajo dentro de `MD TO YOUTUBE`;
- no incluir secretos de `APP TO DaVinci\SciClip\.streamlit\secrets.toml`;
- colocar branding propio dentro de `APP TO DaVinci\assets\BRANDING`;
- revisar `APP TO DaVinci\config\pipeline-settings.json` para adaptar rutas locales opcionales.
