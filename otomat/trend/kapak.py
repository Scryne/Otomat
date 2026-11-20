"""Kapak: 1280×720 tek kare. Tam ekran gerçek fotoğraf + 2-5 kelime, yüksek kontrast, tek odak.

vidIQ 500 breakout kapağı [İ]: %89'u yüz ya da yüksek kontrast, yazılıların medyanı 5 kelime, abartılı ifade yalnız
%5. Yüzsüz kanalda odak: fotoğraftaki tek nesne + sarı blokta kısa metin. HyperFrames `snapshot` ile PNG'ye alınır.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

from otomat.trend import kurgu
from otomat.trend.kurgu import RENK, _e

W, H = 1280, 720


def html(metin: str, gorsel: str, vurgu: str = "") -> str:
    kelimeler = metin.upper().split()
    v = vurgu.upper()
    satir = " ".join(f'<span class="{"v" if k.strip(".,!?") == v else ""}">{_e(k)}</span>' for k in kelimeler)
    boy = 150 if len(metin) <= 14 else (124 if len(metin) <= 22 else 104)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8" /><meta name="viewport" content="width={W}, height={H}" />
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html, body {{ width:{W}px; height:{H}px; overflow:hidden; background:{RENK["murekkep"]}; }}
  #root {{ position:relative; width:100%; height:100%; overflow:hidden; }}
  .foto {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }}
  .karart {{ position:absolute; inset:0; background:linear-gradient(90deg, rgba(0,0,0,.82) 0%, rgba(0,0,0,.45) 48%,
             rgba(0,0,0,0) 72%); }}
  .metin {{ position:absolute; left:56px; top:50%; transform:translateY(-50%); width:760px;
            font-family:'League Gothic', sans-serif; font-size:{boy}px; line-height:.9; color:#fff;
            text-shadow:0 6px 24px rgba(0,0,0,.6); }}
  .metin span {{ display:inline; }}
  .metin span.v {{ color:#111; background:{RENK["vurgu"]}; padding:0 10px; box-decoration-break:clone; }}
  .serit {{ position:absolute; left:56px; top:64px; width:120px; height:14px; background:{RENK["vurgu"]}; }}
</style></head>
<body><div id="root" data-composition-id="main" data-start="0" data-duration="1" data-width="{W}" data-height="{H}"
data-no-timeline>
  <img class="foto" src="{_e(gorsel)}" alt="">
  <div class="karart"></div>
  <div class="serit"></div>
  <div class="metin">{satir}</div>
</div></body></html>
"""


def uret(metin: str, gorsel: Path, dizin: Path, vurgu: str = "") -> Path:
    dizin.mkdir(parents=True, exist_ok=True)
    (dizin / "assets").mkdir(exist_ok=True)
    shutil.copy2(gorsel, dizin / "assets" / "kapak.jpg")
    if not vurgu:
        vurgu = max(metin.split(), key=len)  # en uzun kelime vurgulanır (çoğunlukla konunun adı)
    (dizin / "index.html").write_text(html(metin, "assets/kapak.jpg", vurgu), encoding="utf-8")
    kare = kurgu.kareler(dizin, [0.0])
    if not kare:
        raise RuntimeError("kapak karesi alınamadı")
    hedef = dizin / "kapak.jpg"
    Image.open(kare[0]).convert("RGB").resize((W, H)).save(hedef, "JPEG", quality=90)
    return hedef
