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
    assert kaldirilan == [f"{gunluk._K.id}-2026-10-06.mp4"]


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


def _pist_ortami(tmp_path, monkeypatch, db, uretim):
    monkeypatch.setenv("OTOMAT_YAYIN", "buffer")
    monkeypatch.setattr(gunluk.durum, "baglan", lambda: db)
    monkeypatch.setattr(gunluk, "RAPOR", tmp_path / "gunluk.jsonl")
    monkeypatch.setattr(gunluk, "ALARM", tmp_path / "alarm.md")
    monkeypatch.setattr(gunluk.rapor, "RAPORLAR", tmp_path)  # haftalık rapor da test klasörüne
    monkeypatch.setattr(gunluk, "HIKAYE", False)
    monkeypatch.setattr(gunluk, "analitik_adimi", lambda *a: (None, None))
    monkeypatch.setattr(gunluk, "topla", lambda: ([], []))
    monkeypatch.setattr(gunluk, "bir_video", uretim)


def _yayinlanan(db, gun, yayin_ani, kayit):
    _secim(db, gun.isoformat(), yayin_ani.isoformat(), f"v{gun.isoformat()}")
    t = gun.isoformat()
    kayit.update(durum="tamam", video_id=f"v{t}", anahtar=f"k:{t}", hash=f"h{t}", kalip="kalip", sablon="sablon",
                 baslik=f"B {t}", yayin_ani=yayin_ani.isoformat())  # fmt: skip


def test_pist_bos_slotlari_doldurur_dolunca_atlar(tmp_path, monkeypatch):
    """2026-10-09: tek cron kaçınca o günün yayını da kaçıyordu. Pist: bugün + PIST_GUN gün planlı durur."""
    db = durum.baglan(tmp_path / "d.db")
    _pist_ortami(tmp_path, monkeypatch, db, lambda p, db, gun, an, mod, kayit, al: _yayinlanan(db, gun, an, kayit))
    bugun = dt.datetime.now(UTC).date()
    sinir = bugun + dt.timedelta(days=durum.PIST_GUN)
    for _ in range(4):
        gunluk.main()
    slotlar = sorted(dt.date.fromisoformat(t) for (t,) in db.execute("SELECT tarih FROM secimler"))
    assert slotlar == [slotlar[0] + dt.timedelta(days=i) for i in range(len(slotlar))]  # boşluksuz, günde bir
    assert slotlar[-1] == sinir and slotlar[0] <= bugun + dt.timedelta(days=1)
    assert durum.pist_dolu(db, dt.datetime.now(UTC), "buffer")
    satirlar = [json.loads(s) for s in (tmp_path / "gunluk.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(satirlar) == len(slotlar) and all(s["kosu"] == bugun.isoformat() for s in satirlar)
    assert not (tmp_path / "alarm.md").exists()


def test_pist_kota_yarin_planliysa_alarmsiz_degilse_alarm(tmp_path, monkeypatch):
    from otomat.hikaye.cf import KotaHatasi

    def kota(*a):
        raise KotaHatasi("kota bitti")

    db = durum.baglan(tmp_path / "d.db")
    bugun = dt.datetime.now(UTC).date()
    yarin = dt.datetime.combine(bugun + dt.timedelta(days=1), dt.time(gunluk.YAYIN_SAATI_UTC), UTC)
    _secim(db, yarin.date().isoformat(), yarin.isoformat(), "vyarin")
    _pist_ortami(tmp_path, monkeypatch, db, kota)
    gunluk.main()  # sıradaki slot yarından sonra: alarm yok
    assert not (tmp_path / "alarm.md").exists()
    assert json.loads((tmp_path / "gunluk.jsonl").read_text(encoding="utf-8"))["durum"] == "kota"
    db.execute("DELETE FROM secimler")
    with pytest.raises(KotaHatasi):
        gunluk.main()  # yarının videosu yok: alarm
    assert "kota bitti" in (tmp_path / "alarm.md").read_text(encoding="utf-8")


def test_pist_plan_b_ye_dusen_video_ikinciyi_uretmez(tmp_path, monkeypatch):
    db = durum.baglan(tmp_path / "d.db")
    cagri = []

    def teslim(p, db, gun, an, mod, kayit, al):
        cagri.append(gun)
        kayit.update(durum="tamam", video_id=None)

    _pist_ortami(tmp_path, monkeypatch, db, teslim)
    gunluk.main()
    assert len(cagri) == 1


def test_gonder_cocuk_kanalinda_mfk_yukler(monkeypatch):
    """Orbit (MFK) videoları Buffer'dan "çocuklara özel değil" yükleniyordu; duzenle sonra düzeltiyordu."""
    from otomat import kanal

    girdiler = []

    def sahte(metin, degiskenler=None, tekrar=True):
        if "createPost" in metin:
            girdiler.append(degiskenler["i"])
            return {"createPost": {"post": {"id": "p1"}}}
        return {"post": {"status": "sent", "externalLink": "https://youtube.com/shorts/JXSEMofyS3k"}}

    monkeypatch.setattr(buffer, "kanal_id", lambda: "c1")
    monkeypatch.setattr(buffer, "sorgu", sahte)
    for kimlik, mfk in (("uzay", True), ("earth", False)):
        monkeypatch.setenv("OTOMAT_KANAL", kimlik)
        kanal._aktif.cache_clear()
        buffer.gonder("https://x/v.mp4", "Başlık", "Açıklama")
        assert girdiler[-1]["metadata"]["youtube"]["madeForKids"] is mfk
    kanal._aktif.cache_clear()


def test_sorgu_istek_sayar(monkeypatch):
    class Yanit:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"data": {"ok": 1}}'

    monkeypatch.setattr(buffer, "anahtar", lambda: "k")
    monkeypatch.setattr(buffer.urllib.request, "urlopen", lambda *a, **k: Yanit())
    once = buffer.ISTEK["sayi"]
    assert buffer.sorgu("query { ok }") == {"ok": 1}
    assert buffer.ISTEK["sayi"] == once + 1
