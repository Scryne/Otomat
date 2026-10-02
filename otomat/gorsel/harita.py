"""Harita yardımcıları: Natural Earth ülke poligonları (paketle gelir), basit eşdikdörtgen izdüşüm."""

import json
import math
from functools import cache

import numpy as np

from otomat.ayarlar import VARLIKLAR

KUTU_DUNYA = (-170.0, 190.0, -58.0, 84.0)
KUTU_AVRUPA = (-25.0, 45.0, 34.0, 71.5)


@cache
def ulkeler(kapsam: str) -> dict[str, dict]:
    """{ISO3: {"ad", "p": [halka...], "m": [boylam, enlem]}}; kapsam 'dunya' | 'avrupa'."""
    veri = json.loads((VARLIKLAR / f"ulkeler_{kapsam}.json").read_text(encoding="utf-8"))
    for v in veri.values():
        v["p"] = [np.array(h, dtype=float) for h in v["p"]]
    return veri


@cache
def kara() -> list[np.ndarray]:
    veri = json.loads((VARLIKLAR / "ne_110m_land.geojson").read_text(encoding="utf-8"))
    sonuc = []
    for f in veri["features"]:
        g = f["geometry"]
        for p in [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]:
            sonuc.append(np.array(p[0], dtype=float))
    return sonuc


def kaydir(halka: np.ndarray) -> np.ndarray:
    """Tarih çizgisini aşan kutular için boylamları 0..360'a taşı."""
    h = halka.copy()
    h[:, 0] = np.where(h[:, 0] < 0, h[:, 0] + 360, h[:, 0])
    return h


def kutu_ayarla(ax, kutu: tuple[float, float, float, float], en_boy: float) -> None:
    """Kutuyu eksenin en-boy oranına (genişlik/yükseklik, piksel) göre genişletip ortala; enlem ölçeği cos(φ)."""
    b0, b1, e0, e1 = kutu
    orta_enlem = (e0 + e1) / 2
    k = max(math.cos(math.radians(orta_enlem)), 0.2)
    gen, yuk = (b1 - b0) * k, e1 - e0
    if gen / yuk < en_boy:
        ek = (yuk * en_boy - gen) / k / 2
        b0, b1 = b0 - ek, b1 + ek
    else:
        ek = (gen / en_boy - yuk) / 2
        e0, e1 = e0 - ek, e1 + ek
    ax.set_xlim(b0, b1)
    ax.set_ylim(e0, e1)
    ax.set_aspect(1 / k, adjustable="box")


def ara_kutu(a, b, oran: float):
    return tuple(x + (y - x) * oran for x, y in zip(a, b, strict=True))
