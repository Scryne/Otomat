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
    for i in (3, 5, 7, 9):  # aynı görsel dört kez (sınır GORSEL_EN_COK = 3)
        s["sahneler"][i]["gorsel"] = "G2"
    s["sahneler"][12]["gorsel"] = s["sahneler"][13]["gorsel"] = "G5"  # komşu sahnede aynı görsel
    s["sahneler"].insert(10, _sahne("kapanis", "early end", metin="x"))
    yapilan = senaryo.yapi_onar(s, gorsel_sayisi=40)
    assert yapilan
    assert s["sahneler"][2]["deger"] == "475"
    assert sum(1 for sh in s["sahneler"] if sh.get("gorsel") == "G2") <= senaryo.GORSEL_EN_COK
    gl = [sh.get("gorsel") for sh in s["sahneler"]]
    assert all(a != b for a, b in zip(gl, gl[1:], strict=False) if a)  # komşu tekrar yok
    assert all(sh.get("gorsel") for sh in s["sahneler"] if sh["tur"] != "harita")  # her sahnede görsel
    assert [sh["tur"] for sh in s["sahneler"]].count("kapanis") == 1
    assert s["sahneler"][-1]["tur"] == "kapanis"
    assert not [h for h in senaryo.yapi_kapisi(s, 40) if "görsel" in h or "kapanis" in h or "sayi.deger" in h]


def test_zemin_parallax_klip_ve_yedek():
    sh = {"id": "s07", "sure": 5.0, "gorsel": "assets/img/g01.jpg", "derinlik": "assets/derinlik/g01.png"}
    h, js = kurgu.zemin(sh, 3, "karart")
    assert 'class="px"' in h and "assets/derinlik/g01.png" in h  # derinlikli parallax tuvali
    assert "window.PX.ciz" in js and "buildReady['s07-px']" in js
    assert "radial-gradient" in h  # karartma katmanı
    h2, js2 = kurgu.zemin({"id": "s08", "sure": 4.0, "gorsel": "assets/img/g02.jpg"}, 1)
    assert "<img" in h2 and "canvas" not in h2 and "scale" in js2  # derinlik yoksa kamera hareketi
    h3, _ = kurgu.zemin({"id": "s09", "sure": 4.0, "klip": "assets/klip/a.mp4"}, 2)
    assert "<video" in h3 and 'data-duration="4.000"' in h3
    h4, js4 = kurgu.zemin({"id": "s10", "sure": 4.0}, 0)
    assert "leke" in h4 and "tl.fromTo" in js4  # görsel yoksa bile hareketli zemin, düz renk değil


def test_sablonlarda_duz_renk_zemin_yok():
    ortak = {"sure": 6.0, "kelimeler": [], "anlatim": "x", "gorsel": "assets/img/g01.jpg",
             "derinlik": "assets/derinlik/g01.png"}  # fmt: skip
    ornek = {
        "sayi": {"deger": "1800000000", "etiket": "dollars in a day"},
        "alinti": {"metin": "We did it", "kim": "CEO"},
        "zaman": {"olaylar": [{"tarih": "2013", "olay": "a"}, {"tarih": "2020", "olay": "b"}]},
        "ikili": {"sol": {"etiket": "a", "deger": "1"}, "sag": {"etiket": "b", "deger": "2"}},
        "ifade": {"metin": "A big claim"},
        "manset": {"mansetler": [{"kaynak": "BBC", "baslik": "Something happened"}]},
        "bolum": {"no": "01", "baslik": "Act one"},
        "kapanis": {"metin": "Remember this", "kanal": "X"},
    }
    for tur, alan in ornek.items():
        sh = {**ortak, **alan, "id": f"t-{tur}", "tur": tur}
        html = kurgu.SAHNELER[tur](sh, "kesme", 2)
        assert 'class="px"' in html, tur
        assert 'background:#FFD60A; color:#111">' not in html and "background:#F4F2EC; color:#111" not in html, tur
        dh = kesit.DIKEY[tur]({**sh, "id": f"d-{tur}"}, "kesme", 2)
        assert 'class="px"' in dh, f"dikey {tur}"


def test_muzik_bolumleri_ve_zarf():
    import numpy as np

    from otomat.trend import muzik

    sahneler = [{"tur": "foto", "bas": 0.0, "sure": 30.0}, {"tur": "bolum", "bas": 30.0, "sure": 3.0},
                {"tur": "sayi", "bas": 33.0, "sure": 40.0, "kelimeler": [{"w": "$265", "s": 2.0, "e": 2.6}]},
                {"tur": "bolum", "bas": 73.0, "sure": 3.0}, {"tur": "foto", "bas": 76.0, "sure": 60.0},
                {"tur": "foto", "bas": 136.0, "sure": 8.0}, {"tur": "kapanis", "bas": 144.0, "sure": 6.0}]  # fmt: skip
    plan = {"kanca": "merak", "bolumler": ["gerilim", "dram"], "kapanis": "umut"}
    b = muzik.bolumler(sahneler, plan, 150.0)
    assert [x["ruh"] for x in b] == ["merak", "gerilim", "dram", "umut"]  # son iki sahne kapanış parçası
    kisa = sahneler[:-2] + [{"tur": "kapanis", "bas": 136.0, "sure": 6.0}]
    assert muzik.bolumler(kisa, plan, 142.0)[-1]["ruh"] == "dram"  # 6 sn'lik kapanış önceki bölüme katılır
    assert b[0]["bas"] == 0 and b[-1]["son"] == 150.0 and b[1]["bas"] == 30.0
    # zarf: konuşma altında kısık, boşlukta açık
    sr = muzik.SR
    konusma = np.zeros((sr * 4, 2), np.float32)
    konusma[: sr * 2] = 0.3 * np.sin(np.linspace(0, 2000, sr * 2))[:, None]
    k = muzik.zarf(konusma, len(konusma), [])
    assert abs(20 * np.log10(k[int(sr * 1.5)]) - muzik.KONUSMA_DB) < 0.5
    assert abs(20 * np.log10(k[int(sr * 3.8)]) - muzik.BOSLUK_DB) < 1.5


def test_ton_talimati():
    assert zamanla.ton_talimati({"ton": "hushed,  building suspense"}).endswith("hushed, building suspense")
    assert zamanla.ton_talimati({}) == zamanla.TON_TABAN


def test_kesit_kirp_uzun_kosuyu_sinira_ceker():
    sh = [_sahne("bolum", "Chapter two")] + [_sahne("foto", " ".join(["w"] * 25)) for _ in range(10)]
    k = senaryo.kesit_kirp({"sahneler": list(range(0, 11)), "kanca": "x"}, sh)
    assert k["sahneler"][0] == 1  # baştaki bölüm kartı atıldı
    assert senaryo.kesit_gecerli(k, sh) and len(k["sahneler"]) == 5  # 125 kelime
    assert not senaryo.kesit_gecerli({"sahneler": [1, 3], "kanca": "x"}, sh)  # ardışık değil


def test_kisi_uygun_yalniz_adi_gecen_kisi():
    assert senaryo._kisi_uygun("Robert Pattinson", "He was born in Barnes", "Robert Pattinson")  # ana konu
    assert senaryo._kisi_uygun("Pierce Brosnan", "Brosnan shrugged it off", "Robert Pattinson")
    assert not senaryo._kisi_uygun("Pierce Brosnan", "Piers Morgan issued a verdict", "Robert Pattinson")
    assert senaryo._kisi_uygun(None, "anything", "x")  # kişisiz görsel her yere uyar


def test_sayac_sira_sayisi_ve_kucuk_sayi_sayilmaz():
    assert kurgu._sayac_bas(25, "th") == 25 and kurgu._sayac_bas(7, "") == 7
    assert kurgu._sayac_bas(1800, "M") == 0
    html = kurgu.sahne_sayi({"id": "s1", "sure": 4.0, "deger": "25", "son": "th", "etiket": "film", "kelimeler": []},
                            "kesme", 1)  # fmt: skip
    assert "{v:25.0}, {v:25.0" in html


def test_stok_uygun_ai_klip_ve_kisa_klip_elenir():
    from otomat.trend import stok

    iyi = {"tags": "london, street, night", "duration": 12, "videos": {"medium": {"url": "u", "width": 1920}}}
    assert stok.uygun(iyi, 8.0)
    assert not stok.uygun({**iyi, "tags": "ai generated, london"}, 8.0)  # üretilmiş görüntü gerçek gibi gösterilmez
    assert not stok.uygun({**iyi, "duration": 3}, 8.0)
    assert not stok.uygun({**iyi, "videos": {"medium": {"url": "u", "width": 960}}}, 8.0)
    assert stok.gecerli_klip({"klip": {"id": 123, "url": "u"}}) and not stok.gecerli_klip({"klip": "x.mp4"})
