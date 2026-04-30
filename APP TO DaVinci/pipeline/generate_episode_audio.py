import argparse
import asyncio
import json
import subprocess
from pathlib import Path

import edge_tts

from semantic_video_planner import extract_blocks


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run(cmd: list[str]):
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def write_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return float(result.stdout.strip())


def find_episode_manifest_entry(project_manifest: dict, episode_name: str) -> dict:
    for item in project_manifest.get("episodes", []):
        if item.get("episode") == episode_name:
            return item
    raise SystemExit(f"No se encontró el episodio '{episode_name}' en project-manifest.json")


def parse_heading_lines(path: Path) -> list[str]:
    return [line.strip()[2:].strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip().startswith("- ")]


async def save_tts(text: str, voice: str, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    await edge_tts.Communicate(text=text, voice=voice).save(str(out_path))


def concat_inputs(items: list[Path], output: Path):
    manifest = output.parent / f"{output.stem}-concat.txt"
    manifest.write_text("".join(f"file '{path.as_posix()}'\n" for path in items), encoding="utf-8")
    run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(manifest), "-c", "copy", str(output)])


async def main_async(root: Path, project: str, episode_name: str):
    project_dir = root / "FINALS PROJECTS" / project
    admin_dir = project_dir / "00-admin"
    runtime = load_json(admin_dir / "production-runtime.json")
    project_manifest = load_json(admin_dir / "project-manifest.json")
    voice_plan = load_json(Path(runtime["voice_plan_reference"]))

    episode_entry = find_episode_manifest_entry(project_manifest, episode_name)
    episode_dir = Path(episode_entry["legacy_source"])
    md_path = episode_dir / f"{episode_name}.md"
    headings_md = episode_dir / "videos" / "on-screen-text-es.md"
    blocks = extract_blocks(md_path)
    headings = parse_heading_lines(headings_md)
    if len(blocks) != len(headings):
        raise SystemExit(f"Headings y bloques no coinciden en {episode_name}: {len(headings)} vs {len(blocks)}")

    audio_es = episode_dir / "audio" / "es"
    headings_dir = audio_es / "headings-female"
    bodies_dir = audio_es / "blocks-male"
    blocks_dir = audio_es / "blocks"
    render_tmp = episode_dir / "videos" / "render-temp"
    for directory in [headings_dir, bodies_dir, blocks_dir, render_tmp]:
        directory.mkdir(parents=True, exist_ok=True)

    female_voice = voice_plan["selected_voices"]["titles_cards"]["ShortName"]
    male_voice = voice_plan["selected_voices"]["narration_main"]["ShortName"]

    write_text(audio_es / "headings-female-es.md", "\n".join(headings) + "\n")

    body_chunks: list[str] = []
    block_outputs: list[Path] = []
    female_outputs: list[Path] = []
    male_outputs: list[Path] = []

    for idx, ((_, _heading, body), heading_text) in enumerate(zip(blocks, headings), start=1):
        female_path = headings_dir / f"{idx:02}.mp3"
        await save_tts(heading_text, female_voice, female_path)
        female_outputs.append(female_path)

        if body:
            male_path = bodies_dir / f"{idx:02}.mp3"
            await save_tts(body, male_voice, male_path)
            male_outputs.append(male_path)
            body_chunks.append(body)
        else:
            male_path = None

        output = blocks_dir / f"{idx:02}.mp3"
        cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", str(female_path), "-f", "lavfi", "-t", "0.35", "-i", "anullsrc=r=24000:cl=mono"]
        if male_path is not None:
            cmd += ["-i", str(male_path), "-filter_complex", "[0:a][1:a][2:a]concat=n=3:v=0:a=1[a]", "-map", "[a]"]
        else:
            cmd += ["-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[a]", "-map", "[a]"]
        cmd += ["-c:a", "mp3", str(output)]
        run(cmd)
        block_outputs.append(output)

    concat_inputs(block_outputs, audio_es / "youtube-es-full.mp3")

    full_text = "\n\n".join(body_chunks).strip()
    if not full_text:
        full_text = "\n\n".join(body for _, _, body in blocks if body).strip()
    write_text(audio_es / "narration-source-es.md", full_text + ("\n" if full_text else ""))
    write_text(audio_es / "locucion-es.md", full_text + ("\n" if full_text else ""))

    if full_text:
        await save_tts(full_text, male_voice, audio_es / "narration-source-es.mp3")
        await save_tts(full_text, male_voice, audio_es / "locucion-es.mp3")
    concat_inputs(female_outputs, audio_es / "headings-female-es.mp3")

    metadata = {
        "episode": episode_name,
        "episode_dir": str(episode_dir),
        "male_voice": male_voice,
        "female_voice": female_voice,
        "block_count": len(block_outputs),
        "youtube_es_full_duration": round(probe_duration(audio_es / "youtube-es-full.mp3"), 3),
        "generated_outputs": {
            "headings_dir": str(headings_dir),
            "blocks_male_dir": str(bodies_dir),
            "blocks_dir": str(blocks_dir),
            "youtube_es_full": str(audio_es / "youtube-es-full.mp3"),
            "narration_source_mp3": str(audio_es / "narration-source-es.mp3"),
            "locucion_mp3": str(audio_es / "locucion-es.mp3"),
            "headings_full_mp3": str(audio_es / "headings-female-es.mp3"),
        },
    }
    write_text(audio_es / "runtime-audio-generation.json", json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print(
        f"OK|EPISODE={episode_name}|MALE={male_voice}|FEMALE={female_voice}|AUDIO={audio_es / 'youtube-es-full.mp3'}"
    )


def main():
    parser = argparse.ArgumentParser(description="Regenera el audio de un episodio usando el voice-plan del proyecto.")
    parser.add_argument("--root", type=Path, required=True, help="Raíz DaVinci Projects")
    parser.add_argument("--project", required=True, help="Proyecto dentro de FINALS PROJECTS")
    parser.add_argument("--episode", required=True, help="Nombre exacto del episodio")
    args = parser.parse_args()
    asyncio.run(main_async(args.root.resolve(), args.project, args.episode))


if __name__ == "__main__":
    main()
