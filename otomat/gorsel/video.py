"""matplotlib figürünü kare kare ffmpeg'e akıtan yazıcı."""

import subprocess
from pathlib import Path

import imageio_ffmpeg


class VideoYazici:
    def __init__(self, cikti: Path, genislik: int, yukseklik: int, fps: int):
        cikti.parent.mkdir(parents=True, exist_ok=True)
        self._proc = subprocess.Popen(
            [
                imageio_ffmpeg.get_ffmpeg_exe(),
                "-y",
                "-v",
                "error",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgba",
                "-s",
                f"{genislik}x{yukseklik}",
                "-r",
                str(fps),
                "-i",
                "-",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-crf",
                "20",
                str(cikti),
            ],
            stdin=subprocess.PIPE,
        )

    def yaz(self, fig) -> None:
        fig.canvas.draw()
        self._proc.stdin.write(fig.canvas.buffer_rgba().tobytes())

    def kapat(self) -> None:
        self._proc.stdin.close()
        if self._proc.wait() != 0:
            raise RuntimeError("ffmpeg hata verdi")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.kapat()
