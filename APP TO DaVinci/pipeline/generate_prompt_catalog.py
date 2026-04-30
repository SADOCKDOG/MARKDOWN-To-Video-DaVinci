import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, payload: dict):
    lines = [
        f"# Catálogo de prompts - {payload['project']}",
        "",
        f"- Estado del proyecto: `{payload['project_state']}`",
        f"- Prompt recomendado ahora: `{payload['recommended_prompt']}`",
        "",
        "| Tipo | Estado | Prompt | Cuándo usarlo |",
        "|---|---|---|---|",
    ]
    for item in payload["available_prompts"]:
        prompt = item["prompt"].replace("|", "\\|")
        when = item["when_to_use"].replace("|", "\\|")
        lines.append(f"| {item['kind']} | {item['status']} | `{prompt}` | {when} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_catalog(project: str, manifest: dict, brief: dict, runtime: dict) -> dict:
    state = []
    if manifest:
        state.append("project_materialized")
    if brief.get("brief_status") == "approved_brief":
        state.append("brief_approved")
    if brief.get("implementation_state", {}).get("runtime_generated"):
        state.append("runtime_generated")

    prompts = [
        {
            "kind": "bootstrap",
            "status": "available",
            "prompt": "Genera el proyecto y los episodios según las instrucciones contenidas en este directorio raíz",
            "when_to_use": "Para arrancar un proyecto nuevo desde MD TO YOUTUBE.",
        },
        {
            "kind": "brief_project",
            "status": "available" if manifest else "not_ready",
            "prompt": f"Entregables del proyecto {project} verificado y aprobado, procede a generarlos a traves de un plan",
            "when_to_use": "Para abrir el briefing creativo global del proyecto una vez revisados los entregables.",
        },
        {
            "kind": "approve_runtime",
            "status": "available" if brief.get("brief_status") == "approved_brief" else "not_ready",
            "prompt": "Brief revisado y aprobado, procede con este runtime",
            "when_to_use": "Para activar el runtime global aprobado del proyecto.",
        },
        {
            "kind": "execute_episode_runtime",
            "status": "available" if runtime else "not_ready",
            "prompt": "Prepara y ejecuta el Episodio [NOMBRE DEL EPISODIO] según el runtime aprobado del proyecto, regenerando el flujo completo de este episodio: audios, stock online, plan semántico, montaje y render final en DaVinci Resolve.",
            "when_to_use": "Para lanzar la ejecución completa de un episodio concreto usando el runtime aprobado.",
        },
        {
            "kind": "execute_episode_template",
            "status": "planned",
            "prompt": "Prepara y ejecuta el Episodio [NOMBRE DEL EPISODIO] según la plantilla",
            "when_to_use": "Para abrir el selector de plantillas por episodio antes de ejecutar el flujo audiovisual.",
        },
        {
            "kind": "suggest_next",
            "status": "available",
            "prompt": "Propon un prompt para el siguiente paso",
            "when_to_use": "Para que Copilot sugiera el siguiente prompt válido según el estado real del proyecto.",
        },
    ]

    if runtime:
        recommended = prompts[3]["prompt"]
    elif brief.get("brief_status") == "approved_brief":
        recommended = prompts[2]["prompt"]
    elif manifest:
        recommended = prompts[1]["prompt"]
    else:
        recommended = prompts[0]["prompt"]

    return {
        "project": project,
        "project_state": ",".join(state) if state else "bootstrap_pending",
        "recommended_prompt": recommended,
        "available_prompts": prompts,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="Genera un catálogo de prompts disponibles para un proyecto.")
    parser.add_argument("--root", type=Path, required=True, help="Raíz DaVinci Projects")
    parser.add_argument("--project", required=True, help="Nombre del proyecto en FINALS PROJECTS")
    args = parser.parse_args()

    root_dir = args.root.resolve()
    project_dir = root_dir / "FINALS PROJECTS" / args.project
    admin_dir = project_dir / "00-admin"

    manifest = load_json(admin_dir / "project-manifest.json") if (admin_dir / "project-manifest.json").exists() else {}
    brief = load_json(admin_dir / "production-brief.json") if (admin_dir / "production-brief.json").exists() else {}
    runtime = load_json(admin_dir / "production-runtime.json") if (admin_dir / "production-runtime.json").exists() else {}

    catalog = build_catalog(args.project, manifest, brief, runtime)
    json_path = admin_dir / "prompt-catalog.json"
    md_path = admin_dir / "prompt-catalog.md"
    write_json(json_path, catalog)
    write_markdown(md_path, catalog)

    print(f"OK|PROJECT={args.project}|CATALOG={json_path}|MARKDOWN={md_path}")


if __name__ == "__main__":
    main()
