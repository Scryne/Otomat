"""Nokta harita şablonu: zamanla beliren olaylar (ör. depremler) + sayaç. Bölge videosunda kamera yakınlaşır."""

import datetime as dt
from pathlib import Path

import numpy as np
from matplotlib.collections import PolyCollection

from otomat.gorsel import harita
from otomat.gorsel.kimlik import font, renk, sayi
from otomat.gorsel.sahne import Sahne, yumusat


def ciz(
    olaylar: list[list[float]],  # [zaman, boylam, enlem, büyüklük]
    baslik: str,
    kaynak: str,
    cikti: Path,
    kutu: dict | None = None,
    kanca: str | None = None,
    sayac_etiketi: str = "earthquakes",
    bolge_adi: str | None = None,  # bölge videosu: küçük adalar 110m kara verisinde yok, yakınlaşınca harita boş kalır
    genislik: int = 1080,
    yukseklik: int = 1920,
    fps: int = 30,
    saniye: float = 30,
    **sahne_kw,
) -> Path:
    if not olaylar:
        raise ValueError("olay yok")
    ev = np.array(sorted(olaylar), dtype=float)
    kaydirma = bool(kutu and kutu.get("boylam_kaydir"))
    if kaydirma:
        ev[:, 1] = np.where(ev[:, 1] < 0, ev[:, 1] + 360, ev[:, 1])
    t0, t1 = ev[0, 0], ev[-1, 0]
    sure = max(t1 - t0, 1.0)

    s = Sahne(baslik, kaynak, kanca, genislik=genislik, yukseklik=yukseklik, fps=fps, saniye=saniye, **sahne_kw)
    g = s.g
    harita_alt, harita_ust = 0.36, min(0.80, s.icerik_ust)
    ax = s.eksen(harita_alt, harita_ust)
    en_boy = genislik / ((harita_ust - harita_alt) * yukseklik)
    halkalar = [harita.kaydir(h) for h in harita.kara()] if kaydirma else harita.kara()
    ax.add_collection(PolyCollection(halkalar, facecolor=renk("land"), edgecolor=renk("land-edge"), linewidths=0.6))
    if kutu:  # bölge videosunda ülke sınırları ve 5°'lik ızgara bağlam verir (okyanus bölgeleri boş kalmasın)
        sinirlar = [harita.kaydir(h) if kaydirma else h for u in harita.ulkeler("dunya").values() for h in u["p"]]
        ax.add_collection(PolyCollection(sinirlar, facecolor="none", edgecolor=renk("land-edge"), linewidths=0.8))
        izgara = dict(color=renk("land-edge"), linewidth=0.7 * s.olcek, zorder=1)
        for b in range(-180, 541, 5):
            ax.axvline(b, **izgara)
        for e in range(-85, 86, 5):
            ax.axhline(e, **izgara)
        if bolge_adi:
            s.fig.text(
                g["sol"],
                harita_ust - 0.008,
                bolge_adi,
                ha="left",
                va="top",
                zorder=5,
                color=renk("ink-secondary"),
                fontproperties=font("label", s.olcek),
            )
    dunya = harita.KUTU_DUNYA if not kaydirma else (10.0, 370.0, -58.0, 84.0)
    hedef = (kutu["boylam"][0], kutu["boylam"][1], kutu["enlem"][0], kutu["enlem"][1]) if kutu else dunya
    harita.kutu_ayarla(ax, dunya, en_boy)

    birinc = renk("primary")
    eski = ax.scatter([], [], s=[], c=birinc, alpha=0.35, linewidths=0, zorder=3)
    yeni = ax.scatter([], [], s=[], facecolors="none", edgecolors=birinc, linewidths=2 * s.olcek, zorder=4)
    sayac = s.fig.text(
        g["sol"], 0.285, "", ha="left", va="bottom", color=renk("ink-primary"), fontproperties=font("display", s.olcek)
    )
    s.fig.text(
        g["sol"],
        0.27,
        sayac_etiketi,
        ha="left",
        va="top",
        color=renk("ink-secondary"),
        fontproperties=font("label", s.olcek),
    )
    gun = s.fig.text(
        g["sag"],
        0.285,
        "",
        ha="right",
        va="bottom",
        color=renk("ink-secondary"),
        fontproperties=font("title", s.olcek),
    )

    tarih_bicimi = "%b %Y" if sure > 60 * 86400 else "%b %d"
    yakinlasma = 2.0  # sn
    oynatma = max(saniye - s.baslangic - yakinlasma - 2.0, 1.0)

    def boy(b):
        return ((b - 4) ** 2 * 70 + 10) * s.olcek**2

    def guncelle(t: float) -> None:
        ilerleme = (t - s.baslangic) / yakinlasma
        if kutu and 0 <= ilerleme <= 1.05:
            harita.kutu_ayarla(ax, harita.ara_kutu(dunya, hedef, yumusat(ilerleme)), en_boy)
        oran = min(max((t - s.baslangic - (yakinlasma if kutu else 0)) / oynatma, 0), 1)
        tc = t0 + sure * oran if oran > 0 else t0 - 1
        gorulen = ev[ev[:, 0] <= tc]
        eski.set_offsets(gorulen[:, 1:3] if len(gorulen) else np.empty((0, 2)))
        eski.set_sizes(boy(gorulen[:, 3]))
        pencere = sure / 25
        taze = gorulen[gorulen[:, 0] > tc - pencere]
        yeni.set_offsets(taze[:, 1:3] if len(taze) else np.empty((0, 2)))
        yeni.set_sizes(boy(taze[:, 3]) * (1 + 5 * (tc - taze[:, 0]) / pencere))
        sayac.set_text(sayi(len(gorulen)))
        gun.set_text(dt.datetime.fromtimestamp(max(tc, t0), dt.UTC).strftime(tarih_bicimi))

    return s.calistir(cikti, guncelle)
