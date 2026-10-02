"""Koroplet şablonu: ülkeler düşükten yükseğe sırayla rampadan dolar; sonda ilk 3 vurgulanır."""

from pathlib import Path

from matplotlib.collections import PolyCollection
from matplotlib.patches import Rectangle

from otomat.gorsel import harita
from otomat.gorsel.kimlik import font, renk, sayi, sirali_renk
from otomat.gorsel.sahne import Sahne, yumusat


def ciz(
    degerler: dict[str, float],  # ISO3 -> değer
    baslik: str,
    kaynak: str,
    cikti: Path,
    kapsam: str = "dunya",  # dunya | avrupa
    birim: str = "",
    ondalik: int | None = None,
    kanca: str | None = None,
    genislik: int = 1080,
    yukseklik: int = 1920,
    fps: int = 30,
    saniye: float = 30,
) -> Path:
    ulkeler = harita.ulkeler(kapsam)
    var = {k: v for k, v in degerler.items() if k in ulkeler}
    if len(var) < 5:
        raise ValueError("haritada eşleşen ülke yok denecek kadar az")
    sirali = sorted(var.items(), key=lambda x: x[1])  # düşükten yükseğe
    sira = {k: i for i, (k, _) in enumerate(sirali)}
    n = len(sirali)
    ilk3 = [k for k, _ in sirali[::-1][:3]]

    s = Sahne(baslik, kaynak, kanca, genislik=genislik, yukseklik=yukseklik, fps=fps, saniye=saniye)
    g = s.g
    # Dünya haritası 9:16'da kısa kalır: altındaki boşluğu büyük ilk-3 listesi doldurur (DESIGN.md Koroplet)
    alt, ust = (0.47, min(0.80, s.icerik_ust)) if kapsam == "dunya" else (0.40, min(0.80, s.icerik_ust))
    gosterge_y = alt - 0.025
    liste_y, liste_adim, liste_font = (
        (gosterge_y - 0.05, 0.045, "title") if kapsam == "dunya" else (gosterge_y - 0.035, 0.034, "label")
    )
    ax = s.eksen(alt, ust)
    en_boy = genislik / ((ust - alt) * yukseklik)
    harita.kutu_ayarla(ax, harita.KUTU_DUNYA if kapsam == "dunya" else harita.KUTU_AVRUPA, en_boy)

    halkalar, sahip = [], []
    for iso, u in ulkeler.items():
        for h in u["p"]:
            halkalar.append(h)
            sahip.append(iso)
    koleksiyon = PolyCollection(halkalar, facecolors=renk("no-data"), edgecolors=renk("surface"), linewidths=0.5)
    ax.add_collection(koleksiyon)
    vurgu = PolyCollection(
        [h for iso in ilk3 for h in ulkeler[iso]["p"]],
        facecolors="none",
        edgecolors=renk("primary"),
        linewidths=2.5 * s.olcek,
        zorder=5,
    )
    vurgu.set_visible(False)
    ax.add_collection(vurgu)
    kucukler = [k for k in var if not ulkeler[k]["p"]]
    noktalar = ax.scatter(
        [ulkeler[k]["m"][0] for k in kucukler],
        [ulkeler[k]["m"][1] for k in kucukler],
        s=60 * s.olcek**2,
        facecolors=renk("no-data"),
        edgecolors=renk("surface"),
        linewidths=1,
        zorder=4,
    )

    kucuk_ilk3 = [k for k in ilk3 if not ulkeler[k]["p"]]
    kucuk_vurgu = None
    if kucuk_ilk3:  # haritada çizilemeyen küçük ülke ilk 3'teyse turuncu halka
        kucuk_vurgu = ax.scatter(
            [ulkeler[k]["m"][0] for k in kucuk_ilk3],
            [ulkeler[k]["m"][1] for k in kucuk_ilk3],
            s=260 * s.olcek**2,
            facecolors="none",
            edgecolors=renk("primary"),
            linewidths=2.5 * s.olcek,
            zorder=6,
        )
        kucuk_vurgu.set_visible(False)

    # Rampa göstergesi
    for i in range(5):
        s.fig.patches.append(
            Rectangle(
                (g["sol"] + i * 0.11, gosterge_y), 0.11, 0.012, transform=s.fig.transFigure, color=renk(f"seq-{i + 1}")
            )
        )
    # Her ton ülkelerin beşte biri (rank tabanlı); sınır değerleri tonların arasına yazılır
    for k in range(6):
        deger = sirali[min(round(k * (n - 1) / 5), n - 1)][1]
        s.fig.text(
            g["sol"] + k * 0.11,
            gosterge_y - 0.006,
            sayi(deger, ondalik),
            ha="left" if k == 0 else ("right" if k == 5 else "center"),
            va="top",
            color=renk("ink-secondary"),
            fontproperties=font("caption", s.olcek),
        )
    s.fig.text(
        g["sol"] + 0.57,
        gosterge_y + 0.006,
        birim,
        ha="left",
        va="center",
        color=renk("ink-secondary"),
        fontproperties=font("caption", s.olcek),
    )

    etiketler = []
    for j, iso in enumerate(ilk3):
        etiketler.append(
            s.fig.text(
                g["sol"],
                liste_y - j * liste_adim,
                f"{j + 1}. {ulkeler[iso]['ad']}  {sayi(var[iso], ondalik)}",
                ha="left",
                va="top",
                color=renk("ink-primary"),
                fontproperties=font(liste_font, s.olcek),
            )
        )
        etiketler[-1].set_visible(False)

    son_tutma = 3.0
    dolum = max(saniye - s.baslangic - son_tutma, 2.0)
    renkler_son = [sirali_renk(sira[iso] / max(n - 1, 1)) if iso in sira else renk("no-data") for iso in sahip]
    nokta_son = [sirali_renk(sira[k] / max(n - 1, 1)) for k in kucukler]

    def guncelle(t: float) -> None:
        oran = yumusat((t - s.baslangic) / dolum)
        esik = oran * n
        yuzler = [
            renkler_son[i] if (iso in sira and sira[iso] < esik) else renk("no-data") for i, iso in enumerate(sahip)
        ]
        koleksiyon.set_facecolors(yuzler)
        if kucukler:
            noktalar.set_facecolors(
                [nokta_son[i] if sira[k] < esik else renk("no-data") for i, k in enumerate(kucukler)]
            )
        son = t >= s.baslangic + dolum
        vurgu.set_visible(son)
        if kucuk_vurgu is not None:
            kucuk_vurgu.set_visible(son)
        for j, e in enumerate(etiketler):
            e.set_visible(t >= s.baslangic + dolum + j * 0.4)

    return s.calistir(cikti, guncelle)
