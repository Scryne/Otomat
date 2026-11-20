"""Trend radarı testleri: yalnız ayrıştırıcılar ve saf fonksiyonlar sınanır (ağ yok)."""

import datetime as dt
import json
from pathlib import Path

from otomat.trend import radar

VERI = Path(__file__).parent / "veri" / "trend"


def _metin(ad: str) -> str:
    return (VERI / ad).read_text(encoding="utf-8")


def _gt(sorgu: str, geo: str, trafik: int, haberler: list[dict] | None = None) -> radar.GTKayit:
    return radar.GTKayit(
        sorgu=sorgu,
        geo=geo,
        trafik=trafik,
        zaman=dt.datetime(2026, 11, 20, tzinfo=dt.UTC),
        haberler=haberler or [],
    )


def _gunluk_json(bas: str, goruntulemeler: list[int]) -> str:
    """`bas` ("20261101") gününden başlayan ardışık günlük per-article yanıtı."""
    ilk = dt.datetime.strptime(bas, "%Y%m%d")
    elemanlar = [
        {"timestamp": (ilk + dt.timedelta(days=i)).strftime("%Y%m%d") + "00", "views": v}
        for i, v in enumerate(goruntulemeler)
    ]
    return json.dumps({"items": elemanlar})


def test_trafik_sayi():
    assert radar.trafik_sayi("200+") == 200
    assert radar.trafik_sayi("20K+") == 20000
    assert radar.trafik_sayi("2M+") == 2000000
    assert radar.trafik_sayi("1,000+") == 1000
    assert radar.trafik_sayi("abc") == 0


def test_normalize():
    assert radar.normalize("Grand_Theft_Auto_VI") == "grand theft auto vi"
    assert radar.normalize("Léa Seydoux") == "lea seydoux"
    assert radar.normalize("Robin (film)") == "robin"


def test_makale_uygun():
    for makale in (
        "Main_Page",
        "Special:Search",
        "Wikipedia:Featured_pictures",
        "File:WhatsApp.svg",
        "Deaths_in_2026",
        "List_of_highest-grossing_films",
        ".xxx",
        "-",
    ):
        assert not radar.makale_uygun(makale), makale
    assert radar.makale_uygun("Grand_Theft_Auto_VI")
    assert radar.makale_uygun("The_Hunger_Games:_Sunrise_on_the_Reaping")  # iki nokta başlıkta, ad alanı değil


def test_gt_ayristir():
    for geo, ad in (("US", "gt_US.xml"), ("GB", "gt_GB.xml")):
        kayitlar = radar.gt_ayristir(_metin(ad), geo)
        assert len(kayitlar) == 10 and all(k.geo == geo for k in kayitlar)
    ilki = radar.gt_ayristir(_metin("gt_US.xml"), "US")[0]
    assert ilki.sorgu == "yashasvi jaiswal" and ilki.trafik == 1000
    assert ilki.haberler and ilki.haberler[0]["url"].startswith("http")
    assert ilki.resim and ilki.resim.startswith("https://")
    assert ilki.zaman.tzinfo is not None and ilki.zaman.utcoffset() == dt.timedelta(0)


def test_wiki_top_ayristir():
    makaleler = radar.wiki_top_ayristir(_metin("wiki_top.json"))
    adlar = [m[0] for m in makaleler]
    for dislanan in ("Main_Page", "Special:Search", "Deaths_in_2026", ".xxx"):
        assert dislanan not in adlar
    assert makaleler[0] == ("Grand_Theft_Auto_VI", 750227)  # ilk sıradaki uygun makale
    assert makaleler == sorted(makaleler, key=lambda m: -m[1])[: len(makaleler)]  # liste sırası korunur


def test_artis_hesapla():
    assert radar.artis_hesapla(_metin("wiki_makale_gta6.json")) > 5
    assert radar.artis_hesapla(_gunluk_json("20261101", [100] * 5)) is None  # 7'den az eleman
    assert radar.artis_hesapla(_gunluk_json("20261101", [100] * 10)) == 1.0  # düz seri
    # son 3 gün tabana girmez: yükselişin başı tabanı şişirmesin
    seri = [100] * 10 + [1000, 1000, 5000]
    assert radar.artis_hesapla(_gunluk_json("20261101", seri)) == 50.0


def test_birlestir_wiki_adi_kazanir():
    gt = [_gt("grand theft auto vi", "US", 5000)]
    artislar = {"Grand_Theft_Auto_VI": 9.8}
    konular = radar.birlestir(gt, [("Grand_Theft_Auto_VI", 750227)], artislar)
    assert len(konular) == 1
    k = konular[0]
    assert (k.anahtar, k.ad) == ("grand theft auto vi", "Grand Theft Auto VI")
    assert k.gt_trafik == 5000 and k.gt_geolar == ["US"]
    assert k.wiki_makale == "Grand_Theft_Auto_VI" and k.wiki_goruntuleme == 750227
    assert k.wiki_artis == 9.8


def test_tek_kelimelik_eslesmez():
    konular = radar.birlestir([_gt("vgk", "US", 200)], [("VGK_Arena", 500)], {})
    assert len(konular) == 2
    assert {k.anahtar for k in konular} == {"vgk", "vgk arena"}


def test_iki_geo_toplanir():
    konular = radar.birlestir([_gt("gold price", "US", 10000), _gt("gold price", "GB", 2000)], [], {})
    assert len(konular) == 1
    k = konular[0]
    assert k.gt_trafik == 12000 and k.gt_geolar == ["US", "GB"]


def test_haberler_tekrarsiz_ve_sinirli():
    h1 = {"baslik": "a", "url": "https://x/1", "kaynak": "X"}
    h2 = {"baslik": "b", "url": "https://x/2", "kaynak": "Y"}
    k = radar.birlestir([_gt("gold price", "US", 10000, [h1, h2]), _gt("gold price", "GB", 2000, [h1])], [], {})[0]
    assert [h["url"] for h in k.haberler] == ["https://x/1", "https://x/2"]  # url tekrarı girmez
    haberler = [{"baslik": f"h{i}", "url": f"https://x/{i}", "kaynak": "X"} for i in range(12)]
    cok = radar.birlestir([_gt("konu a", "US", 100, haberler[:6]), _gt("konu a", "GB", 100, haberler[6:])], [], {})[0]
    assert len(cok.haberler) == 10  # en çok 10


def test_skor_sirasina_gore_azalan():
    konular = radar.birlestir([_gt("kucuk konu", "US", 100), _gt("buyuk konu", "US", 1_000_000)], [], {})
    assert [k.anahtar for k in konular] == ["buyuk konu", "kucuk konu"]
    assert all(konular[i].skor >= konular[i + 1].skor for i in range(len(konular) - 1))


def test_esit_skorda_anahtara_gore_artan():
    konular = radar.birlestir([_gt("beta", "US", 100), _gt("alpha", "US", 100)], [], {})
    assert [k.anahtar for k in konular] == ["alpha", "beta"]


def test_skorla_formul():
    # 1.0*log10(1000) + 0.8*2 + 1.2*log10(1000) + 1.5*log2(8) = 3 + 1.6 + 3.6 + 4.5
    k = radar.Konu(anahtar="x", ad="x", gt_trafik=999, gt_geolar=["US", "GB"], wiki_goruntuleme=999, wiki_artis=8.0)
    assert radar.skorla(k) == 12.7
    assert radar.skorla(radar.Konu(anahtar="y", ad="y")) == 0.0  # veri yoksa skor da yok
    artissiz = radar.Konu(anahtar="z", ad="z", gt_trafik=999, wiki_artis=None)
    assert radar.skorla(artissiz) == round(3.0 + 0.0, 3)  # artış terimi max(1, 1) ile 0
