import datetime as dt
import json

import pytest

from otomat import durum, gunluk
from otomat.yayin import buffer, youtube

UTC = dt.UTC


def _secim(db, tarih: str, yayin_ani: str, video_id: str | None) -> None:
    db.execute(
        "INSERT INTO secimler VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
        (tarih, f"k:{tarih}", f"h{tarih}", "k", "kalip", "sablon", f"B {tarih}", yayin_ani, video_id),
    )


def test_yayin_slotu_gunde_bir_ve_kuyruk(tmp_path):
    db = durum.baglan(tmp_path / "d.db")
    sabah = dt.datetime(2026, 10, 6, 6, 20, tzinfo=UTC)
    assert gunluk.yayin_slotu(db, sabah) == dt.datetime(2026, 10, 6, 14, tzinfo=UTC)
    # yayına bir saatten az kaldıysa ertesi gün
    assert gunluk.yayin_slotu(db, sabah.replace(hour=13, minute=30)) == dt.datetime(2026, 10, 7, 14, tzinfo=UTC)
    # kanalda planlı video varsa onun ertesi günü; video_id'siz (Plan B) satır slot tutmaz
    _secim(db, "2026-10-05", "2026-10-08T14:00:00+00:00", "abcdefghijk")
    _secim(db, "2026-10-06", "2026-10-20T14:00:00+00:00", None)
    assert gunluk.yayin_slotu(db, sabah) == dt.datetime(2026, 10, 9, 14, tzinfo=UTC)
    # geri çekilen (private'a alınıp planı kaldırılan) video slot tutmaz (2026-10-08 format değişimi)
    durum.geri_cek(db, ["abcdefghijk"], sabah.date(), "format değişimi")
    assert gunluk.yayin_slotu(db, sabah) == dt.datetime(2026, 10, 6, 14, tzinfo=UTC)


def test_gonder_private_yukler_video_id_doner(monkeypatch):
    cagrilar = []
    durumlar = iter(
        [{"status": "sending"}, {"status": "sent", "externalLink": "https://www.youtube.com/watch?v=JXSEMofyS3k"}]
    )

    def sahte(metin, degiskenler=None, tekrar=True):
        cagrilar.append((metin, degiskenler, tekrar))
        if "createPost" in metin:
            return {"createPost": {"post": {"id": "p1"}}}
        return {"post": next(durumlar)}

    monkeypatch.setattr(buffer, "kanal_id", lambda: "c1")
    monkeypatch.setattr(buffer, "sorgu", sahte)
    monkeypatch.setattr(buffer.time, "sleep", lambda _: None)
    assert buffer.gonder("https://x/v.mp4", "T" * 120, "Açıklama") == "JXSEMofyS3k"
    _, girdi, tekrar = cagrilar[0]
    assert tekrar is False  # mutasyon yeniden denenmez: çift gönderi açmasın
    yt = girdi["i"]["metadata"]["youtube"]
    assert yt["privacy"] == "private" and len(yt["title"]) == 100
    assert girdi["i"]["assets"] == [{"video": {"url": "https://x/v.mp4"}}]


def test_gonder_hata_durumu(monkeypatch):
    def sahte(metin, degiskenler=None, tekrar=True):
        if "createPost" in metin:
            return {"createPost": {"post": {"id": "p1"}}}
        return {"post": {"status": "error", "error": {"message": "video too long"}}}

    monkeypatch.setattr(buffer, "kanal_id", lambda: "c1")
    monkeypatch.setattr(buffer, "sorgu", sahte)
    with pytest.raises(buffer.BufferHatasi, match="video too long"):
        buffer.gonder("https://x/v.mp4", "T", "A")


def _dizin(tmp_path):
    d = tmp_path / "gun"
    d.mkdir(parents=True)
    (d / "video.mp4").write_bytes(b"x")
    (d / "en.srt").write_text("1\n", encoding="utf-8")
    meta = {"baslik": "Başlık", "aciklama": "A", "etiketler": ["data"]}
    (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return d


def test_yayinla_buffer_medyayi_her_durumda_kaldirir(tmp_path, monkeypatch):
    kaldirilan = []
    monkeypatch.setattr(buffer, "medya_koy", lambda v, ad: f"https://site/{ad}")
    monkeypatch.setattr(buffer, "medya_kaldir", kaldirilan.append)

    def dus(*_):
        raise buffer.BufferHatasi("createPost: kota")

    monkeypatch.setattr(buffer, "gonder", dus)
    with pytest.raises(buffer.BufferHatasi):
        gunluk.yayinla_buffer(_dizin(tmp_path), None, "2026-10-06", [])
    assert kaldirilan == ["2026-10-06.mp4"]


def test_yayinla_buffer_planlama_duserse_alarm_ve_id(tmp_path, monkeypatch):
    monkeypatch.setattr(buffer, "medya_koy", lambda v, ad: "https://site/v.mp4")
    monkeypatch.setattr(buffer, "medya_kaldir", lambda ad: None)
    monkeypatch.setattr(buffer, "gonder", lambda *_: "abcdefghijk")
    monkeypatch.setattr(youtube, "servis", lambda: object())
    altyazi = []
    monkeypatch.setattr(youtube, "altyazi_ekle", lambda vid, dil, metin, yt=None: altyazi.append(dil))

    def dus(*_, **__):
        raise RuntimeError("publishAt geçmişte")

    monkeypatch.setattr(youtube, "duzenle", dus)
    alarmlar = []
    an = dt.datetime(2026, 10, 7, 14, tzinfo=UTC)
    assert gunluk.yayinla_buffer(_dizin(tmp_path), an, "2026-10-06", alarmlar) == "abcdefghijk"
    assert "planlanamadı" in alarmlar[0] and "abcdefghijk" in alarmlar[0]
    monkeypatch.setattr(youtube, "duzenle", lambda *_, **__: None)
    assert gunluk.yayinla_buffer(_dizin(tmp_path / "b"), an, "2026-10-06", []) == "abcdefghijk"
    assert altyazi == ["en"]
