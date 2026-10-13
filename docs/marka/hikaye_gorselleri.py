"""Hikâye kanallarının YouTube görselleri: profil (800, daire kırpılır), banner (2560×1440, içerik 1546×423 güvenli
alanda), filigran (150). Semboller `inkwell/master/sembol.svg`, `lanternbug/master/sembol.svg` (logo-design skill'i,
siyah master); renkler burada. SVG → PNG için skill'in render_png.py'si (Chrome) kullanılır.

    uv run python docs/marka/hikaye_gorselleri.py
"""

import random
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

KOK = Path(__file__).parent
RENDER = Path.home() / ".claude/skills/logo-design/scripts/render_png.py"
FELL = KOK / "fontlar/IMFellEnglish-Regular.ttf"

MARKA = {
    "inkwell": {
        "ad": "Inkwell Oddities",
        "slogan": "True stories too strange to make up",
        "zemin": "#F1E6CC",  # parşömen
        "murekkep": "#1C2B45",  # mürekkep mavisi
        "font": FELL,
    },
    "lanternbug": {
        "ad": "Lanternbug Tales",
        "slogan": "Aesop's fables, told straight",  # 10-13: çocuk kanalından genel kitleye (K-24)
        "zemin": "#1F2B4D",  # gece
        "govde": "#F6EBD9",  # krem
        "isik": "#FFB703",  # ateş böceği ışığı (altyazı vurgusuyla aynı)
        "font": FELL,
    },
}


def renkli_svg(ad: str, zemin: bool) -> str:
    m = MARKA[ad]
    svg = (KOK / ad / "master" / "sembol.svg").read_text(encoding="utf-8")
    if ad == "inkwell":
        svg = svg.replace('fill="#000"', f'fill="{m["murekkep"]}"')
    else:
        # son yol karın (evenodd, kitap delikli): ışık rengi; ayırıcı beyaz daire zemin rengi; gerisi gövde
        svg = svg.replace('fill="#fff"', f'fill="{m["zemin"]}"')
        parcalar = svg.rsplit('fill="#000" fill-rule="evenodd"', 1)
        svg = parcalar[0].replace('fill="#000"', f'fill="{m["govde"]}"') + f'fill="{m["isik"]}" fill-rule="evenodd"'
        svg += parcalar[1]
    if zemin:
        # daire kırpmasında sembol güvenli kalsın: %72 ölçek, ortada
        ic = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S).group(1)
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">'
            f'<rect width="256" height="256" fill="{m["zemin"]}"/>'
            f'<g transform="translate(36 34) scale(0.72)">{ic}</g></svg>'
        )
    return svg


def png(svg: str, yol: Path, boyut: int) -> Image.Image:
    gecici = yol.with_suffix(".svg")
    gecici.write_text(svg, encoding="utf-8")
    subprocess.run([sys.executable, str(RENDER), str(gecici), "--out-dir", str(yol.parent), "--size", str(boyut)],
                   check=True, capture_output=True)  # fmt: skip
    return Image.open(yol).convert("RGBA")


def isiltili_zemin(ad: str, g: int, y: int) -> Image.Image:
    m = MARKA[ad]
    r = random.Random(ad)
    if ad == "inkwell":
        zemin = Image.new("RGB", (g, y), m["zemin"])
        leke = Image.new("L", (g, y), 0)
        d = ImageDraw.Draw(leke)
        for _ in range(26):  # soluk mürekkep lekeleri, kenarlarda
            x = r.choice([r.uniform(0, g * 0.22), r.uniform(g * 0.78, g)])
            yy, rr = r.uniform(0, y), r.uniform(30, 160)
            d.ellipse((x - rr, yy - rr, x + rr, yy + rr), fill=r.randint(10, 26))
        leke = leke.filter(ImageFilter.GaussianBlur(40))
        zemin.paste(Image.new("RGB", (g, y), m["murekkep"]), (0, 0), leke)
        return zemin
    ust, alt = (31, 43, 77), (16, 22, 44)
    zemin = Image.new("RGB", (g, y))
    d = ImageDraw.Draw(zemin)
    for i in range(y):
        t = i / y
        d.line([(0, i), (g, i)], fill=tuple(round(a + (b - a) * t) for a, b in zip(ust, alt, strict=True)))
    isik = Image.new("RGBA", (g, y), (0, 0, 0, 0))
    di = ImageDraw.Draw(isik)
    for _ in range(70):  # uçuşan ateş böcekleri, güvenli alanın dışında yoğun
        x, yy = r.uniform(0, g), r.uniform(0, y)
        if abs(x - g / 2) < 780 and abs(yy - y / 2) < 220:
            continue
        rr = r.uniform(4, 11)
        di.ellipse((x - rr * 3, yy - rr * 3, x + rr * 3, yy + rr * 3), fill=(255, 183, 3, 40))
        di.ellipse((x - rr, yy - rr, x + rr, yy + rr), fill=(255, 214, 102, 230))
    zemin.paste(isik.filter(ImageFilter.GaussianBlur(3)), (0, 0), isik.filter(ImageFilter.GaussianBlur(3)))
    return zemin


def banner(ad: str, sembol: Image.Image, cikti: Path) -> None:
    m = MARKA[ad]
    g, y = 2560, 1440
    b = isiltili_zemin(ad, g, y)
    renk = m.get("murekkep", m.get("govde"))
    s = sembol.resize((300, 300), Image.LANCZOS)
    font = ImageFont.truetype(str(m["font"]), 150 if ad == "inkwell" else 128)
    kucuk = ImageFont.truetype(str(m["font"]), 54 if ad == "inkwell" else 46)
    d = ImageDraw.Draw(b)
    yazi_g = d.textlength(m["ad"], font=font)
    toplam = 300 + 50 + yazi_g
    x0 = (g - toplam) / 2  # güvenli alan 1546 px: toplam bunu aşmamalı
    assert toplam <= 1546, f"{ad}: banner içeriği güvenli alana sığmıyor ({toplam:.0f} px)"
    b.paste(s, (round(x0), (y - 300) // 2), s)
    ust = y / 2 - 105
    d.text((x0 + 350, ust), m["ad"], font=font, fill=renk if ad == "inkwell" else m["govde"])
    d.text((x0 + 356, ust + 160), m["slogan"], font=kucuk, fill=renk if ad == "inkwell" else m["isik"])
    b.save(cikti)


def main() -> None:
    for ad in MARKA:
        dizin = KOK / ad
        sembol = png(renkli_svg(ad, zemin=False), dizin / "master" / "sembol-renkli.png", 1024)
        profil = png(renkli_svg(ad, zemin=True), dizin / "profil-800.png", 800)
        profil.convert("RGB").save(dizin / "profil-800.png")
        profil.resize((150, 150), Image.LANCZOS).save(dizin / "filigran-150.png")
        banner(ad, sembol, dizin / "banner-2560x1440.png")
        print(ad, "->", sorted(p.name for p in dizin.glob("*.png")))


if __name__ == "__main__":
    main()
