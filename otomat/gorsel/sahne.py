"""Ortak sahne: 9:16 figür, kanca kartı, başlık, altyazı, atıf ve kare döngüsü. Şablonlar bunun üstüne çizer."""

import textwrap
from collections.abc import Callable, Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from otomat.gorsel.kimlik import font, guvenli_alan, renk, yerlesim  # noqa: E402
from otomat.gorsel.video import VideoYazici  # noqa: E402

KANCA_SURE = 1.5  # sn; DESIGN.md "Kanca kartı" (seslendirilen kanca daha uzunsa onun süresi, en çok 3 sn)
KANCA_EN_COK = 3.0
KANCA_SONUM = 0.3
ALTYAZI_Y = 0.232  # Earth varsayılanı (kimlik.yerlesim); alt güvenli sınırın hemen üstü (DESIGN.md Components)


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
        kanca_sure: float | None = None,
        altyazi: Sequence | None = None,  # [Parca(bas, son, metin)]
    ):
        self.genislik, self.yukseklik, self.fps, self.saniye = genislik, yukseklik, fps, saniye
        self.olcek = genislik / 1080
        self.g = guvenli_alan()
        self.y = yerlesim()  # kanal kimliğinin sahne yerleşimi (DESIGN `layout`)
        self.fig = plt.figure(figsize=(genislik / 100, yukseklik / 100), dpi=100, facecolor=renk("surface"))
        sol = self.g["sol"]
        orta = (self.g["sol"] + self.g["sag"]) / 2
        ortali = self.y["title-align"] == "center"
        self.baslik = self.fig.text(
            orta if ortali else sol,
            self.g["ust"],
            textwrap.fill(baslik, 26 if ortali else 30),
            ha="center" if ortali else "left",
            multialignment="center" if ortali else "left",
            va="top",
            color=renk("ink-primary"),
            fontproperties=font("title", self.olcek),
            linespacing=1.05,
        )
        kutu = self.baslik.get_window_extent(self.fig.canvas.get_renderer())
        self.icerik_ust = kutu.y0 / yukseklik - 0.02  # başlığın altı: içerik buradan aşağı
        atif_orta = self.y["attribution-align"] == "center"
        self.fig.text(
            0.5 if atif_orta else sol,
            self.g["alt"] + 0.004,
            f"Data: {kaynak}",
            ha="center" if atif_orta else "left",
            va="bottom",
            color=renk("ink-muted"),
            fontproperties=font("caption", self.olcek),
        )
        self.kanca_sure = min(max(kanca_sure or KANCA_SURE, KANCA_SURE), KANCA_EN_COK)
        self._kanca = None
        if kanca:
            perde = Rectangle((0, 0), 1, 1, transform=self.fig.transFigure, color=renk("surface"), alpha=0.6, zorder=50)
            self.fig.patches.append(perde)
            yazi = self.fig.text(
                0.5,
                float(self.y["hook-y"]),
                textwrap.fill(kanca, 24),
                ha="center",
                va="center",
                color=renk("ink-primary"),
                zorder=51,
                fontproperties=font("title", self.olcek, 1.15),
                linespacing=1.05,
            )
            self._kanca = (perde, yazi)
        self._altyazi = list(altyazi or [])
        self._altyazi_yazi = self.fig.text(
            0.5,
            float(self.y["caption-y"]),
            "",
            ha="center",
            va="center",
            color=renk("ink-primary"),
            zorder=40,
            fontproperties=font("title", self.olcek, 0.85),
            path_effects=[pe.withStroke(linewidth=8 * self.olcek, foreground=renk("surface"))],
        )

    def eksen(self, alt: float, ust: float, sol: float = 0.0, sag: float = 1.0):
        ax = self.fig.add_axes((sol, alt, sag - sol, ust - alt), facecolor="none")
        ax.axis("off")
        return ax

    def _kanca_guncelle(self, t: float) -> None:
        if not self._kanca:
            return
        gorunurluk = 1 - yumusat((t - (self.kanca_sure - KANCA_SONUM)) / KANCA_SONUM)
        perde, yazi = self._kanca
        perde.set_alpha(0.6 * gorunurluk)
        yazi.set_alpha(gorunurluk)
        yazi.set_visible(gorunurluk > 0)
        perde.set_visible(gorunurluk > 0)

    def _altyazi_guncelle(self, t: float) -> None:
        metin = ""
        if t >= self.baslangic:  # kanca kartı açıkken kanca zaten ekranda
            for p in self._altyazi:
                if p.bas <= t < p.son:
                    metin = p.metin
                    break
        self._altyazi_yazi.set_text(textwrap.fill(metin, 26))

    @property
    def baslangic(self) -> float:
        """Veri hareketinin başladığı an (kanca kartı varsa ondan sonra)."""
        return self.kanca_sure if self._kanca else 0.0

    def calistir(self, cikti: Path, guncelle: Callable[[float], None]) -> Path:
        kare = int(self.fps * self.saniye)
        with VideoYazici(cikti, self.genislik, self.yukseklik, self.fps) as yazici:
            for i in range(kare):
                t = i / self.fps
                guncelle(t)
                self._kanca_guncelle(t)
                self._altyazi_guncelle(t)
                yazici.yaz(self.fig)
        plt.close(self.fig)
        return cikti
