"""Fotoğraf → derinlik haritası (Depth Anything V2 Small, ONNX, CPU). 2.5D parallax için kurgu bunu WebGL'de kullanır.

Neden: düz kare + yavaş yakınlaşma "slayt" hissi veriyor (11-20 izleyici geri bildirimi: "çok sıkıcı"). Derinlik
haritasıyla ön plan arka plandan farklı kayar; aynı fotoğraf kamera ile çekilmiş bir plan gibi okunur.
Model: onnx-community/depth-anything-v2-small (Apache-2.0), modeller/derinlik/da2s.onnx (~99 MB, git dışı).
Çıktı: görselle aynı boyutta 8 bit gri PNG, yakın = beyaz. Bulanıklaştırılır: keskin derinlik kenarı parallax'ta
yırtılır.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

MODEL = Path(__file__).resolve().parents[2] / "modeller" / "derinlik" / "da2s.onnx"
GIRDI = 518  # modelin eğitim çözünürlüğü (14'ün katı)
ORT = np.array([0.485, 0.456, 0.406], dtype=np.float32)
SAP = np.array([0.229, 0.224, 0.225], dtype=np.float32)


@lru_cache(maxsize=1)
def _oturum():
    import onnxruntime as ort

    return ort.InferenceSession(str(MODEL), providers=["CPUExecutionProvider"])


def harita(kaynak: Path, hedef: Path, bulanik: float = 6.0) -> Path:
    if hedef.exists() and hedef.stat().st_mtime >= kaynak.stat().st_mtime:
        return hedef
    im = Image.open(kaynak).convert("RGB")
    k = im.resize((GIRDI, GIRDI), Image.Resampling.BICUBIC)
    x = (np.asarray(k, dtype=np.float32) / 255.0 - ORT) / SAP
    x = x.transpose(2, 0, 1)[None]
    s = _oturum()
    d = s.run(None, {s.get_inputs()[0].name: x})[0].squeeze().astype(np.float32)
    lo, hi = np.percentile(d, 2), np.percentile(d, 98)
    d = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)
    out = Image.fromarray((d * 255).astype(np.uint8)).resize(im.size, Image.Resampling.BICUBIC)
    if bulanik:
        out = out.filter(ImageFilter.GaussianBlur(bulanik))
    hedef.parent.mkdir(parents=True, exist_ok=True)
    out.save(hedef, "PNG", optimize=True)
    return hedef
