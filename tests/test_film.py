"""Film hattının saf parçaları: senaryo denetimi, anlatım parçalama/denetimi, zaman çizelgesi, kamera, müzik."""

import json
from pathlib import Path

import pytest

from otomat.film import anlatim, kurgu, senaryo
from otomat.film.anlatim import Zaman
from otomat.film.uretim import aciklama, muzik_plani

PILOT = Path(__file__).parents[1] / "filmler" / "violet-jessop" / "senaryo.json"


def _ham(**degis) -> dict:
    d = {
        "slug": "x", "baslik": "B", "kapak_yazi": "K.", "kapak_sahne": "s", "stil": "st", "insan": "in",
        "karakterler": {"a": "bir kişi"},
        "bolumler": [{"ad": "Bir", "mood": "tragic", "bloklar": [
            {"anlatim": "Bir cümle.", "sahneler": [{"tarif": "The man from the reference image.", "kim": ["a"]}]}]}],
    }  # fmt: skip
    d.update(degis)
    return d


def _yaz(tmp_path: Path, d: dict) -> Path:
    yol = tmp_path / "s.json"
    yol.write_text(json.dumps(d), encoding="utf-8")
    return yol


def test_pilot_senaryosu_gecerli():
    f = senaryo.oku(PILOT)
    assert f.kelime() > 900 and len(f.sahneler()) > 60
    assert all(len(anlatim.parcala(b.anlatim)) >= 1 for _, b in f.bloklar())


@pytest.mark.parametrize(
    ("sahne", "hata"),
    [
        ({"tarif": "x", "hareket": "zipla"}, "bilinmeyen hareket"),
        ({"tarif": "The man from the reference image.", "kim": ["yok"]}, "tanımsız karakter"),
        ({"tarif": "x", "hareket": "i2v"}, "hareket istemi"),
        ({"tarif": "A man walks.", "kim": ["a"]}, "reference image"),
    ],
)
def test_kusurlu_sahne_duser(tmp_path, sahne, hata):
    d = _ham()
    d["bolumler"][0]["bloklar"][0]["sahneler"] = [sahne]
    with pytest.raises(senaryo.SenaryoHatasi, match=hata):
        senaryo.oku(_yaz(tmp_path, d))


def test_bos_anlatim_ve_bilinmeyen_mood_duser(tmp_path):
    d = _ham()
    d["bolumler"][0]["bloklar"][0]["anlatim"] = "  "
    with pytest.raises(senaryo.SenaryoHatasi, match="anlatım boş"):
        senaryo.oku(_yaz(tmp_path, d))
    d = _ham()
    d["bolumler"][0]["mood"] = "neşeli"
    with pytest.raises(senaryo.SenaryoHatasi, match="mood"):
        senaryo.oku(_yaz(tmp_path, d))


def test_parcala_cumle_sinirinda_ve_sinirda():
    metin = "Bir iki üç. Dört beş altı yedi. Sekiz."
    assert anlatim.parcala(metin, sinir=5) == ["Bir iki üç.", "Dört beş altı yedi. Sekiz."]
    uzun = " ".join(["kelime"] * 40) + "."
    assert anlatim.parcala(uzun, sinir=10) == [uzun]  # tek cümle bölünmez


def test_fark_ve_soylenis():
    assert anlatim.fark("Born near Bahía Blanca, in 1887.", "born near bahia blanca in 1887") == 0
    assert anlatim.fark("She jumped into the sea.", "She jumped.") > anlatim.HATA_ESIGI
    assert anlatim.soylenis("Bahía — 1916") == "Bahia, 1916"


def test_cekimler_bitisik_kartli_ve_kuyruklu():
    zaman = [Zaman(0, 4), Zaman(4.5, 9), Zaman(10.4, 14)]
    sahneler = [[("iceri", Path("a"), "")], [("sol", Path("b"), ""), ("sag", Path("c"), "")], [("i2v", Path("d"), "")]]
    c = kurgu.cekimler([0, 0, 1], zaman, sahneler, ["Bir", "İki"])
    assert [x.tur for x in c] == ["iceri", "sol", "sag", "kart", "i2v"]
    assert c[0].son == 4.5  # blok arası boşluk önceki çekime
    assert (c[3].bas, c[3].son, c[3].kart) == (9, 10.4, "İki")
    assert c[-1].son == 14 + kurgu.KUYRUK
    assert all(a.son == pytest.approx(b.bas) for a, b in zip(c, c[1:], strict=False))


@pytest.mark.parametrize("tur", ["iceri", "disari", "sol", "sag", "yukari", "i2v"])
def test_kamera_kaynak_disina_tasmaz(tur):
    for t in (0, 0.3, 0.7, 1):
        olcek, cx, cy = kurgu.kamera(tur, t)
        assert olcek >= 1
        yarim = 0.5 / olcek
        assert yarim - 1e-9 <= cx <= 1 - yarim + 1e-9 and yarim - 1e-9 <= cy <= 1 - yarim + 1e-9


def test_muzik_plani_art_arda_ayni_parca_yok():
    f = senaryo.oku(PILOT)
    plan = muzik_plani(f)
    assert len(plan) == len(f.bolumler)
    assert all(a != b for a, b in zip(plan, plan[1:], strict=False))


def test_aciklama_bolumleri_youtube_kuralina_uyar():
    f = senaryo.oku(PILOT)
    bas = [0.0] + [30.0 * i for i in range(1, len(f.bolumler))]
    metin = aciklama(f, bas, muzik_plani(f))
    satirlar = [s for s in metin.splitlines() if s[:2].isdigit() and s[2] == ":"]
    assert satirlar[0].startswith("00:00") and len(satirlar) >= 3
    assert "wikipedia.org/wiki/Violet_Jessop" in metin and "Creative Commons" in metin


def test_insansiz_sahneye_karakter_tasarimi_gitmez(tmp_path):
    d = _ham()
    d["bolumler"][0]["bloklar"][0]["sahneler"] += [
        {"tarif": "A lonely lighthouse."},
        {"tarif": "A crowd on a pier.", "kisi": True},
    ]
    f = senaryo.oku(_yaz(tmp_path, d))
    referansli, deniz_feneri, kalabalik = f.sahneler()
    assert "in." in senaryo.sahne_istemi(f, referansli) and "in." in senaryo.sahne_istemi(f, kalabalik)
    istem = senaryo.sahne_istemi(f, deniz_feneri)
    assert "in." not in istem and "no people" in istem and senaryo.YUZSUZ in istem
