"""Model dosyalarını indir ve hash'le doğrula. Hash tutmazsa dosya kullanılmaz."""

import hashlib
import urllib.request
from pathlib import Path

from otomat.ayarlar import modeller


def _sha256(yol: Path) -> str:
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def indir(url: str, beklenen: str, hedef: Path) -> Path:
    if not hedef.exists() or _sha256(hedef) != beklenen:
        hedef.parent.mkdir(parents=True, exist_ok=True)
        gecici = hedef.with_suffix(hedef.suffix + ".part")
        urllib.request.urlretrieve(url, gecici)
        if _sha256(gecici) != beklenen:
            gecici.unlink()
            raise RuntimeError(f"hash tutmadı: {url}")
        gecici.replace(hedef)
    return hedef


def kokoro_dosyalari(dizin: Path) -> tuple[Path, Path]:
    t = modeller()["tts"]
    model = indir(t["model_url"], t["model_sha256"], dizin / "kokoro-v1.0.onnx")
    sesler = indir(t["sesler_url"], t["sesler_sha256"], dizin / "voices-v1.0.bin")
    return model, sesler
