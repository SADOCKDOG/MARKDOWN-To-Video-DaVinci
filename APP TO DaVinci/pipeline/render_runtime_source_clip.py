import argparse
import json
import subprocess
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def probe_duration(path: Path) -> float:
    return float(
        subprocess.check_output(
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
            text=True,
        ).strip()
    )


def format_ass_ts(seconds: float) -> str:
    cs = int(round(seconds * 100))
    h = cs // 360000
    cs %= 360000
    m = cs // 6000
    cs %= 6000
    s = cs // 100
    cs %= 100
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def escape_sub_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:")


def ass_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def split_heading(text: str) -> str:
    words = text.split()
    if len(words) <= 4:
        return text
    midpoint = len(words) // 2
    return " ".join(words[:midpoint]) + r"\N" + " ".join(words[midpoint:])


def write_ass(path: Path, headings, durations):
    styles = [
        ("PolarBlue", "&H00F0E8D8", "&H00101828", "&H78000000"),
        ("PetrolGlow", "&H00FFDFA0", "&H00142030", "&H78000000"),
        ("DeepIce", "&H00FFFFFF", "&H00152030", "&H78000000"),
    ]
    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1920",
        "PlayResY: 1080",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
    ]
    for name, primary, outline, back in styles:
        header.append(
            f"Style: {name},Arial,52,{primary},&H00FFFFFF,{outline},{back},1,0,0,0,100,100,1.2,0,1,5,0,5,140,140,0,1"
        )
    header += ["", "[Events]", "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text"]
    events = []
    start = 0.0
    for idx, (heading, dur) in enumerate(zip(headings, durations), start=1):
        subtitle_end = start + min(max(5.6, min(7.2, dur * 0.42)), max(3.8, dur - 0.12))
        style = styles[(idx - 1) % len(styles)][0]
        text = split_heading(ass_escape(heading))
        events.append(
            f"Dialogue: 0,{format_ass_ts(start)},{format_ass_ts(subtitle_end)},{style},,0,0,0,,{{\\an5\\pos(960,540)\\move(960,625,960,520,0,900)\\fad(420,520)\\blur3.2\\bord5\\shad0\\fscx82\\fscy82\\t(0,700,\\fscx100\\fscy100)\\t(700,1600,\\fscx104\\fscy104)}}{text}"
        )
        start += dur
    path.write_text("\n".join(header + events) + "\n", encoding="utf-8")


def build_xfade_graph(visual_paths, transition_duration: float):
    parts = []
    durations = []
    for idx, path in enumerate(visual_paths):
        parts.append(
            f"[{idx}:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=24,format=yuv420p,settb=AVTB,setpts=PTS-STARTPTS[v{idx}]"
        )
        durations.append(probe_duration(path))
    if len(visual_paths) == 1:
        parts.append("[v0]format=yuv420p[vout]")
        return ";".join(parts)
    offset = durations[0] - transition_duration
    parts.append(f"[v0][v1]xfade=transition=fade:duration={transition_duration:.3f}:offset={offset:.3f}[x1]")
    cumulative = durations[0] + durations[1] - transition_duration
    for idx in range(2, len(visual_paths)):
        offset = cumulative - transition_duration
        parts.append(f"[x{idx-1}][v{idx}]xfade=transition=fade:duration={transition_duration:.3f}:offset={offset:.3f}[x{idx}]")
        cumulative += durations[idx] - transition_duration
    parts.append(f"[x{len(visual_paths)-1}]format=yuv420p[vout]")
    return ";".join(parts)


def select_visual_paths(clip_paths, total_audio: float, transition_duration: float):
    visual_total = 0.0
    visual_paths = []
    while True:
        for path in clip_paths:
            visual_paths.append(path)
            visual_total += probe_duration(path)
            effective = visual_total - max(0, len(visual_paths) - 1) * transition_duration
            if effective >= total_audio + 1.0:
                return visual_paths, effective
        if not clip_paths:
            break
    effective = visual_total - max(0, len(visual_paths) - 1) * transition_duration
    return visual_paths, effective


def music_volume(label: str) -> float:
    mapping = {
        "baja y elegante": 0.08,
        "media y envolvente": 0.14,
        "alta y protagonista": 0.22,
        "variable segun momento": 0.12,
    }
    return mapping.get(label.lower(), 0.08)


def main():
    parser = argparse.ArgumentParser(description="Genera el master fuente del runtime aprobado.")
    parser.add_argument("--execution-plan", type=Path, required=True)
    args = parser.parse_args()

    plan = load_json(args.execution_plan)
    path_keys = {
        "headings_markdown",
        "block_audio_dir",
        "narration_audio",
        "music_audio",
        "render_dir",
        "delivery_dir",
        "source_output",
        "final_output",
        "ass_output",
        "resolve_output_dir",
        "resolve_render_settings",
        "resolve_style_guide",
    }
    paths = {k: Path(v) for k, v in plan["paths"].items() if k in path_keys}
    headings = [
        line.strip()[2:].strip()
        for line in paths["headings_markdown"].read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("- ")
    ]
    block_files = sorted(paths["block_audio_dir"].glob("[0-9][0-9].mp3"))
    durations = [probe_duration(path) for path in block_files]
    if len(headings) != len(durations):
        raise RuntimeError("Headings y bloques no coinciden.")

    paths["render_dir"].mkdir(parents=True, exist_ok=True)
    write_ass(paths["ass_output"], headings, durations)

    narration = paths["narration_audio"]
    music = paths["music_audio"]
    total_audio = probe_duration(narration)
    transition_duration = 0.35
    clip_paths = [Path(path) for path in plan["paths"]["stock_clips"]]
    visual_paths, effective_visual = select_visual_paths(clip_paths, total_audio, transition_duration)
    if effective_visual < total_audio:
        raise RuntimeError(f"Stock insuficiente: {effective_visual} < {total_audio}")

    fade_out = max(total_audio - 5.0, 0.0)
    output = paths["source_output"]
    volume = music_volume(plan["brief_snapshot"]["music_and_sound"]["music_intensity"])
    cmd = ["ffmpeg", "-loglevel", "error", "-y"]
    for path in visual_paths:
        cmd += ["-i", str(path)]
    audio_input_idx = len(visual_paths)
    music_input_idx = len(visual_paths) + 1
    cmd += ["-i", str(narration), "-stream_loop", "-1", "-i", str(music)]
    video_graph = build_xfade_graph(visual_paths, transition_duration)
    filter_complex = (
        video_graph
        + f";[vout]subtitles='{escape_sub_path(paths['ass_output'])}'[vfinal];"
        + f"[{audio_input_idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[n];"
        + f"[{music_input_idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,volume={volume:.2f},afade=t=in:st=0:d=3,afade=t=out:st={fade_out:.3f}:d=5[m];"
        + f"[n][m]amix=inputs=2:duration=first:normalize=0[a]"
    )
    cmd += [
        "-filter_complex",
        filter_complex,
        "-map",
        "[vfinal]",
        "-map",
        "[a]",
        "-t",
        f"{total_audio:.3f}",
        "-shortest",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "21",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(output),
    ]
    run(cmd)
    print(f"OUTPUT={output}")


if __name__ == "__main__":
    main()
