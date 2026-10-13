from otomat.ses import Parca
from otomat.yayin.ceviri import rakamlar
from otomat.yayin.srt import srt


def test_rakamlar_ayractan_bagimsiz():
    assert rakamlar("1,047 quakes, magnitude 7.8") == rakamlar("1.047 sismos, magnitud 7,8")
    assert rakamlar("1 047 séismes") == ["1047"]
    assert rakamlar("on August 14, 2026") == rakamlar("el 14 de agosto de 2026") == ["14", "2026"]
    assert rakamlar("2026-10-02") == ["02", "10", "2026"]
    assert rakamlar("1,047") != rakamlar("1,074")


def test_srt():
    metin = srt([Parca(0.0, 1.5, "Hello world"), Parca(1.5, 61.25, "Second")])
    assert metin.startswith("1\n00:00:00,000 --> 00:00:01,500\nHello world\n")
    assert "2\n00:00:01,500 --> 00:01:01,250\nSecond" in metin
    assert "Hola" in srt([Parca(0, 1, "Hello")], ["Hola"])


def test_hafta_sayfasi_teslim_dosyalarindan(tmp_path, monkeypatch):
    import datetime as dt
    import json

    from otomat import gunluk
    from otomat.yayin import hafta

    monkeypatch.setattr(gunluk, "KOK", tmp_path)
    for gun, baslik in (("2026-10-04", "Second Video"), ("2026-10-02", "First: Video")):
        d = tmp_path / gun
        d.mkdir()
        (d / "video.mp4").write_bytes(b"x")
        meta = {"baslik": baslik, "aciklama": "Line one\n\n#Shorts #Data", "etiketler": ["data", "the world"]}
        (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        gunluk.teslime_koy(d, dt.date.fromisoformat(gun))
    eski = "# 2026-10-03: yayın 2026-10-04 14:00 UTC\n\n**Başlık:** Old\n\n"
    eski += "**Açıklama:**\n\n```\nA\n```\n\n**Etiketler:** \n"
    (tmp_path / "teslim" / "2026-10-03_YUKLE.md").write_text(eski, encoding="utf-8")
    yukleler = [hafta.oku(p.read_text(encoding="utf-8")) for p in sorted((tmp_path / "teslim").glob("*_YUKLE.md"))]
    assert yukleler[0] == {
        "tarih": "2026-10-02",
        "baslik": "First: Video",
        "aciklama": "Line one\n\n#Shorts #Data",
        "etiketler": "data, the world",
    }
    assert yukleler[1]["baslik"] == "Old" and yukleler[1]["etiketler"] == ""
    sayfa = hafta.olustur(list(reversed(yukleler)), "teslim-2026-H40")
    # H40 videoları H41'e günde bir: pazartesi 5 Ekim 14:00 UTC = 17:00 TR
    assert "## 1. `2026-10-02_video.mp4` → Pazartesi 05.10.2026 17:00 (TR)" in sayfa
    assert "## 3. `2026-10-04_video.mp4` → Çarşamba 07.10.2026 17:00 (TR)" in sayfa
    assert "```\nFirst: Video\n```" in sayfa and "```\nLine one\n\n#Shorts #Data\n```" in sayfa
    assert hafta.takvim("teslim-2026-H53", 1)[0].date().isoformat() == "2027-01-04"
    assert hafta.takvim("teslim-uzay-2026-H41", 1) == hafta.takvim("teslim-2026-H41", 1)  # kanal önekli Release


def test_hafta_sayfasi_kitleyi_kanaldan_yazar(monkeypatch):
    """Plan B sayfası Orbit (MFK) için de "Hayır, çocuklara özel değil" diyordu. Orbit 10-13'te genel kitleye geçti:
    MFK kanal profilinden gelir (burada sahte bir MFK kanalıyla)."""
    import dataclasses

    from otomat import kanal
    from otomat.yayin import hafta

    v = [{"tarih": "2026-10-10", "baslik": "B", "aciklama": "A", "etiketler": ""}]
    for mfk, beklenen in ((True, "Evet, çocuklara özel"), (False, "Hayır, çocuklara özel değil")):
        monkeypatch.setattr(kanal, "aktif", lambda m=mfk: dataclasses.replace(kanal.yukle("uzay"), mfk=m))
        sayfa = hafta.olustur(v, "teslim-2026-H41")
        assert beklenen in sayfa and "veri animasyonu" not in sayfa


def test_hazirla_ayni_metnin_cevirisini_yeniden_kullanir(tmp_path, monkeypatch):
    """Hazır üretim yayına ikinci kez geldiğinde çeviriler yeniden yapılıp Cloudflare kotası harcanıyordu."""
    import json

    from otomat.yayin import ceviri, hazirla

    meta = {"baslik": "T", "aciklama": "D", "altyazi": [{"bas": 0.0, "son": 1.0, "metin": "One two three"}]}
    (tmp_path / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    cagri = []

    def cevir(dil, *a, **k):
        cagri.append(dil)
        return None if dil == "de" else {"title": f"T-{dil}", "description": "D", "captions": [f"x-{dil}"]}

    monkeypatch.setattr(ceviri, "cevir", cevir)
    s = hazirla.hazirla(tmp_path)
    assert set(s["yerel"]) == {"es", "pt", "fr"} and s["atlanan"] == ["de"] and not (tmp_path / "de.srt").exists()
    cagri.clear()
    s = hazirla.hazirla(tmp_path)  # aynı metin: yalnız atlanan dil yeniden denenir
    assert cagri == ["de"] * 3 and s["yerel"]["es"]["title"] == "T-es"
    meta["baslik"] = "Başka"
    (tmp_path / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    cagri.clear()
    hazirla.hazirla(tmp_path)  # metin değişti: hepsi yeniden
    assert sorted(set(cagri)) == ["de", "es", "fr", "pt"]
