"""Film yükleyicisi: ağsız, sahte YouTube istemcisiyle."""

import datetime as dt
import json
from pathlib import Path

import pytest

from otomat.film import senaryo, uretim, yukle

PILOT = Path(__file__).parents[1] / "filmler" / "violet-jessop" / "senaryo.json"


class _Istek:
    def __init__(self, sonuc):
        self.sonuc = sonuc

    def execute(self, **_):
        return self.sonuc

    def next_chunk(self, **_):
        return None, self.sonuc


class _SahteYT:
    def __init__(self, kanal="One Ticket Back", kapak_hatasi=None):
        self.kanal, self.kapak_hatasi, self.govde, self.kapak = kanal, kapak_hatasi, None, None

    def channels(self):
        return self

    def videos(self):
        return self

    def thumbnails(self):
        return self

    def list(self, **_):
        return _Istek({"items": [{"snippet": {"title": self.kanal}}]})

    def insert(self, part, body, media_body):
        self.govde = body
        return _Istek({"id": "VID123", "status": {"privacyStatus": body["status"]["privacyStatus"]}})

    def set(self, videoId, media_body):
        if self.kapak_hatasi:
            raise self.kapak_hatasi
        self.kapak = videoId
        return _Istek({})


@pytest.fixture
def film(tmp_path, monkeypatch):
    f = senaryo.oku(PILOT)
    d = tmp_path / f.slug
    d.mkdir()
    for ad, icerik in (("video.mp4", b"\0" * 64), ("kapak.jpg", b"\xff\xd8"), ("aciklama.txt", b"Desc <x>")):
        (d / ad).write_bytes(icerik)
    monkeypatch.setattr(uretim, "dizin", lambda film: d)
    return f


def test_yanlis_kanalin_tokeniyle_yuklenmez():
    with pytest.raises(yukle.YuklemeHatasi, match="Inkwell"):
        yukle.kanal_dogrula(_SahteYT("Inkwell Oddities"))


def test_yukleme_kapak_ve_kayit(film):
    yt = _SahteYT()
    kayit = yukle.yukle(film, "unlisted", yt=yt)
    assert kayit["video_id"] == "VID123" and kayit["donen"] == "unlisted" and kayit["kapak"] == "tamam"
    g = yt.govde
    assert g["status"] == {"privacyStatus": "unlisted", "selfDeclaredMadeForKids": False,
                           "containsSyntheticMedia": False}  # fmt: skip
    assert g["snippet"]["title"] == film.baslik and "<" not in g["snippet"]["description"]
    assert "violet jessop" in g["snippet"]["tags"] and g["snippet"]["categoryId"] == "27"
    assert json.loads((uretim.dizin(film) / "yukleme.json").read_text(encoding="utf-8"))["video_id"] == "VID123"


def test_ayni_film_iki_kez_yuklenmez(film):
    yukle.yukle(film, yt=_SahteYT())
    with pytest.raises(yukle.YuklemeHatasi, match="zaten"):
        yukle.yukle(film, yt=_SahteYT())


def test_kapak_dusse_de_video_kaydedilir(film):
    kayit = yukle.yukle(film, yt=_SahteYT(kapak_hatasi=RuntimeError("403 forbidden")))
    assert kayit["video_id"] == "VID123" and "403" in kayit["kapak"]
    assert (uretim.dizin(film) / "yukleme.json").exists()


def test_eksik_dosya_ve_bilinmeyen_gorunurluk(film):
    (uretim.dizin(film) / "kapak.jpg").unlink()
    with pytest.raises(yukle.YuklemeHatasi, match="kapak"):
        yukle.yukle(film, yt=_SahteYT())
    with pytest.raises(yukle.YuklemeHatasi, match="görünürlük"):
        yukle.govde(film, "x", "herkese")


def _utc(*a):
    return dt.datetime(*a, tzinfo=dt.UTC)


def test_film_slotu_haftada_bir_cumartesi():
    pazar = _utc(2026, 10, 18, 12)
    assert yukle.sonraki_film_slotu(pazar, []) == _utc(2026, 10, 24, 19)  # sıradaki cumartesi 19:00 UTC
    cuma_gece = _utc(2026, 10, 23, 20)  # 24 saatten az kala: bir sonraki hafta
    assert yukle.sonraki_film_slotu(cuma_gece, []) == _utc(2026, 10, 31, 19)
    dolu = [_utc(2026, 10, 24, 19)]
    assert yukle.sonraki_film_slotu(pazar, dolu) == _utc(2026, 10, 31, 19)  # aynı hafta ikinci film yok
    assert [yukle.kesit_slotu(dolu[0], i).strftime("%a") for i in range(3)] == ["Mon", "Wed", "Fri"]
    with pytest.raises(yukle.YuklemeHatasi):
        yukle.kesit_slotu(dolu[0], 3)


def test_planli_yukleme_private_ve_publish_at(film, monkeypatch):
    monkeypatch.setattr(yukle, "film_takvimi", lambda kok=None: [])
    yt = _SahteYT()
    kayit = yukle.yukle(film, yt=yt, simdi=_utc(2026, 10, 18, 12))
    assert yt.govde["status"]["privacyStatus"] == "private"
    assert yt.govde["status"]["publishAt"] == "2026-10-24T19:00:00.000Z" == kayit["yayin"]


def test_kesit_filmden_once_yuklenmez_ve_filme_baglanir(film):
    with pytest.raises(yukle.YuklemeHatasi, match="önce film"):
        yukle.yukle_kesit(film, 0, yt=_SahteYT())
    k = film.kesitler[0]
    g = yukle.kesit_govde(film, k, "FILM1", "Hook\n\nChapters\n00:00 A\n\nSources\n- x\n\nMusic\nm")
    aciklama = g["snippet"]["description"]
    assert "watch?v=FILM1" in aciklama and "Chapters" not in aciklama and "Sources" in aciklama
    assert g["snippet"]["title"] == k.baslik
