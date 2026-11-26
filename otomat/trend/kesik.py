"""Fotoğraftan konu kesiti (şeffaf PNG): kapakta büyük yüz, videoda "yazı kişinin arkasında" katmanı.

Model HyperFrames'in kendi `remove-background` komutu (yerel ONNX, CPU'da görsel başına ~1 sn; 11-26 denemesinde saç
telleri dahil temiz). Kesit her zaman işe yaramaz (manzara, kalabalık, araba yığını): kaplama oranı ve en büyük
parçanın payı ölçülür, tek ve belirgin bir konu yoksa `None` döner, çağıran eski düzene düşer.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PIL import Image

from otomat.trend.kurgu import HF_ORTAM, MOTOR_DIZIN

KAPLAMA = (0.08, 0.72)  # konu karenin %8'inden küçükse kayboluyor, %72'den büyükse kesit değil bütün kare


def kes(kaynak: Path, hedef: Path) -> Path | None:
    """Kesit PNG'si yolu; konu belirgin değilse ya da model düşerse None."""
    if not hedef.exists():
        hedef.parent.mkdir(parents=True, exist_ok=True)
        bin_ = MOTOR_DIZIN / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"
        # CLI proje klasöründe (cwd=MOTOR_DIZIN) çalışır: göreli yol orada bulunmuyordu
        komut = ["node", str(bin_), "remove-background", str(kaynak.resolve()), "-o", str(hedef.resolve())]
        r = subprocess.run(komut, cwd=MOTOR_DIZIN, env={**os.environ, **HF_ORTAM}, capture_output=True, text=True,
                           timeout=600)  # fmt: skip
        if r.returncode != 0 or not hedef.exists():
            print(f"kesit düştü ({kaynak.name}): {(r.stderr or r.stdout)[-200:]}", flush=True)
            return None
    return hedef if belirgin(hedef) else None


def belirgin(png: Path) -> bool:
    """Tek, belirgin konu: alfa kaplaması KAPLAMA aralığında ve kaplamanın çoğu tek bölgede (kalabalıkta kesit
    parça parça çıkar)."""
    with Image.open(png) as im:
        a = im.getchannel("A").resize((96, 96))
    p = [1 if v > 128 else 0 for v in a.getdata()]
    oran = sum(p) / len(p)
    if not KAPLAMA[0] <= oran <= KAPLAMA[1]:
        return False
    # en büyük bağlı bölge (4-komşu) toplam konunun ≥ %80'i
    gorulen = [False] * len(p)
    en_buyuk = 0
    for i, v in enumerate(p):
        if not v or gorulen[i]:
            continue
        yigin, n = [i], 0
        gorulen[i] = True
        while yigin:
            j = yigin.pop()
            n += 1
            x, y = j % 96, j // 96
            for k in (j - 1 if x else -1, j + 1 if x < 95 else -1, j - 96 if y else -1, j + 96 if y < 95 else -1):
                if k >= 0 and p[k] and not gorulen[k]:
                    gorulen[k] = True
                    yigin.append(k)
        en_buyuk = max(en_buyuk, n)
    return en_buyuk >= 0.8 * sum(p)


def kutu(png: Path) -> tuple[float, float, float, float]:
    """Konunun kesit içindeki sınır kutusu, oran olarak (sol, üst, sağ, alt)."""
    with Image.open(png) as im:
        a = im.getchannel("A")
        b = a.point(lambda v: 255 if v > 128 else 0).getbbox() or (0, 0, im.width, im.height)
        return b[0] / im.width, b[1] / im.height, b[2] / im.width, b[3] / im.height
