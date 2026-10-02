"""Nokta harita şablonu: zamanla beliren olaylar (ör. depremler) + sayaç."""

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402

from otomat.ayarlar import VARLIKLAR  # noqa: E402
from otomat.gorsel.video import VideoYazici  # noqa: E402

ZEMIN, KARA, VURGU, YAZI = "#0b0f14", "#1c2530", "#ff5a36", "#e8edf2"


@dataclass
class Olay:
    zaman: float  # unix saniye
    boylam: float
    enlem: float
    buyukluk: float


def _kara_poligonlari() -> list[np.ndarray]:
    veri = json.loads((VARLIKLAR / "ne_110m_land.geojson").read_text(encoding="utf-8"))
    poligonlar = []
    for f in veri["features"]:
        g = f["geometry"]
        halkalar = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        poligonlar += [np.array(p[0]) for p in halkalar]
    return poligonlar


def ciz(
    olaylar: list[Olay],
    baslik: str,
    alt_baslik: str,
    kaynak: str,
    cikti: Path,
    genislik: int = 1080,
    yukseklik: int = 1920,
    fps: int = 30,
    saniye: float = 30,
) -> Path:
    if not olaylar:
        raise ValueError("olay yok")
    ev = np.array(sorted((o.zaman, o.boylam, o.enlem, o.buyukluk) for o in olaylar))
    t0, t1 = ev[0, 0], ev[-1, 0]
    sure = max(t1 - t0, 1.0)
    olcek = genislik / 1080

    fig = plt.figure(figsize=(genislik / 100, yukseklik / 100), dpi=100, facecolor=ZEMIN)
    ax = fig.add_axes((0.0, 0.33, 1.0, 0.34), facecolor=ZEMIN)
    ax.add_collection(PolyCollection(_kara_poligonlari(), facecolor=KARA, edgecolor="none"))
    ax.set_xlim(-180, 180)
    ax.set_ylim(-60, 85)
    ax.axis("off")
    fig.text(0.5, 0.86, baslik, ha="center", color=YAZI, fontsize=54 * olcek, weight="bold")
    fig.text(0.5, 0.815, alt_baslik, ha="center", color=YAZI, fontsize=40 * olcek, alpha=0.8)
    sayac = fig.text(0.5, 0.22, "", ha="center", color=VURGU, fontsize=110 * olcek, weight="bold")
    gun = fig.text(0.5, 0.17, "", ha="center", color=YAZI, fontsize=34 * olcek, alpha=0.8)
    fig.text(0.5, 0.04, f"Data: {kaynak}", ha="center", color=YAZI, fontsize=22 * olcek, alpha=0.5)
    eski = ax.scatter([], [], s=[], c=VURGU, alpha=0.35, linewidths=0)
    yeni = ax.scatter([], [], s=[], facecolors="none", edgecolors=VURGU, linewidths=2 * olcek)

    def boy(b):
        return ((b - 4) ** 2 * 60 + 8) * olcek**2

    kare_sayisi = int(fps * saniye)
    with VideoYazici(cikti, genislik, yukseklik, fps) as yazici:
        for i in range(kare_sayisi):
            tc = t0 + sure * min(1, i / (kare_sayisi * 0.85))
            gorulen = ev[ev[:, 0] <= tc]
            eski.set_offsets(gorulen[:, 1:3])
            eski.set_sizes(boy(gorulen[:, 3]))
            taze = gorulen[gorulen[:, 0] > tc - sure / 30]
            yas = (tc - taze[:, 0]) / (sure / 30)
            yeni.set_offsets(taze[:, 1:3])
            yeni.set_sizes(boy(taze[:, 3]) * (1 + 6 * yas))
            sayac.set_text(f"{len(gorulen)}")
            gun.set_text(dt.datetime.fromtimestamp(tc, dt.UTC).strftime("%b %d"))
            yazici.yaz(fig)
    plt.close(fig)
    return cikti
