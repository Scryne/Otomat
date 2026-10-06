"""Orbit Ruler sembolü: Ay'ın yörüngesi (halka) ve ona en yakın noktasında teğet geçen çentikli cetvel (asteroitin yolu).
Teğet noktasında küçük disk = asteroit, en yakın an. Merkezde Dünya.

Geometri parametrik; çıktı 256×256 viewBox, sınır kutusuna göre ortalanır. Renkli sürümde: halka ay grisi, Dünya mavi,
cetvel mor, asteroit nane (videodaki vurgu). Siyah sürüm tek path grubu.
Kullanım: python gen.py  → sembol-siyah.svg, sembol-koyu-zemin.svg, sembol-kucuk-siyah.svg
"""

import math
from pathlib import Path

BURADA = Path(__file__).parent
YUZEY, AY, DUNYA, MOR, NANE = "#04050b", "#c9ccd8", "#3f86f2", "#8b7cf6", "#5ef0c8"


def daire(cx: float, cy: float, r: float) -> str:
    return f"M{cx - r:.2f} {cy:.2f} A{r:.2f} {r:.2f} 0 1 0 {cx + r:.2f} {cy:.2f} A{r:.2f} {r:.2f} 0 1 0 {cx - r:.2f} {cy:.2f} Z"


def halka(cx: float, cy: float, r: float, w: float) -> str:
    dis, ic = r + w / 2, r - w / 2
    return (
        daire(cx, cy, dis)
        + f" M{cx - ic:.2f} {cy:.2f} A{ic:.2f} {ic:.2f} 0 1 1 {cx + ic:.2f} {cy:.2f} A{ic:.2f} {ic:.2f} 0 1 1 {cx - ic:.2f} {cy:.2f} Z"
    )


def cokgen(noktalar) -> str:
    return "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in noktalar) + " Z"


def geometri(kucuk: bool = False) -> dict:
    r, w = 66.0, 16.0 if kucuk else 13.0  # yörünge yarıçapı, halka kalınlığı
    aci = math.radians(-45)  # teğet noktası: sağ üst
    ux, uy = math.cos(aci), math.sin(aci)
    dx, dy = -uy, ux  # teğet yönü
    bosluk = 9.0 if kucuk else 8.0  # halka ile cetvel arası (ayrı okunsun)
    K = 14.0 if kucuk else 11.0  # cetvel kalınlığı
    L = 104.0  # cetvel yarı uzunluğu
    taban = r + w / 2 + bosluk  # cetvelin halkaya bakan kenarı (merkezden)

    def p(s: float, n: float) -> tuple[float, float]:
        return (ux * n + dx * s, uy * n + dy * s)

    parcalar = {
        "halka": ("halka", (0.0, 0.0, r, w)),
        "dunya": ("daire", (0.0, 0.0, 20.0 if kucuk else 17.0)),
        "cetvel": ("cokgen", [p(-L, taban), p(L, taban), p(L, taban + K), p(-L, taban + K)]),
        "centik": [],
        # asteroit yolun üstünde, en yakın noktada: cetvelin orta çizgisinde, cetvelden kalın (boncuk gibi okunur)
        "asteroit": ("daire", (*p(0, taban + K / 2), K * (1.05 if kucuk else 1.0))),
    }
    if not kucuk:  # çentikler: 16 px'te kaybolur, küçük kesimde yok
        adim = 26.0
        for i in range(-3, 4):
            if i == 0:
                continue  # orta: asteroit noktası orada
            s = i * adim
            h = 12.0 if i % 2 == 0 else 8.0
            parcalar["centik"].append(("cokgen", [p(s - 3, taban + K), p(s + 3, taban + K), p(s + 3, taban + K + h), p(s - 3, taban + K + h)]))
    return parcalar


def _noktalar(parcalar: dict):
    for ad, deger in parcalar.items():
        for tur, g in deger if ad == "centik" else [deger]:
            if tur == "cokgen":
                yield from g
            else:
                cx, cy, r = g[0], g[1], g[2] + (g[3] / 2 if tur == "halka" else 0)
                yield from [(cx - r, cy - r), (cx + r, cy + r)]


def svg(parcalar: dict, renkli: bool, zemin: str | None = None) -> str:
    xs, ys = zip(*_noktalar(parcalar), strict=True)
    boy = max(max(xs) - min(xs), max(ys) - min(ys))
    olcek = (256 - 2 * 18) / boy
    ox = 128 - (max(xs) + min(xs)) / 2 * olcek
    oy = 128 - (max(ys) + min(ys)) / 2 * olcek - 2  # optik merkez: bir tık yukarı

    def t(tur: str, g) -> str:
        if tur == "cokgen":
            return cokgen([(x * olcek + ox, y * olcek + oy) for x, y in g])
        cx, cy, r = g[0] * olcek + ox, g[1] * olcek + oy, g[2] * olcek
        return halka(cx, cy, r, g[3] * olcek) if tur == "halka" else daire(cx, cy, r)

    yol = {ad: t(*d) for ad, d in parcalar.items() if ad != "centik"}
    yol["centik"] = " ".join(t(*d) for d in parcalar["centik"])
    arka = f'<rect width="256" height="256" fill="{zemin}"/>' if zemin else ""
    if not renkli:
        # halka delikli (evenodd); gerisi birleşim (nonzero): asteroit diski cetvelle çakışınca oyulmasın
        dolu = " ".join(v for k, v in yol.items() if k != "halka")
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256"><title>Orbit Ruler</title>{arka}'
            f'<path fill-rule="evenodd" d="{yol["halka"]}"/><path d="{dolu}"/></svg>\n'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256"><title>Orbit Ruler</title>{arka}'
        f'<path fill-rule="evenodd" fill="{AY}" d="{yol["halka"]}"/>'
        f'<path fill="{DUNYA}" d="{yol["dunya"]}"/>'
        f'<path fill="{AY}" d="{yol["cetvel"]} {yol["centik"]}"/>'
        f'<path fill="{NANE}" d="{yol["asteroit"]}"/></svg>\n'
    )


if __name__ == "__main__":
    g, gk = geometri(), geometri(kucuk=True)
    (BURADA / "sembol-siyah.svg").write_text(svg(g, False), encoding="utf-8")
    (BURADA / "sembol-koyu-zemin.svg").write_text(svg(g, True, YUZEY), encoding="utf-8")
    (BURADA / "sembol-seffaf.svg").write_text(svg(g, True), encoding="utf-8")
    (BURADA / "sembol-kucuk-siyah.svg").write_text(svg(gk, False), encoding="utf-8")
    (BURADA / "sembol-kucuk-koyu-zemin.svg").write_text(svg(gk, True, YUZEY), encoding="utf-8")
    print("yazıldı")
