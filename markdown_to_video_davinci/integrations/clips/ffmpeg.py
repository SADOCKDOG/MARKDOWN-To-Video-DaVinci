"""FFmpeg-based clip assembly runner.

Converts a still image (+ optional WAV audio) into a base MP4 clip using
``ffmpeg`` via ``subprocess``.  FFmpeg must be installed and available on
``PATH`` (or specified via ``ffmpeg_bin``).

Con audio
---------
::

    ffmpeg -loop 1 -i image.png -i audio.wav \\
           -c:v libx264 -tune stillimage \\
           -c:a aac -b:a 192k \\
           -pix_fmt yuv420p -shortest output.mp4

Sin audio (duracion fija)
-------------------------
::

    ffmpeg -loop 1 -i image.png -t <duration> \\
           -c:v libx264 -tune stillimage \\
           -pix_fmt yuv420p output.mp4

Requirements
------------
``ffmpeg`` instalado y disponible en ``PATH``.

Usage
-----
>>> from markdown_to_video_davinci.integrations.clips.ffmpeg import FFmpegRunner
>>> runner = FFmpegRunner()
>>> updated_job = runner.assemble(job)
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ...models.assets import ClipJob
from ...models.canonical import AssetState
from .base import ClipRunner


class FFmpegRunner(ClipRunner):
    """Ensamblado de clips MP4 base a partir de stills + audio via FFmpeg."""

    def __init__(
        self,
        ffmpeg_bin: str = "ffmpeg",
        video_codec: str = "libx264",
        audio_codec: str = "aac",
        audio_bitrate: str = "192k",
        pix_fmt: str = "yuv420p",
        extra_video_args: list[str] | None = None,
    ) -> None:
        self._ffmpeg = ffmpeg_bin
        self._vcodec = video_codec
        self._acodec = audio_codec
        self._abitrate = audio_bitrate
        self._pix_fmt = pix_fmt
        self._extra_video_args = extra_video_args or []

    def assemble(self, job: ClipJob) -> ClipJob:
        out_path = Path(job.output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = self._build_command(job, out_path)
        try:
            subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"FFmpeg no encontrado: '{self._ffmpeg}'. "
                "Instala FFmpeg y asegurate de que este en PATH, o pasa ffmpeg_bin= "
                "a FFmpegRunner con la ruta completa."
            )
        except subprocess.CalledProcessError:
            job.state = AssetState.REJECTED
            return job

        if out_path.exists() and out_path.stat().st_size > 0:
            job.state = AssetState.GENERATED
        else:
            job.state = AssetState.REJECTED
        return job

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _build_command(self, job: ClipJob, out_path: Path) -> list[str]:
        audio_path = job.audio_path
        has_audio = bool(audio_path and Path(audio_path).exists())

        cmd: list[str] = [
            self._ffmpeg,
            "-y",           # sobreescribir sin preguntar
            "-loop", "1",
            "-i", job.image_path,
        ]

        if has_audio:
            cmd += ["-i", str(audio_path)]

        cmd += [
            "-c:v", self._vcodec,
            "-tune", "stillimage",
        ]
        cmd += self._extra_video_args
        cmd += ["-pix_fmt", self._pix_fmt]

        if has_audio:
            cmd += [
                "-c:a", self._acodec,
                "-b:a", self._abitrate,
                "-shortest",
            ]
        else:
            cmd += ["-t", str(job.duration_seconds)]

        cmd.append(str(out_path))
        return cmd
