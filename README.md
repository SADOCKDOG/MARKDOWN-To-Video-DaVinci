# MARKDOWN-to-Video-DaVinci

Aplicacion base para transformar un guion en Markdown en un paquete de produccion visual: prompts, manifiestos, requests tecnicos y shotlist para montaje en DaVinci Resolve.

Este repositorio **no contiene datos de proyectos concretos**: no incluye personajes reales de una obra, nombres propios, episodios finales, imagenes generadas, modelos convertidos, renders ni proyectos exportados. Solo publica la **infraestructura de aplicacion** y la **estructura de trabajo**.

## Infraestructura creada en este repositorio

| Componente | Ubicacion | Funcion |
| --- | --- | --- |
| CLI de proyecto | `markdown_to_video_davinci\cli.py` | Inicializa proyectos y ejecuta la compilacion del paquete visual |
| Parser Markdown | `markdown_to_video_davinci\parser.py` | Extrae calidad visual, personajes, escenas y prompts |
| Builder de salidas | `markdown_to_video_davinci\builder.py` | Genera manifiestos JSON, prompts `.txt`, requests por escena y shotlist `.csv` |
| Paquete Python | `markdown_to_video_davinci\` | Nucleo reusable de la aplicacion |
| Plantilla de episodio | `templates\episode_template.md` | Ejemplo neutro de entrada Markdown |
| Estructura de proyecto | `templates\project\...` | Carpetas base para `input` y `output` |
| Reglas de publicacion | `.gitignore` | Excluye salidas, avatares locales y artefactos generados |

## Que resuelve esta aplicacion

1. Estandariza la entrada narrativa en Markdown.
2. Convierte esa entrada en una estructura tecnica reproducible.
3. Separa contenido fuente de artefactos generados.
4. Deja preparado el material para generacion de imagenes y montaje de video.

## Estructura del proyecto generado

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

Para compilar un Markdown especifico:

```powershell
python -m markdown_to_video_davinci.cli build .\proyecto_demo --markdown .\proyecto_demo\input\markdown\mi_episodio.md
```

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

| Salida | Ruta | Uso |
| --- | --- | --- |
| Manifest de personajes | `output\manifests\avatar_manifest.json` | Relacion entre personajes y referencias visuales disponibles |
| Manifest de escenas | `output\manifests\scene_manifest.json` | Resumen estructurado de escenas y prompts |
| Requests por escena | `output\manifests\scene_requests.json` | Lote tecnico completo para generacion |
| Prompts finales | `output\prompts\*.txt` | Texto listo para motores de imagen |
| Request individual | `output\requests\*.json` | Configuracion aislada por plano o escena |
| Shotlist DaVinci | `output\davinci\davinci_shotlist.csv` | Base de importacion y montaje editorial |
| Resumen de build | `output\manifests\build_summary.json` | Trazabilidad de la compilacion |

## Pipeline completo

Este repositorio cubre la **capa de orquestacion y empaquetado** dentro de un pipeline mayor:

1. **Escritura**: el proyecto parte de un guion estructurado en Markdown.
2. **Referencias visuales**: se agregan avatares, fotos, concept art o referencias en `input\avatars`.
3. **Compilacion**: la CLI transforma el Markdown en prompts, manifests y requests consistentes.
4. **Generacion de imagenes**: esos prompts pueden enviarse a motores externos.
5. **Curacion**: se seleccionan las imagenes finales por escena o plano.
6. **Montaje**: la shotlist CSV y las imagenes se llevan a DaVinci Resolve.
7. **Edicion y render**: se ajustan tiempos, audio, transiciones, color y export final.

## Aplicaciones, APIs y herramientas utilizadas en el pipeline

La aplicacion publicada aqui es el **nucleo reusable**, pero el flujo completo puede conectarse con estas capas externas:

| Capa | Herramienta | Rol en el pipeline | Incluida en este repo |
| --- | --- | --- | --- |
| Orquestacion | Python | Ejecucion de CLI, parser y builder | Si |
| Definicion de contenido | Markdown | Fuente editable del guion tecnico y visual | Si |
| Estructura de intercambio | JSON / CSV / TXT | Requests, manifests, prompts y shotlists | Si |
| Generacion de imagen local | OpenVINO GenAI | Text-to-image local sobre modelos convertidos | No |
| Generacion de imagen por API | Stability AI Stable Image API | Generacion remota de imagenes desde prompts | No |
| UI local de imagen | SDNext u otras WebUI compatibles | Exploracion iterativa, pruebas y ajuste fino | No |
| Experimentacion | Jupyter / Colab | Notebooks de prueba, tuning y validacion visual | No |
| Edicion y conformado | DaVinci Resolve | Ensamblado, ritmo, color, audio y export de video | No |

## Alcance exacto de esta publicacion

**Incluye**:

- la estructura base de proyecto
- la aplicacion Python reusable
- el parser generico
- el builder de manifests, prompts y shotlist
- plantillas neutras sin datos narrativos concretos

**No incluye**:

- nombres de personajes de proyectos reales
- prompts propietarios de una obra concreta
- imagenes generadas o referencias finales
- modelos convertidos o pesos
- notebooks operativos del proyecto original
- renders de video ni timelines exportadas

## Objetivo de esta separacion

La idea es que el repositorio publique solo la **plataforma de produccion** y no el contenido creativo derivado de proyectos concretos. Asi la base queda reutilizable para cualquier nuevo guion, cualquier universo narrativo y cualquier backend de generacion visual compatible.
