import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_TARGET_DIR = (
    Path.home()
    / "AppData"
    / "Roaming"
    / "Blackmagic Design"
    / "DaVinci Resolve"
    / "Support"
    / "Fusion"
    / "Templates"
    / "Edit"
    / "Titles"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict):
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def lua_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def format_number(value: float) -> str:
    rendered = f"{value:.4f}".rstrip("0").rstrip(".")
    return rendered or "0"


def build_text_node(layer: dict, view_x: int, view_y: int) -> str:
    center_x, center_y = layer["center"]
    return (
        f'\t\t{layer["node_name"]} = TextPlus {{\n'
        f"\t\t\tInputs = {{\n"
        f'\t\t\t\tStyledText = Input {{ Value = "{lua_escape(layer["text"])}", }},\n'
        f'\t\t\t\tFont = Input {{ Value = "{lua_escape(layer["font"])}", }},\n'
        f'\t\t\t\tSize = Input {{ Value = {format_number(layer["size"])}, }},\n'
        f"\t\t\t\tCenter = Input {{ Value = {{ {format_number(center_x)}, {format_number(center_y)} }}, }},\n"
        f'\t\t\t\t[ "EffectMask" ] = Input {{ }},\n'
        f"\t\t\t}},\n"
        f"\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {view_x}, {view_y} }} }},\n"
        f"\t\t}},\n"
    )


def build_merge_node(index: int, background_name: str, foreground_name: str, view_x: int, view_y: int) -> str:
    merge_name = f"Merge{index}"
    return (
        f"\t\t{merge_name} = Merge {{\n"
        f"\t\t\tInputs = {{\n"
        f'\t\t\t\tBackground = Input {{ SourceOp = "{background_name}", Source = "Output", }},\n'
        f'\t\t\t\tForeground = Input {{ SourceOp = "{foreground_name}", Source = "Output", }},\n'
        f"\t\t\t}},\n"
        f"\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {view_x}, {view_y} }} }},\n"
        f"\t\t}},\n"
    )


def build_setting(template: dict) -> str:
    blocks = [
        "{\n",
        "\tTools = ordered() {\n",
        "\t\tBackground1 = Background {\n",
        "\t\t\tInputs = {\n",
        "\t\t\t\tWidth = Input { Value = 1920, },\n",
        "\t\t\t\tHeight = Input { Value = 1080, },\n",
        "\t\t\t\tAlpha = Input { Value = 0, },\n",
        '\t\t\t\t[ "EffectMask" ] = Input { },\n',
        "\t\t\t},\n",
        "\t\t\tViewInfo = OperatorInfo { Pos = { -330, 0 } },\n",
        "\t\t},\n",
    ]

    previous_node = "Background1"
    merge_count = 0
    for index, layer in enumerate(template["layers"], start=1):
        view_y = (index - 1) * 72
        blocks.append(build_text_node(layer, -170, view_y))
        merge_count += 1
        merge_name = f"Merge{merge_count}"
        blocks.append(build_merge_node(merge_count, previous_node, layer["node_name"], 10, view_y))
        previous_node = merge_name

    blocks.extend(
        [
            "\t\tMediaOut1 = MediaOut {\n",
            "\t\t\tInputs = {\n",
            f'\t\t\t\tInput = Input {{ SourceOp = "{previous_node}", Source = "Output", }},\n',
            "\t\t\t},\n",
            "\t\t\tViewInfo = OperatorInfo { Pos = { 180, 0 } },\n",
            "\t\t}\n",
            "\t}\n",
            "}\n",
        ]
    )
    return "".join(blocks)


def build_pack(app_root: Path, output_root: Path) -> tuple[Path, dict]:
    spec_path = app_root / "assets" / "resolve_global_text_pack.json"
    spec = load_json(spec_path)
    pack_dir = output_root / spec["folder_name"]
    if pack_dir.exists():
        shutil.rmtree(pack_dir)
    pack_dir.mkdir(parents=True, exist_ok=True)

    manifest_templates = []
    for template in spec["templates"]:
        destination = pack_dir / template["file_name"]
        write_text(destination, build_setting(template))
        manifest_templates.append(
            {
                "family": template["family"],
                "file_name": template["file_name"],
                "display_name": template["display_name"],
                "style_notes": template["style_notes"],
                "relative_path": str(destination.relative_to(output_root)),
            }
        )

    manifest = {
        "pack_name": spec["pack_name"],
        "folder_name": spec["folder_name"],
        "description": spec["description"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "templates": manifest_templates,
    }
    write_json(pack_dir / "manifest.json", manifest)

    readme_lines = [
        f'{spec["pack_name"]}\n',
        f'{spec["description"]}\n',
        "\n",
        "Incluye una variante por familia:\n",
    ]
    for template in spec["templates"]:
        readme_lines.append(f'- {template["family"]}: {template["file_name"]}\n')
    write_text(pack_dir / "README.txt", "".join(readme_lines))
    return pack_dir, manifest


def install_pack(pack_dir: Path, manifest: dict, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    install_dir = target_dir / manifest["folder_name"]
    if install_dir.exists():
        shutil.rmtree(install_dir)
    shutil.copytree(pack_dir, install_dir)
    return install_dir


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-root", required=True)
    parser.add_argument("--output")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--target-dir")
    args = parser.parse_args()

    app_root = Path(args.app_root).resolve()
    output_root = Path(args.output).resolve() if args.output else app_root / "dist" / "resolve-global-titles"
    target_dir = Path(args.target_dir).resolve() if args.target_dir else DEFAULT_TARGET_DIR

    pack_dir, manifest = build_pack(app_root, output_root)
    install_dir = None
    if args.install:
        install_dir = install_pack(pack_dir, manifest, target_dir)

    message = f"OK|PACK={pack_dir}|TEMPLATES={len(manifest['templates'])}"
    if install_dir:
        message += f"|TARGET={install_dir}"
    print(message)


if __name__ == "__main__":
    main()
