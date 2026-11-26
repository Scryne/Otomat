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


def html(metin: str, gorsel: str, vurgu: str = "", genislik: int = 760) -> str:
    kelimeler = metin.upper().split()
    v = vurgu.upper()
    satir = " ".join(f'<span class="{"v" if k.strip(".,!?") == v else ""}">{_e(k)}</span>' for k in kelimeler)
    boy = 150 if len(metin) <= 14 else (124 if len(metin) <= 22 else 104)
    if genislik < 760:
        boy = int(boy * 0.9)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8" /><meta name="viewport" content="width={W}, height={H}" />
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html, body {{ width:{W}px; height:{H}px; overflow:hidden; background:{RENK["murekkep"]}; }}
  #root {{ position:relative; width:100%; height:100%; overflow:hidden; }}
  .foto {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }}
  .karart {{ position:absolute; inset:0; background:linear-gradient(90deg, rgba(0,0,0,.82) 0%, rgba(0,0,0,.45) 48%,
             rgba(0,0,0,0) 72%); }}
  .metin {{ position:absolute; left:56px; top:50%; transform:translateY(-50%); width:{genislik}px;
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


def kesitli_zemin(ham: Path, kesit_png: Path, hedef: Path) -> Path:
    """Kesitli kapak zemini: koyu, bulanık kendi fotoğrafı + konunun arkasında sıcak ışık halkası; konu sağda, kadrajı
    dolduracak boyda, ince beyaz kontur ve gölgeyle öne çıkar. Sol yarı yazıya kalır. 11-26: kalabalık fotoğrafında
    yüz küçük kalıyor, metin yüzü örtüyordu (vidIQ: breakout kapaklarının %89'unda belirgin yüz/yüksek kontrast)."""
    from PIL import ImageDraw, ImageFilter, ImageOps

    from otomat.trend.kesik import kutu

    zemin = ImageOps.fit(Image.open(ham).convert("RGB"), (W, H), Image.LANCZOS)
    zemin = zemin.filter(ImageFilter.GaussianBlur(28))
    zemin = Image.blend(zemin, Image.new("RGB", (W, H), (10, 10, 14)), 0.62).convert("RGBA")
    k = Image.open(kesit_png).convert("RGBA")
    sol, ust, sag, alt = kutu(kesit_png)
    k = k.crop((int(sol * k.width), int(ust * k.height), int(sag * k.width), int(alt * k.height)))
    oran = k.width / k.height
    boy = int(H * 1.02) if oran < 1.1 else int(min(H * 0.95, W * 0.58 / oran))  # kişi: tam boy; nesne: genişliğe göre
    k = k.resize((max(1, int(boy * oran)), boy), Image.LANCZOS)
    x = W - k.width - (24 if oran < 1.1 else 40)
    x = max(int(W * 0.38), x)
    y = H - k.height + (int(H * 0.04) if oran < 1.1 else -int((H - k.height) / 2))
    # sıcak ışık halkası (konunun arkasında)
    hale = Image.new("L", (W, H), 0)
    ImageDraw.Draw(hale).ellipse((x - 80, y + 40, x + k.width + 80, y + k.height + 260), fill=150)
    hale = hale.filter(ImageFilter.GaussianBlur(120))
    zemin.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (W, H), (255, 176, 40)).split(), hale)))
    alfa = k.getchannel("A")
    golge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    golge.paste((0, 0, 0, 170), (x + 14, y + 18), alfa)
    zemin.alpha_composite(golge.filter(ImageFilter.GaussianBlur(18)))
    kontur = alfa.filter(ImageFilter.MaxFilter(9))
    beyaz = Image.new("RGBA", k.size, (255, 255, 255, 0))
    beyaz.putalpha(kontur)
    zemin.alpha_composite(beyaz, (x, y))
    zemin.alpha_composite(k, (x, y))
    zemin.convert("RGB").save(hedef, "JPEG", quality=94)
    return hedef


def baskili_zemin(ham: Path, hedef: Path) -> Path:
    """Kesit çıkmayan görsel (diyagram, mekân, nesne) için kapak zemini: görsel sağda eğik bir baskı (beyaz kenar,
    gölge), altında kendi koyu, bulanık büyütmesi; sol yarı yazıya kalır. 11-26 Riemann: tam ekran diyagramın üstüne
    binen yazı ikisini de zayıflatıyordu."""
    from PIL import ImageFilter, ImageOps

    im = ImageOps.exif_transpose(Image.open(ham))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        kagit = Image.new("RGBA", im.size, (244, 242, 236, 255))
        kagit.alpha_composite(im)
        im = kagit
    im = im.convert("RGB")
    zemin = ImageOps.fit(im, (W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(24))
    zemin = Image.blend(zemin, Image.new("RGB", (W, H), (10, 10, 14)), 0.6).convert("RGBA")
    kopya = im.copy()
    kopya.thumbnail((int(W * 0.5), int(H * 0.82)), Image.LANCZOS)
    kenar = max(8, kopya.width // 40)
    kart = (
        ImageOps.expand(kopya, border=kenar, fill=(242, 238, 230))
        .convert("RGBA")
        .rotate(2.2, resample=Image.BICUBIC, expand=True)
    )
    golge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x, y = W - kart.width - 40, (H - kart.height) // 2
    golge.paste((0, 0, 0, 170), (x + 16, y + 22), kart.getchannel("A"))
    zemin.alpha_composite(golge.filter(ImageFilter.GaussianBlur(20)))
    zemin.alpha_composite(kart, (x, y))
    zemin.convert("RGB").save(hedef, "JPEG", quality=94)
    return hedef


def uret(metin: str, gorsel: Path, dizin: Path, vurgu: str = "", ham: Path | None = None) -> Path:
    """`ham` (indirilmiş özgün fotoğraf) verilir ve konusu kesilebilirse kesitli düzen, kesilemezse baskı düzeni;
    `ham` yoksa tam ekran fotoğraf."""
    dizin.mkdir(parents=True, exist_ok=True)
    (dizin / "assets").mkdir(exist_ok=True)
    kesit_png = None
    if ham is not None:
        from otomat.trend.kesik import kes

        kesit_png = kes(ham, dizin / "kesit.png")
    if kesit_png:
        kesitli_zemin(ham, kesit_png, dizin / "assets" / "kapak.jpg")  # type: ignore[arg-type]
    elif ham is not None:
        baskili_zemin(ham, dizin / "assets" / "kapak.jpg")
    else:
        shutil.copy2(gorsel, dizin / "assets" / "kapak.jpg")
    if not vurgu:
        # en uzun kelime vurgulanır (çoğunlukla konunun adı); noktalama düşer, yoksa "UNDERSTOOD." eşleşmiyordu (11-26)
        vurgu = max(metin.split(), key=len).strip(".,!?:;")
    (dizin / "index.html").write_text(
        html(metin, "assets/kapak.jpg", vurgu, 600 if ham is not None else 760), encoding="utf-8"
    )
    kare = kurgu.kareler(dizin, [0.0])
    if not kare:
        raise RuntimeError("kapak karesi alınamadı")
    hedef = dizin / "kapak.jpg"
    Image.open(kare[0]).convert("RGB").resize((W, H)).save(hedef, "JPEG", quality=90)
    return hedef
