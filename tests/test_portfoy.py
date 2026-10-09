"""Portföy raporu (Faz 13): kanallar yan yana, kanal başına öldürme kriteri, paylaşılan kotalar."""

import dataclasses
import datetime as dt
import json

import pytest

from otomat import durum, kanal, portfoy


@pytest.fixture
def kanallar(tmp_path, monkeypatch):
    """Gerçek profiller, test klasörüne yönlendirilmiş rapor ve durum yollarıyla."""
    sonuc = []
    for kimlik in ("earth", "uzay"):
        k = dataclasses.replace(kanal.yukle(kimlik), raporlar=tmp_path / kimlik, durum=tmp_path / f"{kimlik}.db")
        k.raporlar.mkdir()
        sonuc.append(k)
    monkeypatch.setattr(portfoy, "aktif_kanallar", lambda: sonuc)
    monkeypatch.setattr(portfoy, "PORTFOY", tmp_path / "portfoy")
    return sonuc


def _jsonl(k, satirlar):
    (k.raporlar / "gunluk.jsonl").write_text("".join(json.dumps(s) + "\n" for s in satirlar), encoding="utf-8")


def test_matris_kanallari_okunur():
    assert [k.id for k in portfoy.aktif_kanallar()] == ["earth", "uzay"]


def test_portfoy_kanallari_yan_yana_ve_kotalar(kanallar):
    earth, uzay = kanallar
    _jsonl(earth, [
        {"tarih": "2026-10-13", "kosu": "2026-10-12", "durum": "tamam", "video_id": "v1", "diller": ["es", "pt"],
         "neuron": 2000, "buffer_istek": 10, "havuz_kalan": 700,
         "dusen_hikayeler": [{"anahtar": "wiki:x", "sorunlar": [], "neuron": 500}]},
        {"tarih": "2026-10-14", "kosu": "2026-10-12", "durum": "kota"},
        {"tarih": "2026-10-04", "kosu": "2026-10-04", "durum": "tamam", "buffer_istek": 5},  # önceki hafta
    ])  # fmt: skip
    _jsonl(uzay, [{"tarih": "2026-10-12", "kosu": "2026-10-12", "durum": "tamam", "video_id": "v2", "diller": [],
                   "neuron": 1200, "buffer_istek": 8, "havuz_kalan": 140}])  # fmt: skip
    hafta = {"views": 1500, "engaged_views": 900, "abone_net": 3, "abone_toplam": 12, "video_sayisi": 4}
    (earth.raporlar / "2026-H42.json").write_text(
        json.dumps({"hafta": hafta, "son_56_gun": {**hafta, "views": 4000}, "analitik_hatasi": None}), "utf-8"
    )
    db = durum.baglan(earth.durum)
    db.execute(
        "INSERT INTO secimler VALUES ('2026-10-01','a','h','k','k','s','B','2026-10-01T14:00:00+00:00','eski',NULL)"
    )
    db.execute(
        "INSERT INTO secimler VALUES ('2026-10-10','b','h','k','k','s','B','2026-10-10T14:00:00+00:00','v0',NULL)"
    )
    durum.geri_cek(db, ["eski"], dt.date(2026, 10, 8), "format değişimi")
    db.close()

    ozetler = [portfoy.kanal_ozeti(k, 2026, 42) for k in kanallar]
    e, u = ozetler
    assert (e["uretilen"], e["kanala_cikan"], e["kota"], e["dusen_hikaye"]) == (1, 1, 1, 1)
    assert e["neuron"] == 2500 and e["buffer_istek"] == 10 and e["buffer_30_gun"] == 15
    assert e["gunluk_api"] == {"2026-10-12": 50 + 400 * 3 + portfoy.API_KOSU}
    assert e["ilk_public"] == dt.date(2026, 10, 10) and u["ilk_public"] is None  # geri çekilen sayılmaz

    metin = portfoy.olustur(2026, 42, ozetler, {"earth": 20, "uzay": 18, "ortak": 7})
    assert "| | Inkwell Oddities (`earth`) | Lanternbug Tales (`uzay`) |" in metin
    assert "| Görüntüleme (hafta) | 1.500 | — |" in metin and "| Abone (net · toplam) | +3 · 12 | — |" in metin
    assert "| Hikâye havuzu (kalan) | 700 | 140 |" in metin
    assert "karar günü 2026-12-05 (9/56 gün); son 56 günde 4.000 / 1.200.000 görüntüleme, 12 / 200 abone" in metin
    assert "Lanternbug Tales**: kanalda henüz yeni formatta video yok" in metin
    assert "Cloudflare neuron: haftada 3.700; en yoğun gün 2026-10-12 3.700 (sınır günde 10.000)" in metin
    assert "Buffer: son 30 günde 23 istek" in metin and "haftada 45 dk (ortak işler 7)" in metin
    assert "GitHub belirteci yoktu" in portfoy.olustur(2026, 42, ozetler, None)


def test_bekleyen_kanal_raporlarini_bekler_bir_kez_yazar(kanallar, monkeypatch):
    earth, uzay = kanallar
    monkeypatch.setattr(portfoy, "actions_dakikasi", lambda *a: None)
    sali = dt.date(2026, 10, 20)  # biten hafta: 42
    assert portfoy.bekleyen(sali) is None  # hiç kayıt yok
    _jsonl(earth, [{"tarih": "2026-10-13", "durum": "tamam"}])
    _jsonl(uzay, [{"tarih": "2026-10-13", "durum": "tamam"}])
    (earth.raporlar / "2026-H42.md").write_text("r", encoding="utf-8")
    assert portfoy.bekleyen(sali) is None  # uzay'ın raporu henüz yok
    (uzay.raporlar / "2026-H42.md").write_text("r", encoding="utf-8")
    assert portfoy.bekleyen(sali) == (2026, 42)
    portfoy.yaz(2026, 42)
    assert portfoy.bekleyen(sali) is None and portfoy.dosya(2026, 42).exists()
    assert portfoy.bekleyen(dt.date(2026, 10, 8)) is None  # ILK_HAFTA'dan önce rapor yok


def test_is_dakikasi_yukari_yuvarlar_atlanani_saymaz():
    assert portfoy.is_dakikasi({"started_at": "2026-10-09T17:00:00Z", "completed_at": "2026-10-09T17:10:01Z"}) == 11
    assert portfoy.is_dakikasi({"started_at": "2026-10-09T17:00:00Z", "completed_at": "2026-10-09T17:00:03Z"}) == 1
    assert portfoy.is_dakikasi({"conclusion": "skipped", "started_at": "x", "completed_at": "y"}) == 0
