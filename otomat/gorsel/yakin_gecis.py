"""Yakın geçiş şablonu (uzay kanalı): ortada Dünya, Ay yörüngesi cetvel halkası, asteroitler en yakın noktaları kendi
mesafelerinde olan düz çizgilerle geçer. Mesafe ekseni karekök ölçekli (0,1–20 Ay mesafesi aynı karede okunsun);
halkalar gerçek değerleriyle etiketlidir. Tekil videoda son bölüm tahmini boyutu bilinen yapılarla karşılaştırır.

Geometri şematiktir: CAD yalnız en yakın mesafeyi verir, gerçek yörünge yönünü değil. Bu yüzden geçiş yönleri
eşit aralıklı açılara dağıtılır ve ekranda "distance to scale, directions are not" notu durur.
"""

import math
from pathlib import Path

import numpy as np
from matplotlib.patches import Circle, Ellipse, Rectangle

from otomat.gorsel.kimlik import font, renk, sayi
from otomat.gorsel.sahne import Sahne, yumusat

# Bilinen yapılar (yükseklik/uzunluk, m): tahmini çap aralığının yanında ölçek verir.
YAPILAR = [
    ("a bus", 12),
    ("a blue whale", 30),
    ("Statue of Liberty", 93),
    ("Great Pyramid", 139),
    ("Eiffel Tower", 330),
    ("Empire State Building", 443),
]
GECIS_SN = 1.6  # bir asteroitin ekrandan geçiş süresi (liste kipi)


def _r(ld: float) -> float:
    return math.sqrt(ld)


def _halkalar(en_uzak: float) -> list[float]:
    aday = [0.5, 1, 2, 5, 10, 20]
    return [h for h in aday if h <= max(en_uzak * 1.05, 1.0)] or [1]


def _yapilar(cap_max: float) -> list[tuple[str, int]]:
    """Asteroitin üst sınırını çevreleyen iki yapı: biri ondan küçük, biri büyük (yoksa en yakın ikisi)."""
    alt = [y for y in YAPILAR if y[1] <= cap_max]
    ust = [y for y in YAPILAR if y[1] > cap_max]
    secim = (alt[-1:] if alt else []) + (ust[:1] if ust else [])
    if len(secim) < 2:
        secim = YAPILAR[-2:] if not ust else YAPILAR[:2]
    return secim


def ciz(
    gecisler: list[dict],  # [{"ad", "ld", "tarih", "cap": [min, max], "hiz"}], en yakın önce
    baslik: str,
    kaynak: str,
    cikti: Path,
    kanca: str | None = None,
    vurgu: int = 0,
    genislik: int = 1080,
    yukseklik: int = 1920,
    fps: int = 30,
    saniye: float = 30,
    **sahne_kw,
) -> Path:
    if not gecisler:
        raise ValueError("geçiş yok")
    s = Sahne(baslik, kaynak, kanca, genislik=genislik, yukseklik=yukseklik, fps=fps, saniye=saniye, **sahne_kw)
    tekil = len(gecisler) == 1
    alt, ust = 0.33, min(0.80, s.icerik_ust)
    ax = s.eksen(alt, ust)
    en_boy = genislik / ((ust - alt) * yukseklik)
    en_uzak = max(g["ld"] for g in gecisler)
    halkalar = _halkalar(en_uzak)
    R = _r(max(halkalar[-1], en_uzak)) * 1.08
    ax.set_xlim(-R * en_boy, R * en_boy)
    ax.set_ylim(-R, R)
    ax.set_aspect("equal")

    for h in halkalar:  # mesafe halkaları
        ay = h == 1
        ax.add_patch(
            Circle(
                (0, 0),
                _r(h),
                fill=False,
                ec=renk("moon") if ay else renk("land-edge"),
                lw=(2.2 if ay else 1.2) * s.olcek,
                ls="-" if ay else (0, (4, 4)),
                zorder=1,
            )
        )
        ax.text(
            _r(h) * math.cos(math.radians(62)),
            _r(h) * math.sin(math.radians(62)),
            "Moon's orbit" if ay else f"{sayi(h)}× Moon",
            color=renk("moon") if ay else renk("ink-muted"),
            fontproperties=font("caption", s.olcek),
            ha="left",
            va="bottom",
            zorder=2,
        )
    ax.add_patch(Circle((_r(1) * math.cos(math.radians(205)), _r(1) * math.sin(math.radians(205))), 0.035 * R,
                        color=renk("moon"), zorder=3))  # fmt: skip
    ax.add_patch(Circle((0, 0), 0.06 * R, color=renk("earth"), zorder=3))
    ax.text(0, -0.09 * R, "Earth", color=renk("ink-secondary"), fontproperties=font("caption", s.olcek),
            ha="center", va="top", zorder=3)  # fmt: skip
    s.fig.text(0.5, alt - 0.004, "distances to scale (√), directions are not", ha="center", va="top",
               color=renk("ink-muted"), fontproperties=font("caption", s.olcek, 0.9))  # fmt: skip

    # Geçiş yolları: en yakın nokta r(ld), yön eşit aralıklı açılarda; yol en yakın noktaya diktir.
    n = len(gecisler)
    kirp = Circle((0, 0), R * 0.97, transform=ax.transData)  # yollar dış halkada biter, başlığa/kenara taşmaz
    sira = sorted(range(n), key=lambda i: gecisler[i].get("an", ""))  # takvim sırasıyla geçerler
    yollar = []
    for k, i in enumerate(sira):
        aci = math.radians(90 + 360 * k / n + (25 if tekil else 0))
        r = _r(gecisler[i]["ld"])
        p = np.array([r * math.cos(aci), r * math.sin(aci)])
        d = np.array([-math.sin(aci), math.cos(aci)])
        vurgulu = i == vurgu
        renk_ = renk("primary") if vurgulu else renk("data")
        cizgi = ax.plot([], [], color=renk_, lw=(3.2 if vurgulu else 1.6) * s.olcek, alpha=0.95 if vurgulu else 0.6,
                        zorder=6 if vurgulu else 4)[0]  # fmt: skip
        nokta = ax.scatter([], [], s=(90 if vurgulu else 40) * s.olcek**2, color=renk_, zorder=7)
        cizgi.set_clip_path(kirp)
        nokta.set_clip_path(kirp)
        etiket = ax.text(
            *(p + (0.06 * R) * p / max(np.linalg.norm(p), 1e-9)),
            f"{gecisler[i]['ad']}\n{sayi(gecisler[i]['ld'], 2 if gecisler[i]['ld'] < 1 else 1)}× Moon",
            color=renk("ink-primary") if vurgulu else renk("ink-secondary"),
            fontproperties=font("label" if vurgulu else "caption", s.olcek, 0.8 if vurgulu else 1.0),
            ha="center",
            va="center",
            alpha=0,
            zorder=8,
        )
        yollar.append((p, d, cizgi, nokta, etiket))

    # Tekil: son bölümde boyut karşılaştırması (aynı karede, diyagram solarken)
    boyut = None
    if tekil:
        bx = s.eksen(alt + 0.02, ust - 0.02, 0.08, 0.92)
        cap_min, cap_max = gecisler[0]["cap"]
        yapilar = _yapilar(cap_max)
        yuk = max(cap_max, max(h for _, h in yapilar)) * 1.15
        # eksen oranı eşit değil (x yapı sırası, y metre): daire, piksel oranıyla düzeltilmiş elips.
        # x aralığı, yapılar (2,2 birim) + asteroitin gerçek genişliği sığacak kadar.
        en_px, boy_px = 0.84 * genislik, (ust - alt - 0.04) * yukseklik
        k = (boy_px / (1.08 * yuk)) / en_px * cap_max  # asteroit genişliği / x aralığı
        W = max(3.2, 2.45 / max(1 - k, 0.2))
        x_m = (boy_px / (1.08 * yuk)) * (W / en_px)  # 1 metrenin x verisi karşılığı
        bx.set_xlim(0, W)
        bx.set_ylim(-0.08 * yuk, yuk)
        artistler = [bx.axhline(0, color=renk("land-edge"), lw=1.5 * s.olcek)]
        for j, (ad, h) in enumerate(yapilar):
            x = 0.35 + j * 1.0
            artistler.append(bx.add_patch(Rectangle((x, 0), 0.55, h, color=renk("land"), ec=renk("land-edge"))))
            artistler.append(bx.text(x + 0.275, h + 0.02 * yuk, f"{ad}\n{sayi(h)} m", ha="center", va="bottom",
                                     color=renk("ink-secondary"), fontproperties=font("caption", s.olcek)))  # fmt: skip
        cx = 2.3 + cap_max * x_m / 2
        artistler.append(bx.add_patch(Ellipse((cx, cap_max / 2), cap_max * x_m, cap_max, fill=False,
                                              ec=renk("primary"), ls=(0, (3, 3)), lw=2 * s.olcek)))  # fmt: skip
        artistler.append(bx.add_patch(Ellipse((cx, cap_min / 2), cap_min * x_m, cap_min, color=renk("primary"),
                                              alpha=0.85)))  # fmt: skip
        artistler.append(bx.text(cx, cap_max + 0.02 * yuk, f"{gecisler[0]['ad']}\n{sayi(cap_min)}–{sayi(cap_max)} m",
                                 ha="center", va="bottom", color=renk("ink-primary"),
                                 fontproperties=font("label", s.olcek, 0.85)))  # fmt: skip
        artistler.append(bx.text(W / 2, -0.06 * yuk, "estimated size (from brightness)", ha="center", va="top",
                                 color=renk("ink-muted"), fontproperties=font("caption", s.olcek)))  # fmt: skip
        bx.set_aspect("auto")
        for a in artistler:
            a.set_alpha(0)
        boyut = artistler

    hiz_yazi = s.fig.text(0.5, alt - 0.03, "", ha="center", va="top", color=renk("ink-secondary"),
                          fontproperties=font("label", s.olcek))  # fmt: skip
    diyagram = [*ax.patches, *ax.texts, *ax.lines, *ax.collections]
    oynatma = max(saniye - s.baslangic - 1.5, 1.0)
    gecis_sure = oynatma * 0.55 if tekil else GECIS_SN
    aralik = 0 if tekil else max((oynatma - gecis_sure - 1.0) / max(n - 1, 1), 0.25)
    boyut_bas = s.baslangic + oynatma * 0.6
    taban: dict = {}

    def guncelle(t: float) -> None:
        for k, (p, d, cizgi, nokta, etiket) in enumerate(yollar):
            u = (t - s.baslangic - k * aralik) / gecis_sure
            if u <= 0:
                continue
            u = min(u, 1.0)
            uz = R
            bas = p - d * uz
            simdi = bas + d * (2 * uz) * yumusat(u)
            cizgi.set_data([bas[0], simdi[0]], [bas[1], simdi[1]])
            nokta.set_offsets([simdi] if u < 1 else np.empty((0, 2)))
            etiket.set_alpha(min(max((u - 0.45) / 0.15, 0), 1))
        if tekil:
            hiz_yazi.set_text(f"{sayi(gecisler[0]['hiz'], 1)} km/s relative to Earth" if t > s.baslangic + 1 else "")
            if boyut is not None:
                gecis = yumusat((t - boyut_bas) / 0.8)
                if gecis > 0:
                    if not taban:  # solmanın ilk karesi: her parçanın o anki saydamlığı taban olur
                        taban.update({a: 1.0 if a.get_alpha() is None else a.get_alpha() for a in diyagram})
                    for a in diyagram:
                        a.set_alpha(taban[a] * (1 - gecis))
                for a in boyut:
                    a.set_alpha(gecis)
                hiz_yazi.set_alpha(1 - gecis)

    return s.calistir(cikti, guncelle)
