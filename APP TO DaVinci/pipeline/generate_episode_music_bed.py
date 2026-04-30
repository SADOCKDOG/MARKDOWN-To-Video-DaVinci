import argparse
import json
import subprocess
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def render_music_bed(output: Path, duration: float):
    fade_out_start = max(duration - 4.0, 0.0)
    filter_complex = (
        f"sine=frequency=110:sample_rate=48000:duration={duration:.3f},volume=0.05[a0];"
        f"sine=frequency=165:sample_rate=48000:duration={duration:.3f},volume=0.03[a1];"
        f"sine=frequency=220:sample_rate=48000:duration={duration:.3f},volume=0.02[a2];"
        f"anoisesrc=color=pink:sample_rate=48000:duration={duration:.3f},lowpass=f=900,highpass=f=140,volume=0.01[n];"
        "[a0][a1][a2][n]amix=inputs=4:normalize=0,"
        "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
        "afade=t=in:st=0:d=2,"
        f"afade=t=out:st={fade_out_start:.3f}:d=4"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=48000:cl=stereo",
            "-filter_complex",
            filter_complex,
            "-t",
            f"{duration:.3f}",
            "-c:a",
            "mp3",
            str(output),
        ],
        check=True,
    )


def main():
    parser = argparse.ArgumentParser(description="Genera una cama musical procedural para un episodio.")
    parser.add_argument("--root", type=Path, required=True, help="Raíz DaVinci Projects")
    parser.add_argument("--project", required=True, help="Proyecto dentro de FINALS PROJECTS")
    parser.add_argument("--episode", required=True, help="Nombre exacto del episodio")
    args = parser.parse_args()

    project_dir = args.root.resolve() / "FINALS PROJECTS" / args.project
    admin_dir = project_dir / "00-admin"
    project_manifest = load_json(admin_dir / "project-manifest.json")
    episode_entry = find_episode_manifest_entry(project_manifest, args.episode)
    episode_dir = Path(episode_entry["legacy_source"])
    audio_dir = episode_dir / "audio" / "es"
    narration_path = audio_dir / "youtube-es-full.mp3"
    music_path = audio_dir / "music-bg.mp3"

    if not narration_path.exists():
        raise SystemExit(f"No existe la narración base del episodio: {narration_path}")

    duration = probe_duration(narration_path)
    render_music_bed(music_path, duration)

    metadata = {
        "episode": args.episode,
        "music_bed": str(music_path),
        "duration_seconds": round(duration, 3),
        "generator": "procedural-ambient-ffmpeg",
    }
    write_text(audio_dir / "music-bg-generation.json", json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print(f"OK|EPISODE={args.episode}|MUSIC={music_path}|DURATION={duration:.3f}")


if __name__ == "__main__":
    main()
