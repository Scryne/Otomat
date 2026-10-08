"""Uzay kanalı: JPL CAD ve Exoplanet Archive adaptörleri (kayıtlı gerçek yanıtlar, 2026-10-06), anlatı ve kapılar."""

import datetime as dt
import itertools
import json
import re
from pathlib import Path

import numpy as np
import pytest

from otomat import kanal
from otomat.anlati import kapilar, olgu_cumleleri, yedek
from otomat.gorsel import kimlik, sablonlar
from otomat.veri import jpl, otegezegen

KAYIT = Path(__file__).parent / "veri" / "kayit"
GUN = dt.date(2026, 10, 6)


@pytest.fixture(autouse=True)
def uzay(monkeypatch):
    monkeypatch.setenv("OTOMAT_KANAL", "veri-uzay")
    kanal._aktif.cache_clear()
    kimlik.tokenlar.cache_clear()  # renkler kanala bağlı; Earth'ünkiler kalmasın
    yield
    kanal._aktif.cache_clear()
    kimlik.tokenlar.cache_clear()


def _jpl():
    return jpl.paketler(json.loads((KAYIT / "jpl_cad.json").read_text()), "u", "2026-10-06T19:00:00+00:00", GUN)


def _exo():
    return otegezegen.paketler(json.loads((KAYIT / "otegezegen.json").read_text()), "u", "x", GUN)


def test_cap_kadirden_aralik():
    # H=27,1: D = 1329/√p × 10^(−5,42) km → p=0,25: 10,1 m; p=0,05: 22,6 m
    g = jpl.Gecis("X", dt.datetime(2026, 10, 5, tzinfo=dt.UTC), 0.59, 228_000, 9.7, 27.1)
    assert g.cap_m == (10, 23)


def test_jpl_paketleri():
    pk = _jpl()
    turler = {p.tur for p in pk}
    assert turler == {"yakin_gecis_liste", "yakin_gecis_tekil"}
    liste = next(p for p in pk if p.tur == "yakin_gecis_liste")
    o = {k: v.deger for k, v in liste.olgular.items()}
    assert o["closest_name"] == "2026 TP2" and o["closest_distance_ld"] == 0.59
    assert o["closer_than_moon"] == 1 and o["closest_size_min_m"] < o["closest_size_max_m"]
    gecisler = liste.gorsel["gecisler"]
    assert [g["ld"] for g in gecisler] == sorted(g["ld"] for g in gecisler), "liste en yakından başlar"
    assert all(p.olgular["distance_ld"].deger <= jpl.TEKIL_LD for p in pk if p.tur == "yakin_gecis_tekil")


def test_otegezegen_paketleri_kapsamli_ve_ayrisik():
    pk = _exo()
    assert len({p.anahtar for p in pk}) == len(pk), "aynı gezegen iki kez seçilebilir olmasın"
    siralar = {p.tur: p for p in pk if p.tur != "gezegen_tekil"}
    assert set(siralar) == {"en_yakin_8", "en_sicak_8", "en_kisa_yil_8"}  # "en büyük" bilerek yok
    yakin = siralar["en_yakin_8"]
    yildizlar = [yakin.olgular[f"rank{i}_star"].deger for i in (1, 2, 3)]
    assert len(set(yildizlar)) == 3, "en yakınlar listesinde sistem başına tek gezegen"
    for p in siralar.values():
        degerler = [o["deger"] for o in p.gorsel["ogeler"]]
        assert len(set(degerler[:4])) == 4, f"{p.tur}: ilk dört gösterimde ayrışmalı"
        assert "in front of their star" in p.olgular["comparison_scope"].deger


@pytest.mark.parametrize("kaynak", ["jpl", "exo"])
def test_her_paket_anlatilir_ve_cizilebilir(kaynak):
    for p in _jpl() if kaynak == "jpl" else _exo():
        cumleler, _ = olgu_cumleleri.cumleler(p, "2026-10-06")
        metin = " ".join(cumleler)
        assert cumleler and "{" not in metin and "None" not in metin
        assert not kapilar.politika_kapisi(metin), f"{p.tur}: olgu cümlesi politika kapısına takıldı: {metin}"
        assert p.gorsel["sablon"] in sablonlar.secenekler(p)
        assert yedek.baslik(p) and len(yedek.baslik(p)) <= 70


def test_uzay_politikasi_korku_dilini_reddeder():
    assert kapilar.politika_kapisi("Will this asteroid hit Earth?")
    assert kapilar.politika_kapisi("A dangerous near miss")
    assert not kapilar.politika_kapisi("This rock passed closer than the Moon.")


def test_uzay_kaliplari_ve_yedek_kancalar():
    from otomat.anlati import anlatim

    k = kanal.aktif()
    assert "senin_ulken" not in k.kaliplar and set(k.kaliplar) <= set(anlatim.TUM_KALIPLAR)
    assert set(k.kaliplar) <= set(k.yedek_kancalar)
    for kalip in k.kaliplar:
        assert not kapilar.politika_kapisi(yedek.kanca(kalip, "t"))


def test_kalip_sayisi_tutucu_kapisinda_izinli():
    p = next(p for p in _exo() if p.tur == "en_sicak_8")
    assert kapilar.izinli_sayilar(p) == {"8"}


@pytest.mark.parametrize("kaynak", ["jpl", "exo"])
def test_her_varyant_kurulur_ve_sayilar_paketten(kaynak):
    """Her tip × her varyant; cümledeki her sayı paketin bir olgusundan (K-4)."""
    from otomat.anlati import uzay_cumleleri

    turler = set()
    for p in _jpl() if kaynak == "jpl" else _exo():
        turler.add(p.tur)
        izinli = {"1", "2", "3"}  # sıra numaraları
        for o in p.olgular.values():
            if isinstance(o.deger, int | float):
                izinli |= {f"{o.deger:,.0f}", f"{o.deger:,.1f}", f"{o.deger:,.2f}", f"{o.deger:,}", str(o.deger)}
            else:
                izinli |= {x.rstrip(",.") for x in re.findall(r"\d[\d,]*(?:\.\d+)?", str(o.deger))}
        degerler = {k: o.deger for k, o in p.olgular.items()}
        birimler = {k: o.birim for k, o in p.olgular.items()}
        for varyant in uzay_cumleleri.HAVUZ[p.tur]:
            metin = " ".join(varyant(degerler, birimler))
            assert "{" not in metin and "None" not in metin
            for sayi in re.findall(r"(?:(?<!\w)-)?\d[\d,]*(?:\.\d+)?", metin):
                assert sayi.rstrip(",.") in izinli, (p.anahtar, sayi, metin)
    beklenen = {"yakin_gecis_liste", "yakin_gecis_tekil"} if kaynak == "jpl" else {
        "gezegen_tekil", "en_yakin_8", "en_sicak_8", "en_kisa_yil_8"}  # fmt: skip
    assert turler == beklenen
    assert all(len(uzay_cumleleri.HAVUZ[t]) >= 5 for t in turler)


def test_rakamli_ad_tutucuya_cevrilir():
    from otomat.anlati.anlatim import _tutucuya_cevir

    p = next(p for p in _jpl() if p.tur == "yakin_gecis_tekil")
    ad = p.olgular["name"].deger
    assert _tutucuya_cevir(f"Asteroid {ad} Slipped Past the Moon", p) == "Asteroid {name} Slipped Past the Moon"
    assert _tutucuya_cevir("Asteroid {name} again", p) == "Asteroid {name} again"
    assert kapilar.tutucu_kapisi(_tutucuya_cevir(f"{ad} passed by", p), p) == []


def test_baslik_duzeni_ozel_adi_korur():
    assert kapilar.baslik_duzeni("LTT 1445 A b next to earth", ("LTT 1445 A b",)) == "LTT 1445 A b Next to Earth"
    assert kapilar.baslik_duzeni("the hottest of all") == "The Hottest of All"


# 2026-10-07 karesi: dokuz geçişte "Moon's orbit" TB3'e, TV2 dipnota biniyordu; çizgiler etiketlerin içinden geçiyordu.
GECISLER_1007 = [("2026 TP2", 0.59), ("2026 TU3", 0.83), ("2026 TS2", 1.3), ("2026 TB3", 1.7), ("2026 TQ1", 2.2),
                 ("2026 TX", 2.2), ("2026 TA", 2.3), ("2026 TV2", 2.7), ("2026 TC2", 2.8)]  # fmt: skip


def _yakin_gecis_son_kare(monkeypatch, gecisler):
    from otomat.gorsel import yakin_gecis

    yakalanan = {}

    def calistir(self, cikti, guncelle):
        yakalanan["sahne"], yakalanan["guncelle"] = self, guncelle
        return cikti

    monkeypatch.setattr(yakin_gecis.Sahne, "calistir", calistir)
    g = [{"ad": ad, "ld": ld, "an": f"{i:02d}", "cap": [10, 20], "hiz": 8.0} for i, (ad, ld) in enumerate(gecisler)]
    yakin_gecis.ciz(g, "Test", "Test", Path("yok.mp4"), saniye=25)
    yakalanan["guncelle"](25.0)
    return yakalanan["sahne"]


@pytest.mark.parametrize("adet", [9, 6, 3])
def test_yakin_gecis_son_karede_yazilar_cakismaz(monkeypatch, adet):
    s = _yakin_gecis_son_kare(monkeypatch, GECISLER_1007[:adet])
    r = s.fig.canvas.get_renderer()
    ax = next(a for a in s.fig.axes if a.lines)
    gorunen = [t for t in [*ax.texts, *s.fig.texts] if t.get_text().strip() and t.get_alpha() != 0]
    kutular = [(t.get_text(), t.get_window_extent(r)) for t in gorunen]
    cakisan = [(a, b) for (a, ka), (b, kb) in itertools.combinations(kutular, 2) if ka.overlaps(kb)]
    assert not cakisan
    # her asteroit etiketi kendi yoluna değmez ama en yakın noktasından da uzağa düşmez (hangi yolun olduğu okunsun;
    # çakışmadan kaçan ilk yerleştirici TP2'yi Dünya'nın yanına, TB3 ile TQ1'i birbirinin yerine koymuştu)
    etiketler = [t for t in ax.texts if "\n" in t.get_text()]
    assert len(etiketler) == len(ax.lines) == adet
    for cizgi, etiket in zip(ax.lines, etiketler, strict=True):
        (x0, x1), (y0, y1) = cizgi.get_xdata(), cizgi.get_ydata()
        noktalar = ax.transData.transform([(x0 + (x1 - x0) * u, y0 + (y1 - y0) * u) for u in np.linspace(0, 1, 400)])
        kutu = etiket.get_window_extent(r)
        assert not any(kutu.contains(x, y) for x, y in noktalar), etiket.get_text()
        orta, uc = noktalar[200], noktalar[0]  # yol p ± d·R: orta nokta en yakın geçiş
        uzaklik = np.hypot(max(kutu.x0 - orta[0], 0, orta[0] - kutu.x1), max(kutu.y0 - orta[1], 0, orta[1] - kutu.y1))
        assert uzaklik < 0.3 * np.hypot(*(orta - uc)), etiket.get_text()


@pytest.mark.parametrize("adet", [9, 6, 3])
def test_yakin_gecis_baska_yol_yaziya_degmez(monkeypatch, adet):
    # 10-07: TQ1'in yolu kırpma çemberinde TX etiketinin kenarında bitiyordu (seyrek örnek, boşluksuz kutu)
    s = _yakin_gecis_son_kare(monkeypatch, GECISLER_1007[:adet])
    r = s.fig.canvas.get_renderer()
    ax = next(a for a in s.fig.axes if a.lines)
    yazilar = [t for t in [*ax.texts, *s.fig.texts] if t.get_text().strip() and t.get_alpha() != 0]
    for cizgi in ax.lines:
        (x0, x1), (y0, y1) = cizgi.get_xdata(), cizgi.get_ydata()
        noktalar = ax.transData.transform([(x0 + (x1 - x0) * u, y0 + (y1 - y0) * u) for u in np.linspace(0, 1, 2000)])
        yol, donusum = cizgi.get_clip_path().get_transformed_path_and_affine()
        gorunen = noktalar[yol.contains_points(noktalar, transform=donusum)]
        for t in yazilar:
            kutu = t.get_window_extent(r).padded(2)
            assert not any(kutu.contains(x, y) for x, y in gorunen), t.get_text()
