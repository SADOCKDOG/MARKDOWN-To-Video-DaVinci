# MARKDOWN-to-Video-DaVinci

Base reusable para convertir guiones en Markdown en paquetes de trabajo listos para generar imagenes y organizar un montaje en DaVinci Resolve.

Este repositorio **no incluye proyectos generados**, imagenes, modelos, avatares finales ni salidas de episodios. Solo contiene la aplicacion y la estructura minima para levantar nuevos proyectos.

## Que hace

1. Inicializa la estructura de un proyecto.
2. Lee un guion en Markdown con personajes, escenas y prompts.
3. Genera manifiestos JSON, prompts `.txt` y una shotlist `.csv` para DaVinci.

## Estructura esperada

```text
mi_proyecto/
  input/
    avatars/
    markdown/
  output/
    davinci/
    images/
    manifests/
    prompts/
    requests/
```

## Uso rapido

```powershell
python -m markdown_to_video_davinci.cli init-project .\proyecto_demo
python -m markdown_to_video_davinci.cli build .\proyecto_demo
```

Si quieres usar un archivo concreto:

```powershell
python -m markdown_to_video_davinci.cli build .\proyecto_demo --markdown .\proyecto_demo\input\markdown\mi_episodio.md
```

## Formato Markdown

El parser espera una estructura como esta:

````md
## Calidad visual
```text
Cinematic realism, controlled light, grounded textures.
```

# PERSONAJE - GOR
## Prompt IA
```text
Photorealistic hunter portrait, cinematic close-up...
```

# ESCENA 01 - Apertura
## Visual
Bosque humedo al amanecer con tension contenida.

## Personajes
- GOR
- NARA

## Prompt Visual
```text
Two hunters cross a wet prehistoric forest at dawn...
```
````

Tambien se aceptan encabezados de personaje como `# GOR` y listas de personajes separadas por comas.

## Salidas generadas

- `output\manifests\avatar_manifest.json`
- `output\manifests\scene_manifest.json`
- `output\manifests\scene_requests.json`
- `output\prompts\*.txt`
- `output\requests\*.json`
- `output\davinci\davinci_shotlist.csv`
- `output\manifests\build_summary.json`

## Plantillas

- `templates\episode_template.md`
- `templates\project\...`

Usa `init-project` para copiar la estructura base y un episodio de ejemplo editable.
