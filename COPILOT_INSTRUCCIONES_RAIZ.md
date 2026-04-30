# Instrucciones raíz para Copilot CLI

## Modo obligatorio

Este directorio debe trabajarse **siempre en modo plan** de GitHub Copilot CLI.

## Objetivo

Desde la raíz `DaVinci Projects`, Copilot debe:

1. leer este archivo;
2. detectar el único Markdown activo dentro de `MD TO YOUTUBE`;
3. mover ese archivo al nuevo proyecto materializado y usarlo como fuente editorial principal;
4. crear o actualizar la materialización del proyecto dentro de `FINALS PROJECTS`;
5. usar `APP TO DaVinci` como motor reusable del pipeline;
6. continuar después con la cadena audiovisual: episodización, textos, audio, stock, plan semántico, integración con DaVinci Resolve y export final.

## Contrato de carpetas

- `APP TO DaVinci`: scripts, plantillas, conectores y lógica reusable.
- `MD TO YOUTUBE`: **un solo Markdown activo por ejecución**; funciona como bandeja de entrada.
- `FINALS PROJECTS`: salida materializada del proyecto.

## Regla de nombres

- El **nombre del proyecto Resolve** se toma del nombre completo del Markdown activo.
- La **carpeta serie** en `FINALS PROJECTS` se toma del tramo principal del nombre antes del primer separador ` - `.

Ejemplo:

- Markdown activo: `Mi Serie Documental -  Tema Principal.md`
- Carpeta de salida: `FINALS PROJECTS\Mi Serie Documental\`
- Proyecto Resolve: `Mi Serie Documental -  Tema Principal`

## Punto de entrada técnico

El bootstrap inicial del proyecto debe ejecutarse con:

`APP TO DaVinci\run-project.ps1`

Si el usuario no recuerda el siguiente paso, puede pedir:

`Propon un prompt para el siguiente paso`

y Copilot deberá leer o regenerar el catálogo del proyecto para sugerir el prompt correcto.

## Fase posterior: proyecto verificado y aprobado

Cuando el usuario confirme por prompt que los entregables del proyecto han sido **verificados y aprobados**, Copilot deberá:

1. identificar el proyecto ya materializado en `FINALS PROJECTS`;
2. inicializar o actualizar el manifiesto `production-brief.json` del proyecto;
3. abrir un nuevo plan de briefing guiado;
4. preguntar una a una las decisiones de:
   - idiomas y voces;
   - música y atmósfera;
   - estilo cinematográfico y textos;
   - transiciones y FX;
   - color, resolución y calidad final para DaVinci.

El inicializador técnico de esta fase es:

`APP TO DaVinci\run-init-production-brief.ps1`

## Fase posterior: runtime y regeneración completa

Cuando el brief ya esté aprobado, Copilot puede:

- preparar o ejecutar el runtime por defecto;
- o ejecutar un episodio concreto con regeneración completa.

Para la regeneración completa por episodio, el lanzador operativo es:

`APP TO DaVinci\run-execute-selected-episode.ps1 -Project "<Proyecto>" -Episode "<Episodio>" -FullRegenerate`

## Comportamiento esperado

- No procesar varios Markdown en lote.
- Tras el arranque del flujo, el Markdown activo debe desaparecer de `MD TO YOUTUBE` porque queda movido al proyecto creado.
- No mezclar artefactos de distintos proyectos dentro de la misma carpeta de salida.
- Reutilizar branding, voces y plantillas ya consolidadas.
- Mantener el flujo preparado para reejecución sin duplicar estructura innecesariamente.
- Tras una aprobación del usuario, el briefing creativo debe quedar guardado dentro de `00-admin\production-brief.json`.
- No publicar proyectos reales ni secretos cuando este directorio se prepare para repositorio.
