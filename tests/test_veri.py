"""Sözleşme testleri: kayıtlı gerçek yanıtlar (2026-10-02) üzerinde adaptörler."""

import datetime as dt
import json
from pathlib import Path

import pytest

from otomat import durum
from otomat.veri import dunya_bankasi, eurostat, usgs

KAYIT = Path(__file__).parent / "veri" / "kayit"
CEKILDI = "2026-10-02T17:00:00+00:00"


def oku(ad):
    return json.loads((KAYIT / ad).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("yer", "beklenen"),
    [
        ("80 km ENE of Tadine, New Caledonia", "New Caledonia"),
        ("south of the Fiji Islands", "Fiji"),
        ("Kermadec Islands region", "Kermadec Islands"),
        ("central Mid-Atlantic Ridge", "central Mid-Atlantic Ridge"),
        ("12 km S of Ankara, Turkey", "Turkey"),
        (None, "Unknown"),
    ],
)
def test_bolge_adi(yer, beklenen):
    assert usgs.bolge(yer) == beklenen


def test_okyanus_bolgesi_ulke_sayilmaz():
    assert usgs.kara_mi("Indonesia")
    assert not usgs.kara_mi("central Mid-Atlantic Ridge")
    assert not usgs.kara_mi("Drake Passage")


def test_usgs_paketleri():
    paketler = usgs.paketler(oku("usgs.json"), "u", CEKILDI)
    turler = {p.tur for p in paketler}
    assert turler == {"dunya_30g", "bolge_yillik", "en_guclu_10"}
    for p in paketler:
        assert p.kaynak.ad == "USGS"
        assert all(o.anlam for o in p.olgular.values())
    bolgeler = [p for p in paketler if p.tur == "bolge_yillik"]
    assert bolgeler and all(usgs.kara_mi(p.olgular["region"].deger) for p in bolgeler)
    ilk = bolgeler[0]
    assert ilk.olgular["quake_count"].deger == len(ilk.gorsel["olaylar"])
    en10 = next(p for p in paketler if p.tur == "en_guclu_10")
    degerler = [o["deger"] for o in en10.gorsel["ogeler"]]
    assert degerler == sorted(degerler, reverse=True) and len(degerler) == 10
    assert en10.olgular["rank1_magnitude"].deger == degerler[0]


def test_dunya_bankasi_toplamlari_ayiklar_ve_siralar():
    gecerli = dunya_bankasi.ulkeler(oku("wb_ulkeler.json"))
    assert "TUR" in gecerli and "WLD" not in gecerli and "AFE" not in gecerli
    g = {"kod": "SP.DYN.LE00.IN", "ad": "life expectancy at birth", "birim": "years", "ondalik": 1}
    paketler = dunya_bankasi.paketler(g, oku("wb_SP.DYN.LE00.IN.json"), gecerli, "u", CEKILDI)
    assert {p.tur for p in paketler} == {"en_yuksek_10", "en_dusuk_10", "en_cok_artan_10"}
    yuksek = next(p for p in paketler if p.tur == "en_yuksek_10")
    dusuk = next(p for p in paketler if p.tur == "en_dusuk_10")
    assert (
        yuksek.olgular["rank1_value"].deger > yuksek.olgular["median_value"].deger > dusuk.olgular["rank1_value"].deger
    )
    assert all(o["iso3"] in gecerli for o in yuksek.gorsel["ogeler"])
    assert len(yuksek.gorsel["koroplet"]) == yuksek.olgular["countries_compared"].deger


def test_dunya_bankasi_degisim_tutarli():
    gecerli = dunya_bankasi.ulkeler(oku("wb_ulkeler.json"))
    g = {"kod": "SP.DYN.LE00.IN", "ad": "life expectancy at birth", "birim": "years", "ondalik": 1}
    p = next(x for x in dunya_bankasi.paketler(g, oku("wb_SP.DYN.LE00.IN.json"), gecerli, "u", CEKILDI)
             if x.tur == "en_cok_artan_10")  # fmt: skip
    o = p.olgular
    assert o["to_year"].deger - o["from_year"].deger == 10
    assert o["rank1_to"].deger - o["rank1_from"].deger >= o["rank2_to"].deger - o["rank2_from"].deger - 0.11


def test_eurostat_jsonstat():
    tablo, isimler = eurostat.yil_tablosu(oku("es_sdg_04_20.json"))
    yil = max(tablo)
    assert "GRC" in tablo[yil] and "EU27_2020" not in tablo[yil]
    assert isimler["GRC"] == "Greece"
    assert all(0 < v < 100 for v in tablo[yil].values())


def test_eurostat_filtre_eksikse_hata():
    js = oku("es_sdg_08_10.json")
    bozuk = dict(js, id=js["id"], size=[2 if b == "unit" else n for b, n in zip(js["id"], js["size"], strict=True)])
    with pytest.raises(ValueError, match="filtre eksik"):
        eurostat.yil_tablosu(bozuk)


def test_tekrar_engeli(tmp_path):
    db = durum.baglan(tmp_path / "t.db")
    p = usgs.paketler(oku("usgs.json"), "u", CEKILDI)[0]
    bugun = dt.date(2026, 10, 2)
    assert durum.taze_mi(db, p, bugun)
    durum.kaydet(db, p, bugun)
    assert not durum.taze_mi(db, p, bugun + dt.timedelta(days=59))
    assert durum.taze_mi(db, p, bugun + dt.timedelta(days=61))


def test_hash_kararli():
    a = usgs.paketler(oku("usgs.json"), "u", CEKILDI)
    b = usgs.paketler(oku("usgs.json"), "baska-url", "2030-01-01T00:00:00+00:00")
    assert [p.hash for p in a] == [p.hash for p in b]
    assert len({p.hash for p in a}) == len(a)
