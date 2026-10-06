"""Ölçek şablonu (uzay kanalı): gezegenleri gerçek oranlarıyla daire olarak gösterir.

- `gezegen` kipi: önce Dünya ile özne yan yana; kamera geri çekilip Neptün ve Jüpiter'i de aynı ölçekte gösterir.
  Altta özne gezegenin kartı (uzaklık, yıl uzunluğu, sıcaklık).
- `gezegen_liste` kipi: sekiz gezegen 8'den 1'e sırayla belirir; daire boyu ölçülmüş yarıçap, değer yanında;
  1. sıra vurgulu.
"""

from pathlib import Path

from matplotlib.patches import Circle, Ellipse

from otomat.gorsel.kimlik import font, renk
from otomat.gorsel.sahne import Sahne, yumusat

JUPITER_RE, NEPTUN_RE = 11.21, 3.88


def _deger(d: float | int, birim: str) -> str:
    from otomat.anlati.kapilar import deger_yazisi

    return deger_yazisi(d, birim)


def ciz(
    gorsel: dict,
    baslik: str,
    kaynak: str,
    cikti: Path,
    kanca: str | None = None,
    kart: list[tuple[str, str]] | None = None,  # gezegen kipi: [(etiket, değer)]
    genislik: int = 1080,
    yukseklik: int = 1920,
    fps: int = 30,
    saniye: float = 30,
    **sahne_kw,
) -> Path:
    s = Sahne(baslik, kaynak, kanca, genislik=genislik, yukseklik=yukseklik, fps=fps, saniye=saniye, **sahne_kw)
    if gorsel["kip"] == "gezegen":
        return _gezegen(s, gorsel, cikti, kart or [])
    return _liste(s, gorsel, cikti)


def _gezegen(s: Sahne, g: dict, cikti: Path, kart: list[tuple[str, str]]) -> Path:
    alt, ust = 0.47, min(0.80, s.icerik_ust)
    ax = s.eksen(alt, ust)
    en_boy = s.genislik / ((ust - alt) * s.yukseklik)
    r = float(g["yaricap"])
    # x'te yan yana, tabanları aynı çizgide: Dünya, özne, Neptün, Jüpiter (özne kendi boyuna göre sıraya girer)
    govdeler = [("Earth", 1.0, renk("earth")), (g["ad"], r, renk("primary"))]
    referans = [("Neptune", NEPTUN_RE, renk("seq-3")), ("Jupiter", JUPITER_RE, renk("seq-2"))]
    hepsi = sorted(govdeler + referans, key=lambda x: x[1])
    x, konum = 0.0, {}
    for ad, yr, _ in hepsi:
        konum[ad] = x + yr
        x += 2 * yr + 4.5  # tam görünümde küçük gövdelerin adları birbirine binmesin
    toplam = x
    yakin_genislik = max(konum[g["ad"]] + r, konum["Earth"] + 1) - min(konum[g["ad"]] - r, konum["Earth"] - 1)
    referans_parca = []  # Neptün, Jüpiter: kamera geri çekilirken belirir (yakında kenarda yarım daire olmasın)
    for n, (ad, yr, rk) in enumerate(hepsi):
        ozne = ad == g["ad"]
        daire = ax.add_patch(Circle((konum[ad], yr), yr, color=rk, alpha=1.0 if ozne else 0.9, zorder=3))
        # küçük gövdelerde adlar sırayla iki satıra (biri biraz aşağı) dağılır
        # ad, kamera ne kadar uzakta olursa olsun dairenin hemen altında (piksel ofseti)
        yazi = ax.annotate(ad, (konum[ad], 0), xytext=(0, -6 - (30 if n % 2 and yr < 5 else 0)),
                           textcoords="offset points", ha="center", va="top",
                           color=renk("ink-primary" if ozne else "ink-secondary"),
                           fontproperties=font("label" if ozne else "caption", s.olcek), zorder=4)  # fmt: skip
        if ad in ("Neptune", "Jupiter"):
            referans_parca += [daire, yazi]
    ax.set_aspect("equal")

    def kutu(oran: float) -> None:
        # yakın görünüm (Dünya + özne) → tam görünüm (dört gövde)
        merkez_yakin = (min(konum[g["ad"]], konum["Earth"]) + max(konum[g["ad"]], konum["Earth"])) / 2
        gen = yakin_genislik * 1.5 + (toplam * 1.08 - yakin_genislik * 1.5) * oran
        mx = merkez_yakin + (toplam / 2 - merkez_yakin) * oran
        yuk = gen / en_boy
        ax.set_xlim(mx - gen / 2, mx + gen / 2)
        ax.set_ylim(-0.12 * yuk, 0.88 * yuk)

    kutu(0)
    kart_yazilari = []
    for i, (etiket, deger) in enumerate(kart[:4]):
        y = 0.43 - i * 0.045
        kart_yazilari.append(s.fig.text(0.5 - 0.03, y, etiket, ha="right", va="center", color=renk("ink-secondary"),
                                         fontproperties=font("label", s.olcek, 0.85), alpha=0))  # fmt: skip
        kart_yazilari.append(s.fig.text(0.5 + 0.03, y, deger, ha="left", va="center", color=renk("ink-primary"),
                                         fontproperties=font("label", s.olcek), alpha=0))  # fmt: skip
    oynatma = max(s.saniye - s.baslangic - 1.5, 1.0)

    def guncelle(t: float) -> None:
        u = (t - s.baslangic) / oynatma
        geri = yumusat((u - 0.25) / 0.35)
        kutu(geri)
        for p in referans_parca:
            p.set_alpha(0.9 * yumusat((u - 0.22) / 0.12))
        for i, yazi in enumerate(kart_yazilari):
            yazi.set_alpha(yumusat((u - 0.55 - 0.04 * (i // 2)) / 0.08))

    return s.calistir(cikti, guncelle)


def _liste(s: Sahne, g: dict, cikti: Path) -> Path:
    ogeler = g["ogeler"]  # 1. sıra önce
    n = len(ogeler)
    alt, ust = 0.31, min(0.80, s.icerik_ust)
    satir = (ust - alt) / n
    en_buyuk = max(o["yaricap"] for o in ogeler + [{"yaricap": 1.0}])
    tam = satir * 0.42  # en büyük dairenin yarıçapı, kare yüksekliği kesri cinsinden
    yazilar = []
    sol = s.g["sol"]
    for i, o in enumerate(ogeler):
        y = ust - (i + 0.5) * satir
        ilk = i == 0
        rx = tam * (o["yaricap"] / en_buyuk) ** 0.5  # alan değil yarıçap oranı; çok küçükler kaybolmasın diye kök
        # kare kesirlerinde daire = elips (kare 9:16): genişlik kesri yükseklik kesrinin 16/9 katı
        daire = Ellipse((sol + 0.10, y), 2 * rx * s.yukseklik / s.genislik, 2 * rx, transform=s.fig.transFigure,
                        color=renk("primary") if ilk else renk("seq-3"), alpha=0, zorder=3)  # fmt: skip
        s.fig.patches.append(daire)
        sira = s.fig.text(sol, y, f"{i + 1}", ha="left", va="center", color=renk("ink-muted"),
                          fontproperties=font("label", s.olcek), alpha=0)  # fmt: skip
        ad = s.fig.text(sol + 0.20, y + satir * 0.12, o["ad"], ha="left", va="center",
                        color=renk("ink-primary") if ilk else renk("ink-secondary"),
                        fontproperties=font("label", s.olcek, 0.9), alpha=0)  # fmt: skip
        deger = s.fig.text(sol + 0.20, y - satir * 0.22, _deger(o["deger"], o["birim"]), ha="left", va="center",
                           color=renk("primary") if ilk else renk("ink-primary"),
                           fontproperties=font("title", s.olcek, 0.7), alpha=0)  # fmt: skip
        yazilar.append((daire, sira, ad, deger))
    s.fig.text(0.5, alt - 0.006, "circle size: measured planet width (√ scale)", ha="center", va="top",
               color=renk("ink-muted"), fontproperties=font("caption", s.olcek, 0.9))  # fmt: skip
    oynatma = max(s.saniye - s.baslangic - 2.0, 1.0)
    aralik = oynatma / (n + 1)

    def guncelle(t: float) -> None:
        for i, parcalar in enumerate(yazilar):
            sira_ani = s.baslangic + (n - 1 - i) * aralik  # 8'den 1'e
            if i == 0:
                sira_ani += aralik * 0.6  # birinciye kısa bir bekleme
            a = yumusat((t - sira_ani) / 0.35)
            for p in parcalar:
                p.set_alpha(a)

    return s.calistir(cikti, guncelle)
