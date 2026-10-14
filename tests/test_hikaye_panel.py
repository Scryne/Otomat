"""Panelli sahne denetimi (2026-10-14): Ganesha (10-16) ve Mónica Macías (10-13, yayında) videolarında kare ara
boşluklu panellere bölünmüştü; istemdeki "no panels" tutmuyordu, hiçbir kapı bakmıyordu."""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from otomat.hikaye import cf, panel, senaryo, uretim

G, Y = 768, 1344


def _doku(h: int, w: int, tohum: int) -> np.ndarray:
    """Resim gibi dokulu alan: 12 px'lik rastgele bloklar (satırları düz değil)."""
    rng = np.random.default_rng(tohum)
    a = rng.integers(40, 200, size=(h // 12 + 1, w // 12 + 1, 3), dtype=np.uint8)
    return np.array(Image.fromarray(a).resize(((w // 12 + 1) * 12, (h // 12 + 1) * 12), Image.NEAREST))[:h, :w]


def _kaydet(a: np.ndarray, yol):
    Image.fromarray(a.astype(np.uint8)).save(yol, quality=92)
    return yol


def test_yatay_ara_bosluklu_iki_panel_yakalanir(tmp_path):
    a = _doku(Y, G, 1)
    a[700:724] = 236  # krem ara boşluk, iki yanında resim (Molasses 10-08 düzeni)
    assert panel.panelli(_kaydet(a, tmp_path / "k.jpg"))


def test_dikey_ara_bosluk_da_yakalanir(tmp_path):
    a = _doku(Y, G, 2)
    a[:, 380:392] = 230
    assert panel.panelli(_kaydet(a, tmp_path / "k.jpg"))


def test_panelsiz_kare_gokyuzu_ve_kenar_bandi_panel_sayilmaz(tmp_path):
    a = _doku(Y, G, 3)
    assert not panel.panelli(_kaydet(a, tmp_path / "duz.jpg"))
    gok = a.copy()
    gok[: int(Y * 0.45)] = 225  # kalın düz gökyüzü: bir yanı da düz, ara boşluk değil
    assert not panel.panelli(_kaydet(gok, tmp_path / "gok.jpg"))
    kenar = a.copy()
    kenar[40:60] = 235  # dış kenara yakın bant (kâğıt çerçevesi kalıntısı) iç bölgede değil
    assert not panel.panelli(_kaydet(kenar, tmp_path / "kenar.jpg"))


@pytest.mark.parametrize(
    "ad,beklenen",
    [("panelli_ganesha", True), ("panelli_monica", True), ("duz_tenere", False), ("duz_agac", False)],
)
def test_gercek_karelerde_olcum_tutar(ad, beklenen):
    """Ölçüm kümesinden 384 px'e küçültülmüş kareler: iki panelli (Ganesha 4 panel, Mónica 2 panel ince ara boşluk) ve
    eşiğe en yakın iki panelsiz kare (Ténéré kamyonu: toz bandı, ağaç: zemin bandı; komşu ortalaması 0,83 ve 0,80)."""
    assert panel.panelli(Path(__file__).parent / "veri" / "panel" / f"{ad}.jpg") is beklenen


def test_panelsiz_istem_dunya_cumlesini_dusurur():
    dunya = "Boston's North End, 1919, gray winter light."
    istem = uretim.gorsel_istemi("Watercolor", dunya, [], "Modern summer street in Boston's North End.")
    yeni = uretim.panelsiz_istem(istem, dunya)
    assert dunya not in yeni and "Modern summer street" in yeni and yeni.endswith(uretim.TEK_KARE)
    assert uretim.panelsiz_istem("Watercolor. A scene.", "").endswith(uretim.TEK_KARE)


def _sc(n: int = 3) -> senaryo.Senaryo:
    return senaryo.Senaryo("B", "m", "Delhi, 1995.", [], ["l"] * n, [f"Scene {i} at a temple." for i in range(n)])


def test_panelli_sahne_dunyasiz_istemle_yeniden_cizilir_hak_sinirli(tmp_path, monkeypatch):
    for i in range(4):
        (tmp_path / f"sahne_{i}.jpg").write_bytes(b"eski")
    panelli = {1, 2, 3}  # 1: ilk yeniden çizimde düzelir; 2: iki denemede de panelli; 3: video hakkı biter
    cizim: dict[int, int] = {}

    def denetle(yol):
        i = int(yol.stem.split("_")[1])
        return i in panelli and not (i == 1 and cizim.get(1))

    istemler, tohumlar = [], []

    def gorsel(istem, yol, tohum, **_):
        i = int(yol.stem.split("_")[1])
        cizim[i] = cizim.get(i, 0) + 1
        istemler.append(istem)
        tohumlar.append(tohum)
        yol.write_bytes(b"yeni")
        return yol

    monkeypatch.setattr(panel, "panelli", denetle)
    monkeypatch.setattr(cf, "gorsel", gorsel)
    sc = _sc(4)
    k = uretim.panelleri_ayikla(sc, uretim.istemleri_kur("Ink", sc), tmp_path, 100)
    assert cizim == {1: 1, 2: 2} and k["yeniden"] == uretim.PANEL_YENIDEN == 3
    assert k["ilk"] == [1, 2, 3] and k["son"] == [2, 3] and k["cizilen"] == [1, 2]
    assert all("Delhi, 1995." not in s and uretim.TEK_KARE in s and s.endswith(uretim.YAZISIZ) for s in istemler)
    assert len(set(tohumlar)) == 3 and not list(tmp_path.glob("panelli_*"))
    assert (tmp_path / "sahne_3.jpg").read_bytes() == b"eski"


def test_panelli_sahne_kotaya_takilirsa_eski_kare_yerinde_kalir(tmp_path, monkeypatch):
    (tmp_path / "sahne_0.jpg").write_bytes(b"eski")
    monkeypatch.setattr(panel, "panelli", lambda yol: True)

    def kota(*a, **k):
        raise cf.KotaHatasi("kota")

    monkeypatch.setattr(cf, "gorsel", kota)
    sc = _sc(1)
    with pytest.raises(cf.KotaHatasi):
        uretim.panelleri_ayikla(sc, uretim.istemleri_kur("Ink", sc), tmp_path, 0)
    assert (tmp_path / "sahne_0.jpg").read_bytes() == b"eski" and not list(tmp_path.glob("panelli_*"))


def test_cok_mekanli_tarif_onarima_gider_tek_mekanli_sayi_gitmez(monkeypatch):
    ganesha = (
        "Three separate temples in different settings: a marble temple in a European city, a wooden shrine in North "
        "America, and a colorful temple in Kenya."
    )
    kopekler = "Modern visitors stand before a museum wall painting of three distinct dogs, smiling and pointing."
    assert senaryo.cok_yerliler([kopekler, ganesha]) == [(2, senaryo.COK_YER_NEDEN)]
    sc = senaryo.Senaryo("B", "m", "1990s New Delhi, warm sunrise.", [], ["l"] * 2, [kopekler, ganesha])
    tek = "A crowd of worshippers in a marble temple holds out spoons of milk to a Ganesha statue at dawn."
    istemler = []

    def sohbet(istem, sema):
        istemler.append(istem)
        return {"world": "", "scenes": [{"scene": 2, "image": tek}]}

    monkeypatch.setattr(senaryo.cf, "sohbet", sohbet)
    senaryo.gorsel_temizle(sc)
    isaretli = istemler[0].split("FLAGGED")[1].split("Rewrite")[0]
    assert f"scene 2: {senaryo.COK_YER_NEDEN}" in isaretli and "scene 1" not in isaretli
    assert sc.gorseller == [kopekler, tek] and sc.gorsel_onarim == [[[2, senaryo.COK_YER_NEDEN]], []]


def test_onarim_tutmazsa_cok_mekanli_tarif_kalir_yazi_yan_cumlesi_yine_duser(monkeypatch):
    """Çok mekânlı tarifin kod yedeği yok (piksel denetimi yakalar); yazı taşıyan yan cümle ise yine kodla düşer."""
    cok = "Two different cities side by side at dusk, crowds in each, lanterns glowing over the streets tonight."
    yazili = "A grocer counts milk bottles behind the counter at dawn; a sign above reads SOLD OUT in red."
    sc = senaryo.Senaryo("B", "m", "1990s New Delhi, warm sunrise.", [], ["l"] * 2, [cok, yazili])
    monkeypatch.setattr(senaryo.cf, "sohbet", lambda istem, sema: {"world": "", "scenes": []})
    senaryo.gorsel_temizle(sc)
    assert sc.gorseller[0] == cok and "sign" not in sc.gorseller[1]
    assert sc.gorsel_onarim[1] == [[1, senaryo.COK_YER_NEDEN]]


def test_gorsel_kurali_tek_mekan_ister():
    for tur in ("tuhaf", "masal"):
        assert "one place at one moment" in senaryo.GORSEL_KURALI[tur]
