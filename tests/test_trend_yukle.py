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


class _Durum:
    def __init__(self, durum: dict[str, str]):
        self.durum = durum

    def videos(self):
        return self

    def list(self, part, id):
        return _Istek({"items": [{"id": k, "status": {"uploadStatus": self.durum.get(k, "uploaded")}}
                                 for k in id.split(",")]})  # fmt: skip


def _bitmis_is(tmp_path, kesit_yuklu=True):
    d = tmp_path / "2026-11-28-is"
    for yol in ("video.mp4", "ses/p000.wav", "kesit1/kesit.mp4", "proje/index.html", "kapak/kapak.jpg"):
        (d / yol).parent.mkdir(parents=True, exist_ok=True)
        (d / yol).write_bytes(b"x" * 10)
    (d / "senaryo.json").write_text("{}", encoding="utf-8")
    (d / "altyazi_en.srt").write_text("1", encoding="utf-8")
    kesitler = {"0": {"video_id": "K1", "yayin": "2026-11-29T00:50:00Z"}} if kesit_yuklu else {}
    (d / "yukleme.json").write_text(json.dumps({"video_id": "V1", "kapak": "tamam", "yayin": "2026-11-28T21:50:00Z",
                                                "kesitler": kesitler}), encoding="utf-8")  # fmt: skip
    return d


def test_temizlik_yalniz_bitmis_ve_islenmis_iste_medyayi_siler(tmp_path):
    d = _bitmis_is(tmp_path)
    assert yukle.temizle(d, _Durum({"V1": "processed"})) == 0  # kesit hâlâ işleniyor
    assert (d / "video.mp4").exists()
    assert yukle.temizle(d, _Durum({"V1": "processed", "K1": "processed"})) == 40
    kalan = sorted(str(p.relative_to(d)).replace("\\", "/") for p in d.rglob("*") if p.is_file())
    assert kalan == ["altyazi_en.srt", "kapak/kapak.jpg", "senaryo.json", "yukleme.json"]
    assert json.loads((d / "yukleme.json").read_text(encoding="utf-8"))["temizlik"]["silinen_mb"] == 0
    assert yukle.temizle(d, _Durum({})) == 0  # ikinci kez dokunmaz


def test_temizlik_kesiti_yuklenmemis_ise_dokunmaz(tmp_path):
    d = _bitmis_is(tmp_path, kesit_yuklu=False)
    assert yukle.temizle(d, _Durum({"V1": "processed"})) == 0
    assert (d / "kesit1" / "kesit.mp4").exists()
