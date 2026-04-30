import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Inicializa el production brief de un proyecto materializado.")
    parser.add_argument("--root", type=Path, required=True, help="Raíz DaVinci Projects")
    parser.add_argument("--project", required=True, help="Nombre de carpeta del proyecto dentro de FINALS PROJECTS")
    parser.add_argument("--approval-prompt", default="", help="Texto o referencia del prompt de aprobación del usuario")
    args = parser.parse_args()

    root_dir = args.root.resolve()
    settings = load_json(root_dir / "APP TO DaVinci" / "config" / "pipeline-settings.json")
    template_path = root_dir / Path(settings["production_brief_template"])
    template = deepcopy(load_json(template_path))

    project_dir = root_dir / "FINALS PROJECTS" / args.project
    if not project_dir.exists():
        raise SystemExit(f"No existe el proyecto: {project_dir}")

    manifest_path = project_dir / "00-admin" / "project-manifest.json"
    project_manifest = load_json(manifest_path)

    template["brief_status"] = "awaiting_guided_questions"
    template["project_identity"]["series_title"] = project_manifest.get("series_title", "")
    template["project_identity"]["resolve_project_name"] = project_manifest.get("resolve_project_name", "")
    template["project_identity"]["source_markdown_name"] = project_manifest.get("source_markdown_name", "")
    template["approval"]["project_verified"] = True
    template["approval"]["approved_by_user"] = True
    template["approval"]["approval_prompt_reference"] = args.approval_prompt
    template["implementation_state"]["brief_completed"] = False
    template["implementation_state"]["ready_for_render_plan"] = False
    template["implementation_state"]["last_updated_utc"] = datetime.now(timezone.utc).isoformat()

    output_path = project_dir / "00-admin" / settings["production_brief_filename"]
    output_path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"OK|PROJECT={args.project}|BRIEF={output_path}")


if __name__ == "__main__":
    main()
