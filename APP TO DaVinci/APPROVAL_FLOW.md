# Approval flow

## Cuándo usarlo

Cuando el usuario confirme que los entregables del proyecto ya fueron revisados, verificados y aprobados.

## Ayuda de navegación del flujo

Si el usuario no recuerda el siguiente paso, puede pedir:

`Propon un prompt para el siguiente paso`

y Copilot deberá consultar o regenerar el catálogo de prompts del proyecto.

## Disparador esperado

Un prompt de tipo:

`Entregables del proyecto <Nombre> verificado y aprobado, procede a generarlos a traves de un plan`

## Secuencia operativa

1. Inicializar el manifiesto de producción:
   - `run-init-production-brief.ps1 -Project "<Nombre carpeta en FINALS PROJECTS>"`
2. Entrar en modo plan.
3. Lanzar preguntas guiadas con `ask_user`, una por vez.
4. Completar `00-admin\production-brief.json`.
5. Pasar a implementación final en Resolve solo cuando el brief esté completo.

## Fase posterior al brief aprobado

Cuando el usuario confirme:

`Brief revisado y aprobado, procede con este runtime`

la ejecución por defecto debe hacerse sobre:

- `Episodio 01 - Vida espejo y quiralidad`

usando:

- `run-execute-runtime.ps1 -Project "<Nombre carpeta en FINALS PROJECTS>"`

Si solo se quiere preparar y validar el plan de ejecución sin lanzar render:

- `run-execute-runtime.ps1 -Project "<Nombre carpeta en FINALS PROJECTS>" -PrepareOnly`

## Ejecución por episodio seleccionado

Cuando el usuario pida:

`Prepara y ejecuta el Episodio seleccionado`

Copilot debe:

1. comprobar si el episodio viene explícito en el prompt;
2. si no viene, preguntar cuál ejecutar;
3. usar:
   - `run-execute-selected-episode.ps1 -Project "<Nombre carpeta en FINALS PROJECTS>" -Episode "<Nombre exacto del episodio>"`

Si solo se quiere preparar el plan por episodio:

- `run-execute-selected-episode.ps1 -Project "<Nombre carpeta en FINALS PROJECTS>" -Episode "<Nombre exacto del episodio>" -PrepareOnly`

## Regeneración completa por episodio

Cuando el usuario pida explícitamente:

`Prepara y ejecuta el Episodio <NOMBRE> según el runtime aprobado del proyecto, regenerando el flujo completo de este episodio: audios, stock online, plan semántico, montaje y render final en DaVinci Resolve.`

usar:

- `run-execute-selected-episode.ps1 -Project "<Nombre carpeta en FINALS PROJECTS>" -Episode "<Nombre exacto del episodio>" -FullRegenerate`

Esto encadena:

1. refresco del catálogo de voces;
2. reaplicación del brief para regenerar `voice-plan.json`;
3. regeneración de audio del episodio;
4. refresco del pool stock online;
5. regeneración del plan semántico;
6. source master;
7. render final en DaVinci Resolve.

## Nota de publicación

Para publicar este motor en un repositorio:

- no incluir proyectos dentro de `FINALS PROJECTS`;
- no incluir secretos de `SciClip\.streamlit\secrets.toml`;
- no incluir branding propietario salvo que se desee publicar expresamente.

## Bloques de preguntas

1. Idiomas y voces
2. Música y atmósfera
3. Estilo cinematográfico y textos
4. Transiciones, FX y color
5. Resolución, codec y entrega
