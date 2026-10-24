"""Arena Lore (spor kanalı, K-37) YouTube görselleri: profil (800, daire kırpılır), banner (2560×1440, içerik 1546×423
güvenli alanda), filigran (150). Sembol `arenalore/master/sembol.svg`: kemer kapılı A (arenanın kapısı, logo-design
skill'i; elenen konseptler `konsept-*.svg`). Kalıp `hikaye_gorselleri.py`.

    uv run python docs/marka/arena_gorselleri.py
"""

import random
import re
from pathlib import Path

from hikaye_gorselleri import KOK, png  # aynı klasörden çalıştırılır
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

AD = "ARENA LORE"
SLOGAN = "True sports stories: football, MMA, boxing"
ZEMIN = "#121214"  # mürekkep siyahı
ALTIN = "#FFD84D"  # futbol vurgusu; MMA #FF5A3D, boks #FFB703 (kanallar/spor/DESIGN.md)
KIRMIZI = (255, 90, 61)
FONT = KOK.parents[1] / "otomat/varliklar/fontlar/BarlowCondensed-Bold.ttf"
INCE = KOK.parents[1] / "otomat/varliklar/fontlar/BarlowCondensed-SemiBold.ttf"
DIZIN = KOK / "arenalore"


def renkli_svg(zemin: bool) -> str:
    svg = (DIZIN / "master" / "sembol.svg").read_text(encoding="utf-8").replace('fill="#000"', f'fill="{ALTIN}"')
    if zemin:
        ic = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S).group(1)
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">'
            f'<rect width="256" height="256" fill="{ZEMIN}"/>'
            f'<g transform="translate(36 38) scale(0.72)">{ic}</g></svg>'
        )
    return svg


def zemin(g: int, y: int) -> Image.Image:
    """Siyah zemin, kenarlarda grafik roman hız çizgileri (güvenli alanın dışında)."""
    b = Image.new("RGB", (g, y), ZEMIN)
    cizgi = Image.new("RGBA", (g, y), (0, 0, 0, 0))
    d = ImageDraw.Draw(cizgi)
    r = random.Random("arena")
    for _ in range(90):
        sol = r.random() < 0.5
        x = r.uniform(0, g * 0.3) if sol else r.uniform(g * 0.7, g)
        yy, uzun, kal = r.uniform(0, y), r.uniform(120, 520), r.randint(3, 9)
        renk = (*KIRMIZI, r.randint(50, 120)) if r.random() < 0.25 else (255, 216, 77, r.randint(25, 80))
        d.line([(x, yy), (x + uzun * (1 if sol else -1) * 0.94, yy - uzun * 0.34)], fill=renk, width=kal)
    cizgi = cizgi.filter(ImageFilter.GaussianBlur(1.2))
    bos = Image.new("L", (g, y), 255)  # ad ve sembolün arkası temiz kalsın
    ImageDraw.Draw(bos).rectangle(((g - 1800) // 2, (y - 560) // 2, (g + 1800) // 2, (y + 560) // 2), fill=0)
    cizgi.putalpha(ImageChops.multiply(cizgi.getchannel("A"), bos.filter(ImageFilter.GaussianBlur(90))))
    b.paste(cizgi, (0, 0), cizgi)
    return b


def banner(sembol: Image.Image, cikti: Path) -> None:
    g, y = 2560, 1440
    b = zemin(g, y)
    s = sembol.resize((300, 300), Image.LANCZOS)
    font = ImageFont.truetype(str(FONT), 210)
    kucuk = ImageFont.truetype(str(INCE), 58)
    d = ImageDraw.Draw(b)
    yazi_g = max(d.textlength(AD, font=font), d.textlength(SLOGAN, font=kucuk))
    toplam = 300 + 56 + yazi_g
    assert toplam <= 1546, f"banner içeriği güvenli alana sığmıyor ({toplam:.0f} px)"
    x0 = (g - toplam) / 2
    b.paste(s, (round(x0), (y - 300) // 2), s)
    ust = y / 2 - 150
    d.text((x0 + 356, ust), AD, font=font, fill="#FFFFFF")
    d.text((x0 + 362, ust + 222), SLOGAN, font=kucuk, fill=ALTIN)
    b.save(cikti)


def main() -> None:
    sembol = png(renkli_svg(zemin=False), DIZIN / "master" / "sembol-renkli.png", 1024)
    profil = png(renkli_svg(zemin=True), DIZIN / "profil-800.png", 800)
    profil.convert("RGB").save(DIZIN / "profil-800.png")
    profil.resize((150, 150), Image.LANCZOS).save(DIZIN / "filigran-150.png")
    banner(sembol, DIZIN / "banner-2560x1440.png")
    print(sorted(p.name for p in DIZIN.glob("*.png")))


if __name__ == "__main__":
    main()
