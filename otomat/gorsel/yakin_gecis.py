"""Yakın geçiş şablonu (uzay kanalı): ortada Dünya, Ay yörüngesi cetvel halkası, asteroitler en yakın noktaları kendi
mesafelerinde olan düz çizgilerle geçer. Mesafe ekseni karekök ölçekli (0,1–20 Ay mesafesi aynı karede okunsun);
halkalar gerçek değerleriyle etiketlidir. Tekil videoda son bölüm tahmini boyutu bilinen yapılarla karşılaştırır.

Geometri şematiktir: CAD yalnız en yakın mesafeyi verir, gerçek yörünge yönünü değil. Bu yüzden geçiş yönleri
eşit aralıklı açılara dağıtılır ve ekranda "distance to scale, directions are not" notu durur.
"""

import math
from pathlib import Path

import matplotlib.patheffects as pe
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


def _yerlestir(fig, ax, yollar: list, halka_yazilari: list, engeller: list, R: float, bosluk_px: float) -> None:
    """Etiketleri çakışmasız konuma koyar (2026-10-07: dokuz geçişte yazılar üst üste biniyordu).

    Asteroit etiketi kendi yolundan en az yarı kutusu kadar uzakta, önce dışta sonra içte, yola paralel kaydırılarak
    denenir; halka etiketleri en son boş açıya oturur. Hiçbir aday temiz değilse en az çakışan seçilir.
    """
    r = fig.canvas.get_renderer()
    sinir = ax.get_window_extent(r).padded(-bosluk_px)
    px = ax.transData.transform((1, 0))[0] - ax.transData.transform((0, 0))[0]  # 1 veri birimi = px (eşit oran)
    dolu = [k.padded(bosluk_px) for k in engeller]
    # yolların son hali ve halkalar: üstlerine binmek yazı çakışmasından ucuz ama boş yer varsa ondan kaçınılır
    noktalar = [p + d * R * u for p, d, *_ in yollar for u in np.linspace(-1, 1, 160)]
    noktalar += [_r(h) * np.array([math.cos(a), math.sin(a)]) for h, _ in halka_yazilari
                 for a in np.linspace(0, 2 * math.pi, 240)]  # fmt: skip
    cizgi_px = ax.transData.transform([n for n in noktalar if np.linalg.norm(n) <= R * 0.97])

    def maliyet(t) -> float:
        k = t.get_window_extent(r)
        disari = 0.0 if (k.x0 >= sinir.x0 and k.x1 <= sinir.x1 and k.y0 >= sinir.y0 and k.y1 <= sinir.y1) else 1e9
        ic = (cizgi_px[:, 0] > k.x0) & (cizgi_px[:, 0] < k.x1) & (cizgi_px[:, 1] > k.y0) & (cizgi_px[:, 1] < k.y1)
        return (
            disari
            + 50 * float(ic.sum())
            + sum(max(min(k.x1, d.x1) - max(k.x0, d.x0), 0) * max(min(k.y1, d.y1) - max(k.y0, d.y0), 0) for d in dolu)
        )

    def koy(t, cizgi_nokta, u, ek: float) -> None:
        """Kutunun u'ya bakan köşesini/kenarını çizgi noktasından `ek` kadar u yönüne koyar: kutu çizgiye
        bitişik durur, değmez (merkezden yerleştirmede çapraz yolda etiket çizgiden uzağa düşüyordu)."""
        k = t.get_window_extent(r)
        ha = "center" if abs(u[0]) < 0.35 else ("left" if u[0] > 0 else "right")
        va = "center" if abs(u[1]) < 0.35 else ("bottom" if u[1] > 0 else "top")
        pay = (abs(u[0]) * k.width / 2 if ha == "center" else 0) + (abs(u[1]) * k.height / 2 if va == "center" else 0)
        t.set_ha(ha)
        t.set_va(va)
        t.set_position(cizgi_nokta + u * (pay / px + ek))

    def sec(t, adaylar) -> None:
        """adaylar: (çizgi noktası, yön, ek, uzaklık cezası px); en düşük maliyetli aday kalır."""
        en_iyi = None
        for aday in adaylar:
            koy(t, *aday[:3])
            m = maliyet(t) + 2 * aday[3]
            if en_iyi is None or m < en_iyi[0]:
                en_iyi = (m, aday)
        koy(t, *en_iyi[1][:3])
        dolu.append(t.get_window_extent(r).padded(bosluk_px))

    aralik = bosluk_px / px
    for p, d, _, _, t in yollar:
        u = p / max(np.linalg.norm(p), 1e-9)
        sec(t, [(p + d * kay * R, yon * u, aralik + ek * R, (ek + abs(kay)) * R * px + (yon < 0) * 20)
                for yon in (1, -1) for ek in (0, 0.06) for kay in (0, 0.12, -0.12, 0.25, -0.25)])  # fmt: skip
    for h, t in halka_yazilari:
        adaylar = []
        for j, aci in enumerate((62, 118, 40, 140, 80, 100, 20, 160, 0, 180, -30, 210)):
            u = np.array([math.cos(math.radians(aci)), math.sin(math.radians(aci))])
            adaylar.append((u * _r(h), u, aralik, j * 5))
        sec(t, adaylar)


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

    hale = [pe.withStroke(linewidth=5 * s.olcek, foreground=renk("surface"))]  # üstünden geçen yollar okunsun
    halka_yazilari = []
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
        yazi = ax.text(
            0,
            0,
            "Moon's orbit" if ay else f"{sayi(h)}× Moon",
            color=renk("moon") if ay else renk("ink-muted"),
            fontproperties=font("caption", s.olcek),
            ha="center",
            va="center",
            zorder=5,
            path_effects=hale,
        )
        halka_yazilari.append((h, yazi))
    ay_diski = ax.add_patch(Circle((_r(1) * math.cos(math.radians(205)), _r(1) * math.sin(math.radians(205))),
                                   0.035 * R, color=renk("moon"), zorder=3))  # fmt: skip
    dunya = ax.add_patch(Circle((0, 0), 0.06 * R, color=renk("earth"), zorder=3))
    dunya_yazi = ax.text(0, -0.09 * R, "Earth", color=renk("ink-secondary"), fontproperties=font("caption", s.olcek),
                         ha="center", va="top", zorder=3)  # fmt: skip
    dipnot = s.fig.text(0.5, alt - 0.004, "distances to scale (√), directions are not", ha="center", va="top",
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
            *p,
            f"{gecisler[i]['ad']}\n{sayi(gecisler[i]['ld'], 2 if gecisler[i]['ld'] < 1 else 1)}× Moon",
            color=renk("ink-primary") if vurgulu else renk("ink-secondary"),
            fontproperties=font("label" if vurgulu else "caption", s.olcek, 0.8 if vurgulu else 1.0),
            ha="center",
            va="center",
            alpha=0,
            zorder=8,
            path_effects=hale,
        )
        yollar.append((p, d, cizgi, nokta, etiket))
    r_ = s.fig.canvas.get_renderer()
    engeller = [a.get_window_extent(r_) for a in (ay_diski, dunya, dunya_yazi, dipnot)]
    _yerlestir(s.fig, ax, yollar, halka_yazilari, engeller, R, 6 * s.olcek)

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
    diyagram = [*ax.patches, *ax.texts, *ax.lines, *ax.collections, dipnot]  # dipnot mesafeyi anlatır, boyutta söner
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
