"""Görsel kimlik: token'lar DESIGN.md frontmatter'ından okunur (tek kaynak), fontlar paketle gelir."""

import re
from functools import cache

import yaml
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties

from otomat.ayarlar import KOK, VARLIKLAR

FONT_DOSYALARI = {
    ("Barlow Condensed", 700): "BarlowCondensed-Bold.ttf",
    ("Barlow Condensed", 600): "BarlowCondensed-SemiBold.ttf",
    ("Barlow", 500): "Barlow-Medium.ttf",
    ("Barlow", 400): "Barlow-Regular.ttf",
}
GENISLIK, YUKSEKLIK = 1080, 1920  # token'ların piksel referansı


@cache
def tokenlar() -> dict:
    metin = (KOK / "DESIGN.md").read_text(encoding="utf-8")
    eslesme = re.match(r"^---\n(.*?)\n---", metin, re.S)
    if not eslesme:
        raise RuntimeError("DESIGN.md frontmatter yok")
    return yaml.safe_load(eslesme.group(1))


def renk(ad: str) -> str:
    return tokenlar()["colors"][ad]


def _px(deger: str) -> float:
    return float(str(deger).removesuffix("px"))


@cache
def _font_yolu(aile: str, agirlik: int) -> str:
    yol = VARLIKLAR / "fontlar" / FONT_DOSYALARI[(aile, agirlik)]
    font_manager.fontManager.addfont(str(yol))
    return str(yol)


def font(rol: str, olcek: float = 1.0, boyut_carpani: float = 1.0) -> FontProperties:
    """Tipografi rolünden FontProperties. Boyut px → pt (dpi 100'de 1 px = 0,72 pt)."""
    t = tokenlar()["typography"][rol]
    yol = _font_yolu(t["fontFamily"], int(t["fontWeight"]))
    return FontProperties(fname=yol, size=_px(t["fontSize"]) * 0.72 * olcek * boyut_carpani)


def guvenli_alan() -> dict[str, float]:
    """Kare kesirleri cinsinden güvenli alan sınırları (0..1, alt sol köşe orijin)."""
    s = tokenlar()["spacing"]
    return {
        "ust": 1 - _px(s["safe-top"]) / YUKSEKLIK,
        "alt": _px(s["safe-bottom"]) / YUKSEKLIK,
        "sol": _px(s["safe-side"]) / GENISLIK,
        "sag": 1 - _px(s["safe-right"]) / GENISLIK,
    }


def sirali_renk(oran: float) -> str:
    """0 (düşük) .. 1 (yüksek) → sıralı rampa adımı."""
    adimlar = [renk(f"seq-{i}") for i in range(1, 6)]
    i = min(int(max(oran, 0) * len(adimlar)), len(adimlar) - 1)
    return adimlar[i]


def sayi(x: float | int, ondalik: int | None = None) -> str:
    if ondalik is None:
        ondalik = 0 if float(x).is_integer() else 1
    return f"{x:,.{ondalik}f}"
