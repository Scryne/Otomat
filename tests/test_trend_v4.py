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
