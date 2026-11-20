"""Trend hattının saf fonksiyonları: senaryo kapıları, kurgu ipuçları, kelime hizalama, kesit planı, şablon çıktısı."""

from otomat.trend import kesit, kurgu, senaryo, zamanla


def _sahne(tur, anlatim="one two three four five six seven eight", **kw):
    return {"tur": tur, "anlatim": anlatim, **kw}


def _gecerli_senaryo():
    s = [_sahne("foto", gorsel="G1", baslik="A big launch")]
    turler = ["sayi", "foto", "manset", "foto", "zaman", "foto", "alinti", "foto", "ikili", "foto"]
    alanlar = {"sayi": {"deger": "750227", "etiket": "views in a single day"},
               "foto": {"gorsel": "G2"}, "manset": {"mansetler": [{"kaynak": "BBC", "baslik": "x"}]},
               "zaman": {"olaylar": [{"tarih": "2013", "olay": "x"}]}, "alinti": {"metin": "x", "kim": "y"},
               "ikili": {"sol": {"etiket": "a", "deger": "1"}, "sag": {"etiket": "b", "deger": "2"}}}  # fmt: skip
    uzun = " ".join(["word"] * 30)
    g = 1
    for b in range(4):
        s.append(_sahne("bolum", "Chapter line here", no=f"0{b + 1}", baslik="Act"))
        for t in turler:
            ek = dict(alanlar[t])
            if t == "foto":
                g += 1
                ek["gorsel"] = f"G{g}"
            s.append(_sahne(t, uzun if t in ("foto", "manset", "zaman") else " ".join(["w"] * 20), **ek))
    s.append(_sahne("kapanis", "the end line", metin="The end"))
    return {"tez": "x", "sahneler": s, "baslik_adaylari": ["A title"], "kesitler": [{}, {}, {}]}


def test_yapi_kapisi_gecerli_senaryoyu_gecirir():
    assert senaryo.yapi_kapisi(_gecerli_senaryo(), gorsel_sayisi=30) == []


def test_yapi_kapisi_ayni_tur_ardisik_ve_soru_basligi_yakalar():
    s = _gecerli_senaryo()
    s["sahneler"].insert(3, dict(s["sahneler"][2]))  # iki sayi üst üste
    s["baslik_adaylari"] = ["Why is it everywhere?"]
    hata = senaryo.yapi_kapisi(s, 20)
    assert any("aynı tür (sayi)" in h for h in hata)
    assert any("soru ile bitiyor" in h for h in hata)


def test_yapi_kapisi_gecersiz_gorsel_ve_yasak_ifade():
    s = _gecerli_senaryo()
    s["sahneler"][0]["gorsel"] = "G9"
    s["sahneler"][1]["anlatim"] = "Let's dive in to the numbers now"
    hata = senaryo.yapi_kapisi(s, 5)
    assert any("geçersiz (G9)" in h for h in hata)
    assert any("yasak ifade" in h for h in hata)


def test_sayi_kapisi_esdeger_bicimleri_kabul_eder():
    kaynak = "It sold 265 million copies and earned $1.8 billion in 2026; 750,227 views."
    s = {"sahneler": [_sahne("sayi", "It earned $1.8 billion in 2026.", deger="750227", etiket="views"),
                      _sahne("foto", "GTA V cost $265M to make.")]}  # fmt: skip
    assert senaryo.sayi_kapisi(s, kaynak) == []
    s["sahneler"].append(_sahne("foto", "Over 90 million players joined."))
    assert any("'90'" in h for h in senaryo.sayi_kapisi(s, kaynak))


def test_ipucu_zamani_kelime_ve_obek():
    sh = {"kelimeler": [{"w": "In", "s": 0.1, "e": 0.2}, {"w": "2013,", "s": 0.3, "e": 0.8},
                        {"w": "the", "s": 0.9, "e": 1.0}, {"w": "trailer", "s": 1.1, "e": 1.5}]}  # fmt: skip
    assert abs(kurgu.ipucu_zamani(sh, "trailer", 9) - 1.02) < 1e-6
    assert abs(kurgu.ipucu_zamani(sh, "2013", 9) - 0.22) < 1e-6
    assert kurgu.ipucu_zamani(sh, "missing", 9) == 9


def test_hizala_rakam_ve_bosluk_doldurma():
    whisper = [("Yesterday", 0.0, 0.4), ("750,000", 0.5, 1.6), ("people", 1.7, 2.0), ("looked", 2.1, 2.3)]
    k = zamanla.hizala("Yesterday 750,000 people suddenly looked", whisper)
    assert [x["w"] for x in k] == ["Yesterday", "750,000", "people", "suddenly", "looked"]
    assert k[1]["s"] == 0.5 and k[1]["e"] == 1.6
    assert 2.0 <= k[3]["s"] <= 2.1  # eşleşmeyen kelime komşularından doldurulur


def test_kesit_plani_yeniden_zamanlar():
    plan = {"sure": 30, "muzik": None, "sahneler": [
        {"id": "s01", "tur": "foto", "bas": 0, "sure": 10, "kelimeler": []},
        {"id": "s02", "tur": "sayi", "bas": 10, "sure": 8, "kelimeler": [{"w": "x", "s": 1, "e": 2}]},
        {"id": "s03", "tur": "foto", "bas": 18, "sure": 12, "kelimeler": [{"w": "y", "s": 1, "e": 3}]}]}  # fmt: skip
    alt, t0 = kesit.kesit_plani(plan, [1, 2])
    assert t0 == 10
    assert [s["bas"] for s in alt["sahneler"]] == [0, 8]
    assert alt["sahneler"][-1]["sure"] == 3.6  # son kelime + 0,6
    assert alt["sure"] == 11.6


def test_sahne_sablonlari_kayit_ve_gecis():
    sh = {"id": "s05", "tur": "foto", "sure": 6.0, "gorsel": "assets/img/g01.jpg", "baslik": "Big night",
          "kelimeler": [], "anlatim": "x"}  # fmt: skip
    html = kurgu.sahne_foto(sh, "savur", 3)
    assert 'window.__timelines["s05"] = tl' in html and "<template>" in html
    assert "blur(18px)" in html  # savur girişi
    assert kurgu.gecis_sec(0, "foto", None) == "kesme"
    assert kurgu.gecis_sec(4, "foto", "kesme") != "kesme"


def test_yapi_onar_gorsel_kapanis_sayi_duragan():
    s = _gecerli_senaryo()
    s["sahneler"][2]["deger"] = "<475"  # sayi
    for i in (3, 5, 7):  # aynı görsel üç kez
        s["sahneler"][i]["gorsel"] = "G2"
    s["sahneler"].insert(10, _sahne("kapanis", "early end", metin="x"))
    yapilan = senaryo.yapi_onar(s, gorsel_sayisi=40)
    assert yapilan
    assert s["sahneler"][2]["deger"] == "475"
    assert sum(1 for sh in s["sahneler"] if sh.get("gorsel") == "G2") <= 2
    assert [sh["tur"] for sh in s["sahneler"]].count("kapanis") == 1
    assert s["sahneler"][-1]["tur"] == "kapanis"
    assert not [h for h in senaryo.yapi_kapisi(s, 40) if "görsel" in h or "kapanis" in h or "sayi.deger" in h]
