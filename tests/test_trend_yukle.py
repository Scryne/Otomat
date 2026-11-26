"""Trend yükleme: K-49 yayın günleri (Pzt/Çar/Cmt 21:50 UTC, günde bir) ve kapak yüklenmeden zamanlama yok."""

import datetime as dt
import json

import pytest

from otomat.trend import yukle


def test_siradaki_slot_pzt_car_cmt_ve_dolu_gun_atlanir():
    cuma = dt.datetime(2026, 11, 27, 10, 0, tzinfo=dt.UTC)  # Cuma
    assert yukle.siradaki_slot(cuma, set()) == dt.datetime(2026, 11, 28, 21, 50, tzinfo=dt.UTC)  # Cumartesi
    assert yukle.siradaki_slot(cuma, {"2026-11-28"}) == dt.datetime(2026, 11, 30, 21, 50, tzinfo=dt.UTC)  # Pazartesi
    pzt_gec = dt.datetime(2026, 11, 30, 21, 30, tzinfo=dt.UTC)  # işlenme payı (45 dk) sığmaz
    assert yukle.siradaki_slot(pzt_gec, set()).date() == dt.date(2026, 12, 2)  # Çarşamba


class _Istek:
    def __init__(self, sonuc=None, hata=None):
        self.sonuc, self.hata = sonuc, hata

    def execute(self):
        if self.hata:
            raise self.hata
        return self.sonuc


class _SahteYT:
    def __init__(self, kapak_izni: bool):
        self.kapak_izni, self.guncellemeler, self.n = kapak_izni, [], 0

    def thumbnails(self):
        return self

    def set(self, **_):
        return _Istek({}, None if self.kapak_izni else RuntimeError("403 forbidden"))

    def videos(self):
        return self

    def update(self, part, body):
        self.guncellemeler.append(body)
        return _Istek({})


@pytest.fixture
def is_klasoru(tmp_path, monkeypatch):
    d = tmp_path / "2026-11-27-is"
    (d / "kapak").mkdir(parents=True)
    (d / "kapak" / "kapak.jpg").write_bytes(b"\xff\xd8\xff")
    (d / "video.mp4").write_bytes(b"x")
    (d / "meta.json").write_text(json.dumps({"baslik": "T", "aciklama": "a\n\nSources:\n- x"}), encoding="utf-8")
    (d / "secim.json").write_text(json.dumps({"secim": {"hikaye": "Konu"}}), encoding="utf-8")
    (d / "senaryo.json").write_text(json.dumps({"kesitler": []}), encoding="utf-8")
    monkeypatch.setattr(yukle, "_gonder", lambda yt, g, v: {"id": "VID1", "status": {"privacyStatus": "private"}})
    monkeypatch.setattr(yukle, "dolu_gunler", lambda haric=None: set())
    import googleapiclient.http

    monkeypatch.setattr(googleapiclient.http, "MediaFileUpload", lambda *a, **k: None)
    return d


def test_kapak_yoksa_zamanlanmaz_sonra_tamamlanir(is_klasoru):
    simdi = dt.datetime(2026, 11, 27, 10, 0, tzinfo=dt.UTC)
    yt = _SahteYT(kapak_izni=False)
    k = yukle.yukle(is_klasoru, simdi, yt)
    assert k["video_id"] == "VID1" and "yayin" not in k and "kapak bekliyor" in k["durum"]
    assert yt.guncellemeler == []  # publishAt yazılmadı: private bekler
    yt2 = _SahteYT(kapak_izni=True)
    k2 = yukle.yukle(is_klasoru, simdi, yt2)
    assert k2["kapak"] == "tamam" and k2["yayin"] == "2026-11-28T21:50:00.000Z" and "durum" not in k2
    assert yt2.guncellemeler[0]["status"]["publishAt"] == "2026-11-28T21:50:00.000Z"
