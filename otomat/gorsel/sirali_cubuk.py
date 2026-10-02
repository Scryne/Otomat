"""Sıralı çubuk şablonu: 10. sıradan 1. sıraya geri sayım, 1. sıra vurgu renginde."""

from pathlib import Path

from matplotlib.patches import FancyBboxPatch

from otomat.gorsel.kimlik import font, renk, sayi
from otomat.gorsel.sahne import Sahne, yumusat

SATIR_SURE = 0.45  # bir çubuğun büyüme süresi (sn)


def ciz(
    ogeler: list[dict],  # [{"etiket", "deger", ...}] büyükten küçüğe (1. sıra ilk)
    baslik: str,
    kaynak: str,
    cikti: Path,
    birim: str = "",
    ortanca: float | None = None,
    ondalik: int | None = None,
    kanca: str | None = None,
    genislik: int = 1080,
    yukseklik: int = 1920,
    fps: int = 30,
    saniye: float = 30,
) -> Path:
    if not ogeler:
        raise ValueError("öğe yok")
    ogeler = ogeler[:10]
    n = len(ogeler)
    s = Sahne(baslik, kaynak, kanca, genislik=genislik, yukseklik=yukseklik, fps=fps, saniye=saniye)
    g = s.g
    alt, ust = 0.30, min(0.79, s.icerik_ust)
    ax = s.eksen(alt, ust, g["sol"], g["sag"])
    en_buyuk = max(abs(o["deger"]) for o in ogeler) or 1
    ax.set_xlim(0, en_buyuk * 1.0)
    ax.set_ylim(n - 0.5, -0.5)
    satir_yuk = 0.62
    sutun_etiket = font("label", s.olcek)
    sutun_deger = font("title", s.olcek, 0.8)

    cubuklar, etiketler, degerler = [], [], []
    for i, o in enumerate(ogeler):
        renk_i = renk("primary") if i == 0 else renk("data")
        kutu = FancyBboxPatch(
            (0, i - satir_yuk / 2 + 0.16),
            0,
            satir_yuk - 0.16,
            boxstyle="round,pad=0,rounding_size=0.06",
            mutation_aspect=1 / (en_buyuk * 0.12),
            facecolor=renk_i,
            edgecolor="none",
        )
        ax.add_patch(kutu)
        cubuklar.append(kutu)
        etiketler.append(
            ax.text(
                0,
                i - 0.30,
                f"{i + 1}. {o['etiket']}",
                ha="left",
                va="center",
                color=renk("ink-primary"),
                fontproperties=sutun_etiket,
            )
        )
        degerler.append(
            ax.text(0, i + 0.13, "", ha="left", va="center", color=renk("ink-primary"), fontproperties=sutun_deger)
        )
    if ortanca is not None:
        ax.axvline(ortanca, color=renk("ink-muted"), linewidth=1.5 * s.olcek, linestyle=(0, (4, 4)), zorder=0)
        ax.text(
            ortanca,
            -0.62,
            f" median {sayi(ortanca, ondalik)}",
            ha="left",
            va="bottom",
            clip_on=False,
            color=renk("ink-muted"),
            fontproperties=font("caption", s.olcek),
        )
    s.fig.text(
        g["sol"], 0.255, birim, ha="left", va="top", color=renk("ink-secondary"), fontproperties=font("label", s.olcek)
    )

    son_tutma = 2.5
    pencere = max(saniye - s.baslangic - son_tutma, n * SATIR_SURE)
    aralik = pencere / n

    def guncelle(t: float) -> None:
        for sira in range(n):  # geri sayım: en alttaki (10.) önce
            i = n - 1 - sira
            basla = s.baslangic + sira * aralik
            oran = yumusat((t - basla) / SATIR_SURE)
            gorunur = t >= basla
            deger = ogeler[i]["deger"]
            gen = abs(deger) * oran
            cubuklar[i].set_width(gen)
            cubuklar[i].set_visible(gorunur)
            etiketler[i].set_visible(gorunur)
            etiketler[i].set_alpha(min(1.0, oran * 2))
            degerler[i].set_visible(gorunur)
            degerler[i].set_text(sayi(deger * oran if oran < 1 else deger, ondalik))
            degerler[i].set_x(gen + en_buyuk * 0.015)
            if gen + en_buyuk * 0.015 > en_buyuk * 0.82:  # değer çubuğun içine
                degerler[i].set_x(gen - en_buyuk * 0.015)
                degerler[i].set_ha("right")
                degerler[i].set_color(renk("surface"))

    return s.calistir(cikti, guncelle)
