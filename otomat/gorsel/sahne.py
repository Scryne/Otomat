"""Ortak sahne: 9:16 figür, kanca kartı, başlık, atıf ve kare döngüsü. Şablonlar bunun üstüne çizer."""

import textwrap
from collections.abc import Callable
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from otomat.gorsel.kimlik import font, guvenli_alan, renk  # noqa: E402
from otomat.gorsel.video import VideoYazici  # noqa: E402

KANCA_SURE = 1.5  # sn; DESIGN.md "Kanca kartı"
KANCA_SONUM = 0.3


def yumusat(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


class Sahne:
    def __init__(
        self,
        baslik: str,
        kaynak: str,
        kanca: str | None = None,
        genislik: int = 1080,
        yukseklik: int = 1920,
        fps: int = 30,
        saniye: float = 30,
    ):
        self.genislik, self.yukseklik, self.fps, self.saniye = genislik, yukseklik, fps, saniye
        self.olcek = genislik / 1080
        self.g = guvenli_alan()
        self.fig = plt.figure(figsize=(genislik / 100, yukseklik / 100), dpi=100, facecolor=renk("surface"))
        sol = self.g["sol"]
        self.baslik = self.fig.text(
            sol,
            self.g["ust"],
            textwrap.fill(baslik, 30),
            ha="left",
            va="top",
            color=renk("ink-primary"),
            fontproperties=font("title", self.olcek),
            linespacing=1.05,
        )
        kutu = self.baslik.get_window_extent(self.fig.canvas.get_renderer())
        self.icerik_ust = kutu.y0 / yukseklik - 0.02  # başlığın altı: içerik buradan aşağı
        self.fig.text(
            sol,
            self.g["alt"] + 0.004,
            f"Data: {kaynak}",
            ha="left",
            va="bottom",
            color=renk("ink-muted"),
            fontproperties=font("caption", self.olcek),
        )
        self._kanca = None
        if kanca:
            perde = Rectangle((0, 0), 1, 1, transform=self.fig.transFigure, color=renk("surface"), alpha=0.6, zorder=50)
            self.fig.patches.append(perde)
            yazi = self.fig.text(
                0.5,
                0.62,
                textwrap.fill(kanca, 24),
                ha="center",
                va="center",
                color=renk("ink-primary"),
                zorder=51,
                fontproperties=font("title", self.olcek, 1.15),
                linespacing=1.05,
            )
            self._kanca = (perde, yazi)

    def eksen(self, alt: float, ust: float, sol: float = 0.0, sag: float = 1.0):
        ax = self.fig.add_axes((sol, alt, sag - sol, ust - alt), facecolor="none")
        ax.axis("off")
        return ax

    def _kanca_guncelle(self, t: float) -> None:
        if not self._kanca:
            return
        gorunurluk = 1 - yumusat((t - (KANCA_SURE - KANCA_SONUM)) / KANCA_SONUM)
        perde, yazi = self._kanca
        perde.set_alpha(0.6 * gorunurluk)
        yazi.set_alpha(gorunurluk)
        yazi.set_visible(gorunurluk > 0)
        perde.set_visible(gorunurluk > 0)

    @property
    def baslangic(self) -> float:
        """Veri hareketinin başladığı an (kanca kartı varsa ondan sonra)."""
        return KANCA_SURE if self._kanca else 0.0

    def calistir(self, cikti: Path, guncelle: Callable[[float], None]) -> Path:
        kare = int(self.fps * self.saniye)
        with VideoYazici(cikti, self.genislik, self.yukseklik, self.fps) as yazici:
            for i in range(kare):
                t = i / self.fps
                guncelle(t)
                self._kanca_guncelle(t)
                yazici.yaz(self.fig)
        plt.close(self.fig)
        return cikti
