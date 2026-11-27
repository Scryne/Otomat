"""Trend v4 (11-27, "en iyi haline getir"): Miss Universe videosunun ölçümü (11 görsel, 72 sahne, bir fotoğraf 9 kez,
17 stok klibin ~10'u ilgisiz) üzerine süre bütçesi, görüntüyle stok seçimi, görsel havuzuna göre konu seçimi."""

from pathlib import Path

import pytest
from PIL import Image

from otomat.trend import elestirmen, senaryo, stok, uretim


# ------------------------------------------------------------------------------------------------- süre bütçesi
def test_kelime_hedefi_havuzla_buyur():
    assert senaryo.kelime_hedefi(11) == (550, 825)  # Miss Universe havuzu: ~5,5 dk
    assert senaryo.kelime_hedefi(4)[1] == 700  # taban
    assert senaryo.kelime_hedefi(40)[1] == senaryo.KELIME_HEDEF[1]  # tavan
    alt, ust = senaryo.kelime_hedefi(20)
    assert alt < ust and alt >= 550


def test_iskelet_istemi_butceyi_tasir():
    kisa = senaryo.iskelet_sistemi(825)
    assert "~425-625 words" in kisa and "(3-4 chapters;" in kisa
    uzun = senaryo.iskelet_sistemi(1350)
    assert "(3-5 chapters;" in uzun and "~950-1150 words" in uzun  # tam bütçe eski aralığın aynısı
    assert "~750-950 words" in senaryo.iskelet_sistemi(1150)


def test_bolum_kelimeleri_orantili_kuculur():
    plan = {"bolumler": [{"kelime": 300}, {"kelime": 300}, {"kelime": 400}]}
    senaryo.bolum_kelimeleri(plan, 825)
    toplam = sum(b["kelime"] for b in plan["bolumler"])
    assert toplam <= 825 - senaryo.KANCA_KAPANIS - 30 + 2
    plan2 = {"bolumler": [{"kelime": 200}]}
    senaryo.bolum_kelimeleri(plan2, 1350)  # bütçe içindeyse dokunmaz
    assert plan2["bolumler"][0]["kelime"] == 200


def test_yapi_kapisi_kelimeyi_havuza_gore_olcer():
    sahne = [{"tur": "foto", "anlatim": " ".join(["word"] * 30), "gorsel": f"G{i % 5 + 1}"} for i in range(40)]
    sahne[-1] = {"tur": "kapanis", "anlatim": "bye now"}
    s = {"tez": "t", "sahneler": sahne}
    assert any("toplam anlatım" in h for h in senaryo.yapi_kapisi(s, 5))  # 1170 kelime, 5 görsel: bütçe 700
    assert not any("toplam anlatım" in h for h in senaryo.yapi_kapisi(s, 30))


def test_gorsel_dorduncu_kez_kullanilmaz():
    s = {"sahneler": [{"tur": "foto", "anlatim": "a", "gorsel": "G1" if i % 2 == 0 else "G2"} for i in range(12)]}
    senaryo.yapi_onar(s, 2)
    say = senaryo._gorsel_say(s["sahneler"])
    assert say["G1"] <= senaryo.GORSEL_EN_COK and say["G2"] <= senaryo.GORSEL_EN_COK
    assert any(not sh.get("gorsel") for sh in s["sahneler"])  # fazlası görselsiz: stok doldurur
    assert any("kez kullanılmış" not in h for h in senaryo.yapi_kapisi(s, 2))


# ------------------------------------------------------------------------------------------------- stok seçimi
def test_kisili_satir_zamirle():
    assert stok.kisili("In 2025 she decided to prepare for the pageant.")
    assert stok.kisili("His agent refused.")
    assert not stok.kisili("The tourism company would handle the event.")
    assert not stok.kisili("The theme of the show.")  # "the" ≠ "he"


def test_pixabay_kendi_isaretleri_ve_1080p():
    hit = {
        "tags": "city, night",
        "duration": 12,
        "videos": {"medium": {"url": "m", "width": 1280}, "large": {"url": "l", "width": 1920, "size": 30_000_000}},
    }
    assert stok.uygun(hit, 6)
    assert not stok.uygun({**hit, "isAiGenerated": True}, 6)
    assert not stok.uygun({**hit, "isLowQuality": True}, 6)
    assert stok.kaynak_url(hit) == "l"
    assert stok.kaynak_url({**hit, "videos": {**hit["videos"], "large": {"url": "", "width": 0}}}) == "m"
    dev = {**hit, "videos": {**hit["videos"], "large": {"url": "l", "width": 3840, "size": 500_000_000}}}
    assert stok.kaynak_url(dev) == "m"


def _hit(i: int, tags: str = "city") -> dict:
    return {
        "id": i,
        "tags": tags,
        "duration": 20,
        "videos": {"medium": {"url": f"u{i}", "width": 1920, "thumbnail": ""}},
    }


def test_aday_sayfasi_sahne_basina_satir(monkeypatch, tmp_path):
    kucuk = tmp_path / "k.jpg"
    Image.new("RGB", (640, 360), (200, 50, 50)).save(kucuk)
    monkeypatch.setattr(stok, "_kucuk_resim", lambda h: kucuk)
    adaylar = {3: [_hit(1), _hit(2)], 7: [_hit(3)], 9: [], 12: [_hit(4)], 15: [_hit(5)], 20: [_hit(6)]}
    sayfalar = stok.aday_sayfalari(adaylar)
    assert [g for _, g in sayfalar] == [[3, 7, 12, 15], [20]]  # boş sahne sayfaya girmez
    im = Image.open(__import__("io").BytesIO(sayfalar[0][0]))
    assert im.size == (stok.HUCRE[0] * stok.ADAY_EN_COK, stok.HUCRE[1] * 4)


def test_goruntuyle_sec_etiketi_cozer_ve_kisiyi_isaretler(monkeypatch):
    sahneler = (
        [{"anlatim": "x"}] * 3 + [{"anlatim": "She trained for months."}] + [{"anlatim": "The arena filled."}] * 4
    )
    adaylar = {3: [_hit(1), _hit(2)], 7: [_hit(3)]}
    monkeypatch.setattr(stok, "aday_sayfalari", lambda a: [(b"jpg", [3, 7])])
    gorulen = {}

    def sahte(oturum, sistem, sayfalar, metin, en_cok=0):
        gorulen["metin"] = metin
        return {"secim": [{"i": 3, "id": "3b"}, {"i": 7, "id": "7z"}, {"i": 5, "id": "5a"}]}

    import otomat.trend.gorsel_secici as gs

    monkeypatch.setattr(gs, "goruntu_sor", sahte)
    out = stok.goruntuyle_sec(None, sahneler, adaylar, "hikaye")
    assert out == {3: adaylar[3][1]}  # 7z yok, 5 sayfada değil
    assert "SCENE 3 [ABOUT A SPECIFIC PERSON" in gorulen["metin"] and "SCENE 7:" in gorulen["metin"]


def test_aday_sec_ayni_klibi_iki_sahneye_vermez(monkeypatch):
    h = _hit(1)
    monkeypatch.setattr(stok, "adaylari_topla", lambda s, z: {2: [h], 6: [h]})
    monkeypatch.setattr(stok, "goruntuyle_sec", lambda o, s, a, k="": {2: h, 6: h})
    assert list(stok.aday_sec(None, [{}] * 8, [], {})) == [2]


def test_broll_iki_sorgu(monkeypatch):
    class Sahte:
        def json_sor(self, *a, **k):
            return {"secimler": [{"i": 1, "sorgular": ["stage lights", "concert crowd"]}, {"i": 4, "sorgu": "city"}]}

    sahneler = [{"tur": "foto", "anlatim": "a", "gorsel": "G1"} for _ in range(8)]
    out = stok.broll_sec(Sahte(), sahneler)
    assert out[0]["sorgular"] == ["stage lights", "concert crowd"] and out[0]["sorgu"] == "stage lights"
    assert out[1]["sorgular"] == ["city"]  # eski biçim de okunur


# ------------------------------------------------------------------------------------------------- kurgu ve eleştiri
def test_gorselsiz_sahne_en_az_kullanilan_fotografi_alir():
    onceki = [{"gorsel": "assets/img/g01.jpg"}, {"gorsel": "assets/img/g01.jpg"}, {"gorsel": "assets/img/g02.jpg"}]
    sonraki = [{"gorsel": "G3"}, {"gorsel": "G1"}]
    assert uretim._en_az_gorsel(onceki, sonraki, 4) == 3  # g4 hiç yok; g2 önceki, G3 sonraki sahnede
    assert uretim._en_az_gorsel([], [], 0) == -1


def test_elestirmen_ilgisiz_klibi_cikarir():
    plan = {
        "sahneler": [
            {"id": "s01", "tur": "foto", "klip": "assets/klip/a.mp4", "gorsel": "assets/img/g01.jpg"},
            {"id": "s02", "tur": "foto", "klip": "assets/klip/b.mp4"},
        ]
    }
    b = [
        {"sahne": "s01", "tur": "anlamsiz_gorsel", "siddet": "P1"},
        {"sahne": "s02", "tur": "anlamsiz_gorsel", "siddet": "P1"},
    ]
    yapilan = elestirmen.duzelt(plan, b)
    assert "klip" not in plan["sahneler"][0] and plan["sahneler"][1]["klip"]  # fotoğrafı olmayan klip kalır
    assert len(yapilan) == 1


# ------------------------------------------------------------------------------------------------- konu seçimi
def _kaynak_sahte(havuzlar: dict[str, int]):
    def kaynak(d: Path, secim: dict) -> dict:
        n = havuzlar[secim["secim"]["wiki_baslik"]]
        kay = {
            "wiki": {"metin": "m"},
            "haberler": [],
            "gorseller": [{"i": i} for i in range(n)],
            "suzuldu": True,
            "suzgec_kalan": n,
        }
        uretim._yaz(d / "kaynak.json", kay)
        return kay

    return kaynak


def _secim(*basliklar: str) -> dict:
    ss = [{"hikaye": b, "wiki_baslik": b} for b in basliklar]
    return {"secim": ss[0], "yedekler": ss[1:]}


def test_konu_gorsel_havuzu_yetmezse_yedege_gecer(monkeypatch, tmp_path):
    monkeypatch.setattr(uretim, "asama_kaynak", _kaynak_sahte({"A": 7, "B": 14, "C": 30}))
    secim, kay = uretim.konu_kaynak(tmp_path, None, _secim("A", "B", "C"))
    assert secim["secim"]["wiki_baslik"] == "B" and secim["gorsel_onay"] and len(kay["gorseller"]) == 14
    assert (tmp_path / "kaynak_red_0.json").exists()
    assert uretim._oku(tmp_path / "secim.json")["secim"]["wiki_baslik"] == "B"
    # ikinci koşu onaylı seçimi yeniden ölçmez
    monkeypatch.setattr(uretim, "asama_kaynak", lambda d, s: uretim._oku(d / "kaynak.json"))
    secim2, _ = uretim.konu_kaynak(tmp_path, None, uretim._oku(tmp_path / "secim.json"))
    assert secim2["secim"]["wiki_baslik"] == "B"


def test_konu_esik_yoksa_en_zengin_ya_da_hata(monkeypatch, tmp_path):
    monkeypatch.setattr(uretim, "asama_kaynak", _kaynak_sahte({"A": 8, "B": 9, "C": 3}))
    secim, kay = uretim.konu_kaynak(tmp_path, None, _secim("A", "B", "C"))
    assert secim["secim"]["wiki_baslik"] == "B" and len(kay["gorseller"]) == 9
    d2 = tmp_path / "iki"
    d2.mkdir()
    monkeypatch.setattr(uretim, "asama_kaynak", _kaynak_sahte({"A": 5, "B": 7}))
    with pytest.raises(RuntimeError, match="görsel havuzu yetmedi"):
        uretim.konu_kaynak(d2, None, _secim("A", "B"))


def test_karsitlik_kalibi_ve_kivrik_kesme():
    def hata(anlatim: str) -> list[str]:
        s = {"tez": "t", "sahneler": [{"tur": "foto", "anlatim": anlatim, "gorsel": "G1"}]}
        return [h for h in senaryo.yapi_kapisi(s, 30) if "kalıbı" in h or "yasak ifade" in h]

    assert hata("So the real question isn't whether a mom can win, it's whether the pageant deserves her.")
    assert hata("It wasn't about the money, it was about control.")
    assert hata("They quit not because of the fee but because of the president.")
    assert hata("Here’s the thing about the crown.")  # kıvrık kesme işareti
    assert not hata("The tourism company wasn't paid until April, and the show nearly moved.")
    assert not hata("She didn't come up through the pageant world at all.")


def test_ritim_kapisi_baglac_zinciri():
    def sh(a: str) -> dict:
        return {"tur": "foto", "anlatim": a}

    zincir = [sh("So the money moved."), sh("And then it stopped."), sh("The governor signed it.")] * 4
    h = senaryo.ritim_kapisi(zincir)
    assert any("art arda" in x for x in h)
    temiz = [sh("The governor signed it."), sh("So the money moved."), sh("Payments resumed in April.")] * 3
    assert not [x for x in senaryo.ritim_kapisi(temiz) if "art arda" in x]
    because = [sh(f"It moved because of reason {i}, with more words here to pad the line out.") for i in range(8)]
    assert sum("'because'" in x for x in senaryo.ritim_kapisi(because)) == 5  # 8 kullanım, hak 3


def test_slogan_kapanis_yakalanir():
    def hata(a: str) -> bool:
        s = {"tez": "t", "sahneler": [{"tur": "foto", "anlatim": a, "gorsel": "G1"}]}
        return any("kalıbı" in h for h in senaryo.yapi_kapisi(s, 30))

    assert hata("A mom took the crown while fights shadowed the stage, and that gap is the story.")
    assert hata("The timing wasn't random, because the last edition had problems.")
    assert hata("And the winner's story isn't the only one worth telling.")
    assert not hata("The story spread across Manila within a day.")


def test_bastaki_so_and_atilir():
    assert senaryo._baglac_at("So the money moved.") == "The money moved."
    assert senaryo._baglac_at("And, by April, it flowed.") == "By April, it flowed."
    assert senaryo._baglac_at("Sony said no.") == "Sony said no."
    assert senaryo._baglac_at("Andorra hosted it.") == "Andorra hosted it."
    assert senaryo._baglac_at("But it stopped.") == "But it stopped."
    s = {
        "sahneler": [
            {"tur": "foto", "anlatim": a, "gorsel": f"G{i + 1}"}
            for i, a in enumerate(["So it began.", "And it grew.", "Then it fell.", "It ended."])
        ]
    }
    senaryo.yapi_onar(s, 4)
    assert s["sahneler"][1]["anlatim"] == "It grew."


def test_kesit_ilk_sahne_kanca_panelinin_altindan_baslar(tmp_path):
    from otomat.trend import kesit

    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF")
    kel = [{"w": "Hello", "s": 0.1, "e": 0.5}]
    plan = {"sahneler": [{"id": "s01", "tur": "foto", "bas": 0.0, "sure": 4.0, "anlatim": "Hello", "kelimeler": kel},
                         {"id": "s02", "tur": "foto", "bas": 4.0, "sure": 4.0, "anlatim": "Hi", "kelimeler": kel}],
            "sure": 8.0}  # fmt: skip
    d = kesit.proje_yaz(plan, {"sahneler": [0, 1], "kanca": "A HOOK"}, tmp_path / "p", {"assets/ses/anlatim.wav": wav},
                        {})  # fmt: skip
    html = (d / "index.html").read_text(encoding="utf-8")
    assert f"fromTo('#k01', {{y:{kesit.KANCA_KAYMA}}}" in html
    assert 0 < kesit.KANCA_KAYMA < kesit.KANCA_PANEL


def test_yukle_son_bayat_ve_isaretli_isi_almaz(tmp_path):
    import datetime as dt
    import os

    from otomat.trend import yukle

    simdi = dt.datetime(2026, 11, 28, 9, tzinfo=dt.UTC)
    for ad, saat, isaret, yuklu in [("a-taze", 5, False, False), ("b-bayat", 80, False, False),
                                    ("c-deneme", 2, True, False), ("d-bayat-yuklu", 90, False, True)]:  # fmt: skip
        d = tmp_path / ad
        d.mkdir()
        (d / "video.mp4").write_bytes(b"x")
        t = (simdi - dt.timedelta(hours=saat)).timestamp()
        os.utime(d / "video.mp4", (t, t))
        if isaret:
            (d / "yuklenmez").write_text("x")
        if yuklu:
            (d / "yukleme.json").write_text("{}")
    assert [d.name for d in yukle.yuklenebilir(tmp_path, simdi)] == ["a-taze", "d-bayat-yuklu"]


def test_grup_siniri_uyumu_dusuk_olani_bosaltir():
    s = {"sahneler": [{"tur": "foto", "anlatim": "a", "gorsel": g, "gorsel_uyum": u}
                      for g, u in [("G1", 2), ("G2", 2), ("G1", 0), ("G3", 1), ("G2", 1), ("G3", 2), ("G4", 2),
                                   ("G1", 1), ("G5", 2)]]}  # fmt: skip
    gruplar = {"G1": "k1", "G2": "k1", "G3": "k1"}  # G4, G5 tekil
    yapilan = senaryo.grup_siniri(s, gruplar)
    kalan = [sh.get("gorsel") for sh in s["sahneler"]]
    grupta = [g for g in kalan if g in gruplar]
    assert len(grupta) == senaryo.GRUP_KULLANIM and len(yapilan) == 3
    assert kalan[2] is None  # G1'in uyumu 0 olan kullanımı ilk düşer
    assert kalan[6] == "G4" and kalan[8] == "G5"  # tekiller dokunulmaz


def test_etkin_gorsel_grubu_bir_bucuk_sayar():
    g = [{"grup": "k1"}] * 4 + [{"grup": "k2"}] * 2 + [{}] * 5
    assert uretim.etkin_gorsel(g) == 8  # 5 tekil + 2 grup × 1,5


def test_elestirmen_anlatimi_gorur(monkeypatch, tmp_path):
    plan = {"sahneler": [{"bas": 0.0, "sure": 4.2, "anlatim": "She worked for the U.S. Army."},
                         {"bas": 4.2, "sure": 3.0, "anlatim": "The show went on."}]}  # fmt: skip
    liste = elestirmen.sahne_listesi(plan)
    assert liste.splitlines() == ["0.0-4.2s: She worked for the U.S. Army.", "4.2-7.2s: The show went on."]
    sayfa = tmp_path / "s.jpg"
    Image.new("RGB", (64, 36)).save(sayfa)
    giden = {}

    class Sahte:
        def _istek(self, govde):
            giden["metin"] = govde["messages"][0]["content"][1]["text"]
            return {"content": [{"type": "text", "text": '{"bulgular": []}'}]}

    elestirmen.incele([sayfa], "tez", Sahte(), liste)
    assert "SCENES (time: narration):\n0.0-4.2s: She worked" in giden["metin"]


def test_gorsel_nesne_is_alanlarini_atar():
    g = uretim._gorsel_nesne({"dosya": "File:a.jpg", "url": "u", "genislik": 10, "yukseklik": 10, "mime": "image/jpeg",
                              "lisans": "CC0", "yazar": "", "kredi_satiri": "", "sayfa": "", "yerel": "x",
                              "hazir": "y", "grup": "k1"})  # fmt: skip
    assert g.dosya == "File:a.jpg"


# ------------------------------------------------------------------- 11-27 Wu-Tang: görsel süzgeci ve yedek fotoğraf
def test_suzgec_hikayesi_adlari_tasir():
    h = uretim.suzgec_hikayesi({"hikaye": "Wu-Tang Clan's NFL halftime", "aci": "a rock drummer felt normal",
                                "wiki_baslik": "Wu-Tang_Clan", "ilgili": ["Chad_Smith"],
                                "gorsel_aramalari": ["Chad Smith drummer"]})  # fmt: skip
    assert "Chad Smith" in h and "rock drummer" in h and "Named in this story" in h


_HAVUZ = [{"dosya": "File:RZA @ Virgin festival 2007.jpg", "hazir": "a", "kredi_satiri": "k"},
          {"dosya": "File:Washington Football Team vs. Detroit Lions at Ford Field.jpg", "hazir": "b",
           "kredi_satiri": "k"},
          {"dosya": "File:Chad Smith-Rio De Janeiro-2011.jpg", "hazir": "c", "kredi_satiri": "k"}]  # fmt: skip


def test_ilgili_gorsel_adla_secer_kullanim_ve_komsuyu_sayar():
    assert uretim.ilgili_gorsel("RZA started building something bigger", _HAVUZ, {}, set()) == 0
    assert uretim.ilgili_gorsel("Smith started drums at seven", _HAVUZ, {}, set()) == 2
    assert uretim.ilgili_gorsel("Smith started drums", _HAVUZ, {2: uretim.ILGILI_EN_COK}, set()) == -1
    assert uretim.ilgili_gorsel("Smith started drums", _HAVUZ, {}, {2}) == -1
    assert uretim.ilgili_gorsel("the record deals of the 1990s", _HAVUZ, {}, set()) == -1


def test_etiket_yalniz_kendi_fotografinda():
    assert uretim.etiket_uygun("RZA", _HAVUZ[0]["dosya"])
    assert not uretim.etiket_uygun("RZA", _HAVUZ[1]["dosya"])
    assert uretim.etiket_uygun("the stadium", _HAVUZ[1]["dosya"])  # özel ad yoksa serbest


def test_gorsel_onar_p0_anlamsiz_fotografi_degistirir():
    plan = {"sahneler": [
        {"id": "s01", "tur": "foto", "gorsel": "assets/img/g02.jpg", "anlatim": "The NFL booked them."},
        {"id": "s02", "tur": "foto", "gorsel": "assets/img/g02.jpg", "anlatim": "Chad Smith learned drums at seven.",
         "etiket": "Ford Field", "derinlik": "x"},
        {"id": "s03", "tur": "foto", "klip": "assets/klip/a.mp4", "gorsel": "assets/img/g02.jpg",
         "anlatim": "RZA said it."}]}  # fmt: skip
    bulgu = [{"tur": "anlamsiz_gorsel", "siddet": "P0", "sahne": "s02"},
             {"tur": "anlamsiz_gorsel", "siddet": "P0", "sahne": "s03"},
             {"tur": "anlamsiz_gorsel", "siddet": "P1", "sahne": "s01"}]  # fmt: skip
    varlik: dict = {}
    yapilan = uretim.gorsel_onar(plan, bulgu, _HAVUZ, varlik)
    s = plan["sahneler"]
    assert s[1]["gorsel"] == "assets/img/g03.jpg" and "etiket" not in s[1] and "derinlik" not in s[1]
    assert s[2]["gorsel"] == "assets/img/g02.jpg"  # stok klipli sahne eleştirmen.duzelt'in işi
    assert s[0]["gorsel"] == "assets/img/g02.jpg"  # P1 dokunulmaz
    assert len(yapilan) == 1 and "assets/img/g03.jpg" in varlik


def test_uzun_sahnede_iki_kesme_farkli_olcek():
    from otomat.trend import kurgu

    kel = [{"w": "x", "s": t, "e": t + 0.2} for t in (0.2, 3.1, 4.4, 6.2, 8.6, 10.5)]
    sh = {"id": "s05", "sure": 12.0, "gorsel": "assets/img/g01.jpg", "kelimeler": kel}
    assert kurgu.vurus_anlari(sh) == [4.4, 8.6]  # 4,0 ve 8,0'a en yakın kelime başları
    _, js = kurgu.zemin(sh, 1)
    assert "scale:1.16" in js and "scale:1.07" in js
    assert len(kurgu.vurus_anlari({**sh, "sure": 6.0})) == 1
    assert kurgu.vurus_anlari({**sh, "sure": 4.0}) == []


class _KancaOturum:
    def __init__(self, adaylar, puanlar):
        self.cevap = [{"adaylar": adaylar}, {"puanlar": puanlar}]

    def json_sor(self, *a, **k):
        return self.cevap.pop(0)


def test_kanca_sec_en_yuksek_puanli_aday_gecer():
    ilk = {"tur": "foto", "anlatim": "On Thanksgiving the Lions hosted the Bears at Ford.", "kaynak": ["N8"]}
    s = {"tez": "t", "sahneler": [ilk, {"tur": "foto", "anlatim": "They opened with Triumph."}]}
    ad = [{"metin": "Wu-Tang opened an NFL halftime show with a five-minute song that has nine verses and no hook.",
           "kaynak": ["N18"]},
          {"metin": "This isn't about football, it's about money and who gets the stage tonight.", "kaynak": []},
          {"metin": "kısa", "kaynak": []}]  # fmt: skip
    o = _KancaOturum(ad, [{"i": 0, "toplam": 30}, {"i": 1, "toplam": 46}])
    yeni = senaryo.kanca_sec(o, s, "kaynak")
    assert yeni and yeni.startswith("Wu-Tang") and s["sahneler"][0]["kaynak"] == ["N18", "N8"]
    assert len(s["kanca_adaylari"]) == 2  # yasak kalıp ("isn't about…, it's") ve kısa aday elendi


def test_kanca_sec_esitlikte_yazarinki_kalir():
    s = {"sahneler": [{"tur": "foto", "anlatim": "On Thanksgiving the Lions hosted the Bears at Ford Field."}]}
    ad = [{"metin": "Wu-Tang opened an NFL halftime show with a five-minute song with nine verses.", "kaynak": []}]
    o = _KancaOturum(ad, [{"i": 0, "toplam": 40}, {"i": 1, "toplam": 40}])
    assert senaryo.kanca_sec(o, s, "k") is None and s["sahneler"][0]["anlatim"].startswith("On Thanksgiving")


# ------------------------------------------------------------------- altyazı ve çeviri (11-27 ders: çok dilli meta)
def test_altyazi_senaryonun_yazimini_ve_zamanini_kullanir():
    from otomat.trend import yerel

    sah = [{"anlatim": "RZA met Ghostface Killah. They built Wu-Tang Clan from the Stapleton Houses, slowly."}]
    kel = [{"w": w.strip(".,").lower(), "s": i * 0.4, "e": i * 0.4 + 0.3}
           for i, w in enumerate(sah[0]["anlatim"].split())]  # fmt: skip
    ip = yerel.ipuclari(sah, {"sahneler": [{"bas": 10.0, "kelimeler": kel}]})
    assert ip[0][2] == "RZA met Ghostface Killah." and ip[0][0] == 10.0  # sahne başı + kelime zamanı
    assert all(len(sat) <= yerel.SATIR for _, _, m in ip for sat in m.split("\n"))
    s = yerel.srt(ip)
    assert s.startswith("1\n00:00:10,000 --> ") and "\n2\n" in s


def test_yerellestir_rakami_bozan_ve_cevrilmeyen_dili_atar():
    from otomat.trend import yerel

    class Cevirmen:
        def json_sor(self, *a, **k):
            return {"es": {"title": "Wu-Tang en 1993", "description": "Capítulos\n0:00 Inicio"},
                    "de": {"title": "Wu-Tang 1994", "description": "Kapitel\n0:00 Anfang"},
                    "fr": {"title": "Wu-Tang in 1993", "description": "Chapitres\n0:00 Début"}}  # fmt: skip

    c = yerel.yerellestir(
        Cevirmen(), "Wu-Tang in 1993", "Chapters\n0:00 Start\n\nSources:\n- x", {"es": "", "de": "", "fr": ""}
    )
    assert set(c) == {"es"} and c["es"]["description"].endswith("\n\nSources:\n- x")


def test_ek_parcalar_hatada_yuklemeyi_dusurmez(tmp_path, monkeypatch):
    from otomat.trend import yukle
    from otomat.yayin import youtube

    (tmp_path / "yerel.json").write_text('{"es": {"title": "t", "description": "d"}}', encoding="utf-8")
    (tmp_path / "altyazi_en.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nx\n", encoding="utf-8")
    cagri = []
    monkeypatch.setattr(youtube, "yerellestir", lambda v, c, yt=None: cagri.append(("yerel", v, set(c))))

    def kota(*a, **k):
        raise RuntimeError("quota")

    monkeypatch.setattr(youtube, "altyazi_ekle", kota)
    kayit = {"video_id": "V1"}
    yukle.ek_parcalar(None, tmp_path, kayit)
    assert kayit["yerel"] == "tamam" and kayit["altyazi"] != "tamam" and cagri == [("yerel", "V1", {"es"})]
    monkeypatch.setattr(youtube, "altyazi_ekle", lambda v, dil, m, yt=None: cagri.append(("srt", v, dil)))
    yukle.ek_parcalar(None, tmp_path, kayit)
    assert kayit["altyazi"] == "tamam" and cagri[-1] == ("srt", "V1", "en") and len(cagri) == 2


def test_sayi_kapisi_tirnaga_yapisik_rakami_sayar():
    from otomat.film import anlatim

    metin = "The phrase 'more demonic than GTA 6' shows how extreme it got."
    assert anlatim.sayilar(metin) == ["6"]
    assert anlatim.fark(metin, "The phrase more demonic than GTA 6 shows how extreme it got.") < 0.1
    assert anlatim.kelimeler("They didn't stop.")[1] == "didn't"  # iç kesme işareti kalır


def test_yasak_kalip_ters_cevirme_ve_butun_hikaye():
    for m in ("It's the other way round.", "He's the whole story in one seat.", "it was actually the other way around"):
        assert any(r.search(m.lower()) for r in senaryo.YASAK_KALIP), m
    assert not any(r.search("they drove the other way round the block.") for r in senaryo.YASAK_KALIP)
