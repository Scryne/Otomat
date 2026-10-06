"""Orbit Ruler YouTube varlıkları: profil (800), banner (2560×1440, içerik 1546×423 güvenli alanda), filigran (150).

Sembol gen.py'nin şeffaf SVG'sinden render_png.py ile rasterleşir; yazı Space Grotesk (OFL, otomat/varliklar/fontlar)
ile matplotlib'de çizilir (çıktı PNG; canlı metin sorunu yok). Kullanım: uv run python youtube.py
"""

import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from PIL import Image  # noqa: E402

BURADA = Path(__file__).parent
CIKTI = BURADA.parent / "youtube"
FONT = BURADA.parents[3] / "otomat" / "varliklar" / "fontlar"
RENDER = Path("C:/Users/scryn/.claude/skills/logo-design/scripts/render_png.py")
YUZEY, AY, NANE, MOR = "#04050b", "#c9ccd8", "#5ef0c8", "#9aa3c7"


def sembol_png(boyut: int) -> Image.Image:
    gecici = BURADA / "renders"  # ara dosyalar (git dışı)
    subprocess.run([sys.executable, str(RENDER), str(BURADA / "sembol-seffaf.svg"), "--out-dir", str(gecici),
                    "--size", str(boyut)], check=True, capture_output=True)  # fmt: skip
    return Image.open(gecici / "sembol-seffaf.png").convert("RGBA")


def profil() -> None:
    # YouTube profil resmini daireye kırpar: sembol dairenin içine sığsın (çapın ~%70'i)
    zemin = Image.new("RGBA", (800, 800), YUZEY)
    s = sembol_png(560)
    zemin.alpha_composite(s, (120, 116))
    zemin.convert("RGB").save(CIKTI / "profil-800.png")


def filigran() -> None:
    s = sembol_png(150)
    s.save(CIKTI / "filigran-150.png")


def banner() -> None:
    W, H = 2560, 1440
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=YUZEY)
    # güvenli alan 1546×423 ortada: sembol solda, ad + alt yazı sağında
    sembol = sembol_png(340)
    tmp = BURADA / "renders" / "_banner_sembol.png"
    sembol.save(tmp)
    ax = fig.add_axes(((W / 2 - 740) / W, (H / 2 - 170) / H, 340 / W, 340 / H))
    ax.imshow(plt.imread(tmp))
    ax.axis("off")
    x = (W / 2 - 350) / W
    fig.text(x, 0.53, "Orbit Ruler", color="#eef1ff", va="center", ha="left",
             fontproperties=FontProperties(fname=str(FONT / "SpaceGrotesk-Bold.ttf"), size=118))  # fmt: skip
    fig.text(x + 0.002, 0.448, "Space, measured.", color=MOR, va="center", ha="left",
             fontproperties=FontProperties(fname=str(FONT / "SpaceGrotesk-Medium.ttf"), size=52))  # fmt: skip
    # ince cetvel çizgisi: güvenli alanın altında, masaüstünde görünen genişlikte süs
    for i in range(0, 61):
        xx = (W / 2 - 1100 + i * 2200 / 60) / W
        h = 0.03 if i % 5 == 0 else 0.015
        fig.add_artist(plt.Line2D([xx, xx], [0.30, 0.30 + h], color=AY if i % 5 else NANE, alpha=0.35 if i % 5 else 0.8,
                                  lw=3))  # fmt: skip
    fig.savefig(CIKTI / "banner-2560x1440.png", facecolor=YUZEY)
    plt.close(fig)


if __name__ == "__main__":
    CIKTI.mkdir(exist_ok=True)
    profil()
    filigran()
    banner()
    print("yazıldı:", sorted(p.name for p in CIKTI.iterdir()))
