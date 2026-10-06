"""Uzay kanalı: JPL CAD ve Exoplanet Archive adaptörleri (kayıtlı gerçek yanıtlar, 2026-10-06), anlatı ve kapılar."""

import datetime as dt
import json
import re
from pathlib import Path

import pytest

from otomat import kanal
from otomat.anlati import kapilar, olgu_cumleleri, yedek
from otomat.gorsel import sablonlar
from otomat.veri import jpl, otegezegen

KAYIT = Path(__file__).parent / "veri" / "kayit"
GUN = dt.date(2026, 10, 6)


@pytest.fixture(autouse=True)
def uzay(monkeypatch):
    monkeypatch.setenv("OTOMAT_KANAL", "uzay")
    kanal._aktif.cache_clear()
    yield
    kanal._aktif.cache_clear()


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
        assert "crossing their star" in p.olgular["comparison_scope"].deger


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
