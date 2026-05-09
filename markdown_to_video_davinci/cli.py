from __future__ import annotations

import argparse
import json
from pathlib import Path

from .builder import build_project, copy_project_template


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="markdown-to-video-davinci",
        description="Convierte guiones Markdown en manifiestos y shotlists para video.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-project", help="Crea la estructura base de un proyecto.")
    init_parser.add_argument("project_dir", help="Ruta del proyecto a inicializar.")

    build_parser_cmd = subparsers.add_parser("build", help="Genera prompts, manifiestos y shotlist.")
    build_parser_cmd.add_argument("project_dir", help="Ruta del proyecto.")
    build_parser_cmd.add_argument(
        "--markdown",
        help="Ruta del Markdown a procesar. Si se omite, usa el primer .md encontrado en input\\markdown.",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    repository_dir = Path(__file__).resolve().parent.parent
    project_dir = Path(args.project_dir).resolve()

    if args.command == "init-project":
        copy_project_template(project_dir, repository_dir)
        print(json.dumps({"initialized_project": str(project_dir)}, ensure_ascii=False, indent=2))
        return

    if args.command == "build":
        markdown_path = Path(args.markdown).resolve() if args.markdown else None
        summary = build_project(project_dir, markdown_path)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    raise ValueError(f"Comando no soportado: {args.command}")


if __name__ == "__main__":
    main()
