"""Görsel hazırlığı: indirilen lisanslı fotoğraf → kurgunun beklediği 1920×1080 (yatay) ya da 1080×1920 (dikey) kare.

Yön tutmayan fotoğraf (dikey portre yatay videoda) kırpılıp yüzü kaybetmesin diye kendi bulanık, karartılmış
kopyasının üstüne ortalanır. HyperFrames kuralı: görüntüye bulanıklık/renk CSS filtresiyle değil önceden işlenerek
verilir (skills/hyperframes SKILL.md, kural 11); burada PIL ile bir kez yapılır.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def hazirla(kaynak: Path, hedef: Path, boyut: tuple[int, int] = (1920, 1080), kalite: int = 88) -> Path:
    if hedef.exists() and hedef.stat().st_mtime >= kaynak.stat().st_mtime:
        return hedef
    hedef.parent.mkdir(parents=True, exist_ok=True)
    ham = ImageOps.exif_transpose(Image.open(kaynak))
    if diyagram(kaynak):
        cikti = kagitta(ham, boyut)
        cikti.save(hedef, "JPEG", quality=kalite, optimize=True)
        return hedef
    im = renk(ham.convert("RGB"))
    gw, gh = boyut
    oran_hedef, oran = gw / gh, im.width / im.height
    if abs(oran - oran_hedef) / oran_hedef < 0.28:  # yakın oran: doldurarak kırp (hafif üst ağırlıklı; yüzler üstte)
        cikti = ImageOps.fit(im, boyut, Image.LANCZOS, centering=(0.5, 0.4))
    else:
        cikti = baski(im, boyut, kaynak.name)
    cikti.save(hedef, "JPEG", quality=kalite, optimize=True)
    return hedef


KAGIT = (244, 242, 236)


def diyagram(kaynak: Path) -> bool:
    """Makale diyagramı/grafiği: saydam zeminli ya da çoğu beyaz PNG (Commons SVG'yi PNG olarak verir; bazıları
    saydam, bazıları opak beyaz zeminli). Fotoğrafta karenin yarısından fazlası neredeyse beyaz olmaz."""
    try:
        with Image.open(kaynak) as im:
            if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
                if im.convert("RGBA").getchannel("A").getextrema()[0] < 250:
                    return True
            if kaynak.suffix.lower() != ".png":
                return False
            gri = im.convert("L").resize((96, 96))
            return sum(1 for v in gri.getdata() if v > 235) / (96 * 96) > 0.55
    except OSError:
        return False


def kagitta(ham: Image.Image, boyut: tuple[int, int]) -> Image.Image:
    """Diyagram kâğıt zeminde kadrajın %92'sini kaplar (renk derecelendirmesi ve baskı düzeni yok). 11-26 eleştirmen:
    baskı olarak küçük kalan diyagramın yazıları okunmuyordu (31 bulgu) ve derinlik haritası düz ızgarayı büküyordu."""
    gw, gh = boyut
    ham = ham.convert("RGBA")
    kopya = ham.copy()
    kopya.thumbnail((int(gw * 0.92), int(gh * 0.92)), Image.LANCZOS)
    zemin = Image.new("RGBA", boyut, (255, 255, 255, 255))  # beyaz: kâğıtla çarpılınca düz kâğıt rengi
    zemin.alpha_composite(kopya, ((gw - kopya.width) // 2, (gh - kopya.height) // 2))
    # opak beyaz zeminli diyagram kâğıdın üstünde yama gibi duruyordu: kâğıtla çarpılınca beyaz kâğıda erir, çizgi kalır
    from PIL import ImageChops

    return ImageChops.multiply(zemin.convert("RGB"), Image.new("RGB", boyut, KAGIT))


def _egri(x: float, kanal: str) -> int:
    """Film tonu: siyah hafif kalkar (0 → 12), beyaz yumuşar (255 → 246), ortada hafif S; gölge mavi-yeşile,
    ışık sıcağa kayar (bölünmüş ton, 3-4 birim; göze batmaz, fotoğrafları aynı aileye sokar)."""
    t = x / 255
    s_ = t + 0.08 * math.sin(2 * math.pi * t) * -0.5  # yumuşak S: gölge biraz iner, ışık biraz çıkar
    y = 12 + s_ * (246 - 12)
    golge, isik = (1 - t) ** 2, t**2
    kay = {"r": -2 * golge + 4 * isik, "g": 0.5 * golge + 1 * isik, "b": 3.5 * golge - 4 * isik}[kanal]
    return max(0, min(255, round(y + kay)))


_LUT = [_egri(i, k) for k in "rgb" for i in range(256)]


def renk(im: Image.Image) -> Image.Image:
    """Bütün fotoğraflara aynı derecelendirme: pozlama hafifçe dengelenir, doygunluk %12 iner, film tonu uygulanır.
    11-26: Commons fotoğrafları (stüdyo flaşı, sarı salon ışığı, gri gün) art arda gelince renkleri birbirini tutmuyor,
    video derlenmiş klasör gibi görünüyordu; belgesel kurgusu tek bir "look" taşır. Önceden işlenir (HyperFrames kural
    11: görüntüye renk CSS filtresiyle değil önceden verilir)."""
    im = ImageOps.autocontrast(im, cutoff=0.4, preserve_tone=True)
    im = ImageEnhance.Color(im).enhance(0.88)
    return im.point(_LUT)


def baski(im: Image.Image, boyut: tuple[int, int], ad: str) -> Image.Image:
    """Yön tutmayan fotoğraf masaya konmuş bir baskı gibi durur: beyaz kenar, yumuşak gölge, ±1,6° eğim, kenara yakın
    yerleşim (karşı taraf yazıya kalır); altında kendi koyu, sıcak tonlu, bulanık büyütmesi. 11-26: ortalanmış
    fotoğraf + bulanık yan dolgu (pillarbox) videoyu "ucuz slayt" gösteriyordu; belgesel kurgusu fotoğrafı nesne
    olarak sahneler. Yerleşim ve eğim dosya adından türer (tekrarlanabilir, komşu sahneler farklı)."""
    gw, gh = boyut
    iz = sum(ad.encode()) % 997
    # zemin: aynı fotoğraf alan derinliği gibi (orta bulanık, şekil ve renk seçilir) + kenarlara koyulaşan vinyet.
    # 11-26 eleştirmen: 46 px bulanık + %55 koyu düz griye dönüyor, küçük baskı "boş kadrajda yüzüyor" (36 bulgu)
    zemin = ImageOps.fit(im, boyut, Image.LANCZOS).filter(ImageFilter.GaussianBlur(16))
    zemin = Image.blend(zemin, Image.new("RGB", boyut, (16, 13, 11)), 0.42)
    maske = Image.new("L", (64, 36), 0)
    for y in range(36):
        for x in range(64):
            d = (((x - 31.5) / 32) ** 2 + ((y - 17.5) / 18) ** 2) ** 0.5
            maske.putpixel((x, y), int(min(1.0, max(0.0, (d - 0.45) / 0.75)) * 200))
    zemin = Image.composite(Image.new("RGB", boyut, (8, 7, 6)), zemin, maske.resize(boyut, Image.BILINEAR))
    yatay_boyut = gw > gh
    # yatay videoda boy sınırı 0,74: kamera (×1,12) ve yakın plan kesmesi (×1,16) altında kadraja sığsın (11-26
    # eleştirmen: 0,84'te eğik baskının alt/üst kenarı kesiliyordu)
    oran_ = 0.74 if yatay_boyut else 0.62
    kopya = im.copy()
    kopya.thumbnail((int(gw * (0.9 if not yatay_boyut else 0.6)), int(gh * oran_ if yatay_boyut else gh * 0.5)),
                    Image.LANCZOS)  # fmt: skip
    kenar = max(10, kopya.width // 42)
    kart = ImageOps.expand(kopya, border=kenar, fill=(242, 238, 230)).convert("RGBA")
    aci = ((iz % 7) - 3) * 0.55  # -1,65° … +1,65°
    kart = kart.rotate(aci, resample=Image.BICUBIC, expand=True)
    golge = Image.new("RGBA", (kart.width + 120, kart.height + 120), (0, 0, 0, 0))
    golge.paste((0, 0, 0, 150), (60, 60, 60 + kart.width, 60 + kart.height), kart.split()[3])
    golge = golge.filter(ImageFilter.GaussianBlur(28))
    if yatay_boyut:
        sag = iz % 2 == 0
        x = int(gw * (0.62 if sag else 0.38) - kart.width / 2)
        y = (gh - kart.height) // 2 + (iz % 3 - 1) * 12
    else:
        x = (gw - kart.width) // 2
        y = int(gh * 0.36 - kart.height / 2)
    zemin = zemin.convert("RGBA")
    zemin.alpha_composite(golge, (max(0, x - 60 + 18), max(0, y - 60 + 26)))
    zemin.alpha_composite(kart, (max(0, x), max(0, y)))
    return zemin.convert("RGB")


def dolgulu(kaynak: Path, boyut: tuple[int, int] = (1920, 1080)) -> bool:
    """`hazirla` bu görseli bulanık dolgunun üstüne mi koydu (yön tutmuyor)."""
    hedef = boyut[0] / boyut[1]
    return abs(oran(kaynak) - hedef) / hedef >= 0.28


def oran(kaynak: Path) -> float:
    with Image.open(kaynak) as im:
        return im.width / im.height


def fark_izi(yol: Path) -> int:
    """64 bitlik fark özeti (dHash): yeniden boyut/kırpma/sıkıştırmada aynı kalır, farklı fotoğrafta ayrışır."""
    with Image.open(yol) as im:
        g = ImageOps.exif_transpose(im).convert("L").resize((9, 8), Image.LANCZOS)
    p = list(g.getdata())
    return sum(1 << i for i in range(64) if p[(i // 8) * 9 + i % 8] > p[(i // 8) * 9 + i % 8 + 1])


def yakin_kopyalari_ele(gorseller: list[dict], esik: int = 10) -> list[dict]:
    """Aynı fotoğrafın kırpılmış/küçültülmüş kopyalarını havuzdan atar; büyük olan kalır. 11-26 Bond havuzunda
    "pierce-brosnan-…" ve "…-cropped" ikilileri ile üç neredeyse aynı Vauxhall Köprüsü karesi ayrı görsel sayılıp
    videoda tekrar gibi görünüyordu."""
    import re

    def ad(g: dict) -> str:
        return re.sub(r"[-_ (]*cropped\)?|\.\w+$", "", Path(g["yerel"]).name.lower())

    def alan(g: dict) -> int:
        try:
            with Image.open(g["yerel"]) as im:
                return im.width * im.height
        except OSError:
            return 0

    sirali = sorted(gorseller, key=alan, reverse=True)
    kalan: list[tuple[dict, int, str]] = []
    for g in sirali:
        try:
            iz = fark_izi(Path(g["yerel"]))
        except OSError:
            continue
        if any(a == ad(g) or bin(iz ^ k).count("1") <= esik for _, k, a in kalan):
            continue
        kalan.append((g, iz, ad(g)))
    tut = {id(g) for g, _, _ in kalan}
    return [g for g in gorseller if id(g) in tut]  # özgün sıra (makale görselleri önce) korunur
