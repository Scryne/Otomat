"""Birleştirme: video ile ses kanalı aynı uzunlukta, tasarlanan kapanış karesi (KUYRUK) kesilmiyor."""

import re
import subprocess

import imageio_ffmpeg

from otomat.uretim import birlestir

FF = imageio_ffmpeg.get_ffmpeg_exe()


def _sure(yol, akis):
    """ffprobe yok; akışı ayrı kopyalayıp ffmpeg'in 'time=' satırından süreyi okur."""
    r = subprocess.run([FF, "-i", str(yol), "-map", akis, "-f", "null", "-"], capture_output=True, text=True)
    s, d, sn = re.findall(r"time=(\d+):(\d+):([\d.]+)", r.stderr)[-1]
    return int(s) * 3600 + int(d) * 60 + float(sn)


def test_kapanis_karesi_kesilmiyor(tmp_path):
    video, wav = tmp_path / "sessiz.mp4", tmp_path / "ses.wav"
    for girdi, yol in (("color=c=black:s=64x64:r=30:d=3", video), ("sine=f=440:d=1.8", wav)):
        subprocess.run([FF, "-v", "error", "-f", "lavfi", "-i", girdi, str(yol)], check=True)
    cikti = birlestir(video, wav, tmp_path / "video.mp4")
    assert abs(_sure(cikti, "0:v") - 3.0) < 0.1
    assert abs(_sure(cikti, "0:a") - 3.0) < 0.15
