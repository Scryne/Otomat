"""Anlatım katmanının LLM'siz kısmı: olgu cümleleri, kapılar, seslendirme dönüşümü, yedekler, altyazı."""

import json
import re
from pathlib import Path

import pytest

from otomat.anlati import kapilar, olgu_cumleleri, yedek
from otomat.anlati.anlatim import seslendir
from otomat.ses import Parca, altyazi_parcalari
from otomat.veri import dunya_bankasi, eurostat, usgs

KAYIT = Path(__file__).parent / "veri" / "kayit"
CEKILDI = "2026-10-02T17:00:00+00:00"


def oku(ad):
    return json.loads((KAYIT / ad).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def paketler():
    sonuc = usgs.paketler(oku("usgs.json"), "u", CEKILDI)
    gecerli = dunya_bankasi.ulkeler(oku("wb_ulkeler.json"))
    g = {"kod": "MS.MIL.XPND.GD.ZS", "ad": "military spending as a share of GDP", "birim": "% of GDP", "ondalik": 1}
    sonuc += dunya_bankasi.paketler(g, oku("wb_MS.MIL.XPND.GD.ZS.json"), gecerli, "u", CEKILDI)
    v = {"kod": "sdg_08_10", "ad": "real GDP per person", "birim": "€", "ondalik": 0}
    sonuc += eurostat.paketler(v, oku("es_sdg_08_10.json"), "u", CEKILDI)
    return sonuc


def test_her_varyant_her_pakette_kurulur(paketler):
    """Her olgu tipi × her varyant: eksik anahtar yok, kalıntı tutucu yok, cümle boş değil."""
    turler = set()
    for p in paketler:
        turler.add(p.tur)
        degerler = {k: o.deger for k, o in p.olgular.items()}
        degerler["__ondalik"] = p.gorsel.get("ondalik")
        birimler = {k: o.birim for k, o in p.olgular.items()}
        for varyant in olgu_cumleleri.HAVUZ[p.tur]:
            cumleler = varyant(degerler, birimler)
            assert cumleler and all(c.strip() for c in cumleler)
            assert not any("{" in c or "None" in c for c in cumleler)
    assert turler == set(olgu_cumleleri.HAVUZ)
    assert all(len(v) >= 5 for v in olgu_cumleleri.HAVUZ.values())


def test_olgu_cumlelerindeki_sayilar_pakette_var(paketler):
    """Cümlelerdeki her sayı paketin bir olgusundan gelir (K-4): uydurma sayı yok."""
    for p in paketler:
        # şablonun sabit tanımları: büyüklük eşikleri, "top 10", sıra numaraları, yaş aralığı
        izinli = {"1", "2", "3", "4.5", "6", "7", "10", "30", "365", "25", "34"}
        for o in p.olgular.values():
            if isinstance(o.deger, int | float):
                izinli |= {f"{o.deger:,.0f}", f"{o.deger:,.1f}", f"{o.deger:,}", str(o.deger)}
            else:
                izinli |= {x.rstrip(",.") for x in re.findall(r"\d[\d,]*(?:\.\d+)?", str(o.deger))}
        degerler = {k: o.deger for k, o in p.olgular.items()}
        degerler["__ondalik"] = p.gorsel.get("ondalik")
        birimler = {k: o.birim for k, o in p.olgular.items()}
        for varyant in olgu_cumleleri.HAVUZ[p.tur]:
            for sayi in re.findall(r"\d[\d,]*(?:\.\d+)?", " ".join(varyant(degerler, birimler))):
                assert sayi.rstrip(",.") in izinli, (p.anahtar, sayi)


def test_tutucu_kapisi(paketler):
    p = next(x for x in paketler if x.tur == "bolge_yillik")
    assert kapilar.tutucu_kapisi("Every quake in {region}", p) == []
    assert "bilinmeyen tutucu {country}" in kapilar.tutucu_kapisi("{country} shook", p)
    assert "çıplak rakam" in kapilar.tutucu_kapisi("{region} shook 600 times", p)
    assert any("yazıyla sayı" in h for h in kapilar.tutucu_kapisi("{region} shook thousands of times", p))
    on = next(x for x in paketler if x.tur == "en_yuksek_10")
    assert kapilar.tutucu_kapisi("Top 10 Military Spenders", on) == []


def test_politika_ve_soru():
    assert kapilar.politika_kapisi("Subscribe for more!") == ["yasak ifade: subscribe"]
    assert kapilar.politika_kapisi("A deadly year") == ["yasak ifade: deadly"]
    assert kapilar.politika_kapisi("Where does the ground shake most?") == []
    assert kapilar.olgusuz_soru("Is your country on this map?")
    assert not kapilar.olgusuz_soru("Did {region} shake most?")
    assert not kapilar.olgusuz_soru("Japan shook a lot.")


def test_doldur_birimle(paketler):
    p = next(x for x in paketler if x.kol == "dunya_bankasi" and x.tur == "en_yuksek_10")
    dolu = kapilar.doldur("{rank1_country} at {rank1_value}", p)
    assert dolu.endswith("% of GDP") and "{" not in dolu


def test_baslik_duzeni():
    assert kapilar.baslik_duzeni("countries with the biggest rise in GDP") == "Countries with the Biggest Rise in GDP"
    assert kapilar.baslik_duzeni("the 10 strongest quakes") == "The 10 Strongest Quakes"


def test_seslendir():
    assert seslendir("a median of 1.6%") == "a median of 1 point 6%"
    assert seslendir("€4,800 and $129,000") == "4,800 euros and 129,000 dollars"
    assert seslendir("20,570 people per km²") == "20,570 people per square kilometers"


def test_yedekler_kapidan_gecer(paketler):
    for p in paketler:
        b = yedek.baslik(p)
        assert len(b) <= 70 and not kapilar.politika_kapisi(b)
    for kalip in yedek.KANCALAR:
        k = yedek.kanca(kalip, "t")
        assert not kapilar.politika_kapisi(k) and not kapilar.SAYI_KELIME.search(k)


def test_altyazi_parcalari():
    p = altyazi_parcalari([Parca(1.0, 3.0, "one two three four five six seven eight")], kelime=4)
    assert [x.metin for x in p] == ["one two three four", "five six seven eight"]
    assert p[0].bas == 1.0 and abs(p[-1].son - 3.0) < 1e-9
