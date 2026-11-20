"""Görsel hazırlığı: indirilen lisanslı fotoğraf → kurgunun beklediği 1920×1080 (yatay) ya da 1080×1920 (dikey) kare.

Yön tutmayan fotoğraf (dikey portre yatay videoda) kırpılıp yüzü kaybetmesin diye kendi bulanık, karartılmış
kopyasının üstüne ortalanır. HyperFrames kuralı: görüntüye bulanıklık/renk CSS filtresiyle değil önceden işlenerek
verilir (skills/hyperframes SKILL.md, kural 11); burada PIL ile bir kez yapılır.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFilter, ImageOps


def hazirla(kaynak: Path, hedef: Path, boyut: tuple[int, int] = (1920, 1080), kalite: int = 88) -> Path:
    if hedef.exists() and hedef.stat().st_mtime >= kaynak.stat().st_mtime:
        return hedef
    hedef.parent.mkdir(parents=True, exist_ok=True)
    im = ImageOps.exif_transpose(Image.open(kaynak)).convert("RGB")
    gw, gh = boyut
    oran_hedef, oran = gw / gh, im.width / im.height
    if abs(oran - oran_hedef) / oran_hedef < 0.28:  # yakın oran: doldurarak kırp (hafif üst ağırlıklı; yüzler üstte)
        cikti = ImageOps.fit(im, boyut, Image.LANCZOS, centering=(0.5, 0.4))
    else:
        zemin = ImageOps.fit(im, boyut, Image.LANCZOS).filter(ImageFilter.GaussianBlur(38))
        zemin = Image.blend(zemin, Image.new("RGB", boyut, (12, 12, 14)), 0.3)
        kopya = im.copy()
        kopya.thumbnail((int(gw * 0.94), int(gh * 0.94)), Image.LANCZOS)
        zemin.paste(kopya, ((gw - kopya.width) // 2, (gh - kopya.height) // 2))
        cikti = zemin
    cikti.save(hedef, "JPEG", quality=kalite, optimize=True)
    return hedef


def oran(kaynak: Path) -> float:
    with Image.open(kaynak) as im:
        return im.width / im.height
