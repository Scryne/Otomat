"""2026-10-13 tam denetiminin analitik, haydut, rapor ve Buffer bulguları: her test düzeltmeden önceki hatalı davranışı
reddeder."""

import dataclasses
import datetime as dt
import json
import subprocess
from pathlib import Path

import pytest

from otomat import analitik, durum, gunluk, haydut, kanal, portfoy, rapor


@pytest.fixture
def kanal_sec(monkeypatch):
    def sec(kimlik):
        monkeypatch.setenv("OTOMAT_KANAL", kimlik)
        kanal._aktif.cache_clear()

    yield sec
    kanal._aktif.cache_clear()


def _secim(db, tarih, video_id, kalip="karakter"):
    db.execute(
        "INSERT OR REPLACE INTO secimler VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
        (tarih, f"ezop:{tarih}", f"h{tarih}", "ezop", kalip, "illustrasyon", f"B {tarih}", f"{tarih}T20:00:00+00:00",
         video_id),
    )  # fmt: skip


def _olcum(db, video_id, gun, engaged):
    db.execute("INSERT INTO olcumler VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (video_id, gun, gun, engaged, engaged, 50.0,
                                                                       10.0, 0))  # fmt: skip


def test_haydut_donem_oncesini_ve_geri_cekileni_saymaz(kanal_sec, tmp_path):
    """Orbit'in 0 izlenmeli çocuk dönemi (MFK) genel kitle formatının karakter/sorun kollarını aşağı çekiyordu."""
    kanal_sec("uzay")
    assert kanal.aktif().donem == "2026-10-15"
    db = durum.baglan(tmp_path / "d.db")
    for tarih, vid, e in [("2026-10-10", "cocuk", 0), ("2026-10-16", "a", 30), ("2026-10-17", "b", 10),
                          ("2026-10-18", "c", 20), ("2026-10-19", "cekilen", 99)]:  # fmt: skip
        _secim(db, tarih, vid)
        _olcum(db, vid, tarih, e)
    _secim(db, "2026-10-20", "a")  # aynı video ikinci seçim satırında: bir kez sayılır
    durum.geri_cek(db, ["cekilen"], dt.date(2026, 10, 20), "kalite")
    od = haydut.oduller(db, dt.date(2026, 10, 25))
    assert sorted(o["video_id"] for o in od) == ["a", "b", "c"]
    assert all(o["komsu"] == 2 for o in od)  # çocuk dönemi ve geri çekilen komşu da sayılmaz


def test_bos_analitik_satiri_genc_videoda_olcum_sayilmaz(tmp_path, monkeypatch):
    db = durum.baglan(tmp_path / "d.db")
    _secim(db, "2026-10-10", "v")
    monkeypatch.setattr(
        analitik, "durumlar", lambda yt, ids: {"v": {"public": True, "yayin_gunu": dt.date(2026, 10, 10)}}
    )
    bos = {"views": 0, "engaged_views": 0, "ort_izlenme_yuzde": 0, "ort_izlenme_sn": 0, "abone": 0, "bos": True}
    monkeypatch.setattr(analitik, "pencere", lambda ya, vid, gun: bos)
    assert analitik.olc(db, None, None, dt.date(2026, 10, 15)) == []  # gecikme olabilir: kalıcı sıfır yazılmaz
    assert analitik.olc(db, None, None, dt.date(2026, 10, 17)) == ["v"]  # bir hafta doldu: sıfır gerçek


def _kosu(tarih, durum_, **ek):
    return json.dumps({"tarih": tarih, "kosu": tarih, "mod": "buffer", "durum": durum_, **ek})


def test_rapor_ayni_slotu_bir_kez_sayar_cekileni_ulasan_saymaz(tmp_path, monkeypatch):
    """H41 raporu Walnut-Tree'yi iki kez saymıştı (Plan B'den sonra hazır üretimle çıktı); "kanala ulaşan" geri
    çekilen veri videolarını da sayıyordu."""
    monkeypatch.setattr(rapor, "RAPORLAR", tmp_path)
    satirlar = [
        _kosu("2026-10-06", "tamam", video_id=None, baslik="W", neuron=1349),
        _kosu("2026-10-06", "tamam", video_id="w", baslik="W", neuron=0),
        _kosu("2026-10-07", "tamam", video_id="x", baslik="X", neuron=1474),
        _kosu("2026-10-08", "kota"),
    ]
    (tmp_path / "gunluk.jsonl").write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    db = durum.baglan(tmp_path / "d.db")
    _secim(db, "2026-10-06", "w")
    _secim(db, "2026-10-07", "x")
    durum.geri_cek(db, ["x"], dt.date(2026, 10, 9), "kalite")
    metin = rapor.olustur(db, 2026, 41, None, None, "yok")
    assert "Üretilen **2**" in metin and "kanala ulaşan **1**" in metin and "3/7 gün, 4 satır" in metin
    assert "2.823 neuron" in metin  # harcama gerçek: iki koşunun neuron'u da sayılır


def test_rapor_bekleyen_eski_eksik_haftayi_ve_analitiksiz_raporu_yeniden_yazar(tmp_path, monkeypatch):
    monkeypatch.setattr(rapor, "RAPORLAR", tmp_path)
    bugun = dt.date(2026, 10, 27)  # H44 pazartesi
    satirlar = [_kosu(t, "tamam") for t in ("2026-10-08", "2026-10-15", "2026-10-22")]  # H41, H42, H43
    (tmp_path / "gunluk.jsonl").write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    assert rapor.bekleyen(bugun) == (2026, 41)  # eskiden yalnız H43'e bakıyordu
    for h in (41, 42, 43):
        rapor.dosya(2026, h).write_text("r", encoding="utf-8")
        rapor.dosya(2026, h).with_suffix(".json").write_text(json.dumps({"analitik_hatasi": None}), "utf-8")
    assert rapor.bekleyen(bugun) is None
    rapor.dosya(2026, 43).with_suffix(".json").write_text(json.dumps({"analitik_hatasi": "invalid_grant"}), "utf-8")
    assert rapor.bekleyen(bugun) == (2026, 43)  # analitiksiz rapor iki hafta içinde yeniden denenir
    assert rapor.bekleyen(dt.date(2026, 11, 20)) is None


def test_olme_sayaci_format_doneminden_baslar(tmp_path):
    db = durum.baglan(tmp_path / "d.db")
    _secim(db, "2026-10-09", "cocuk")
    _secim(db, "2026-10-15", "yeni")
    db.commit()
    db.close()
    k = dataclasses.replace(kanal.yukle("uzay"), durum=tmp_path / "d.db", donem="2026-10-15")
    assert portfoy.ilk_public(k) == dt.date(2026, 10, 15)  # eskiden 10-09 (çocuk dönemi) sayacı başlatıyordu


def test_api_kotasi_pasifik_gunune_yazilir():
    assert portfoy._api_gunu({"tarih": "2026-10-13", "kosu_ani": "2026-10-13T06:17+00:00"}) == "2026-10-12"
    assert portfoy._api_gunu({"tarih": "2026-10-13", "kosu_ani": "2026-10-13T16:47+00:00"}) == "2026-10-13"
    assert portfoy._api_gunu({"tarih": "2026-10-13"}) == "2026-10-13"


def test_site_push_reddedilince_rebase_ile_yeniden_dener(monkeypatch):
    """İki kanal işi aynı anda site reposuna yazınca ikincinin push'u non-fast-forward'la düşüyordu."""
    from otomat.yayin import buffer

    komutlar, ret = [], iter([True, False])

    def run(cmd, **k):
        komutlar.append(cmd)
        if "push" in cmd and next(ret):
            raise subprocess.CalledProcessError(1, cmd, stderr="! [rejected] (fetch first)")
        return subprocess.CompletedProcess(cmd, 1 if "diff" in cmd else 0)

    monkeypatch.setattr(buffer.subprocess, "run", run)
    monkeypatch.setattr(buffer.time, "sleep", lambda _: None)
    buffer._site(lambda kopya: "mesaj")
    adlar = [next(a for a in c if a in ("clone", "add", "commit", "push", "pull", "diff")) for c in komutlar]
    assert adlar == ["clone", "add", "diff", "commit", "push", "pull", "push"]


def test_site_push_hatasi_stderrle_bildirilir(monkeypatch):
    from otomat.yayin import buffer

    def run(cmd, **k):
        if "push" in cmd or "pull" in cmd:
            raise subprocess.CalledProcessError(1, cmd, stderr="Permission denied (publickey)")
        return subprocess.CompletedProcess(cmd, 1 if "diff" in cmd else 0)

    monkeypatch.setattr(buffer.subprocess, "run", run)
    monkeypatch.setattr(buffer.time, "sleep", lambda _: None)
    with pytest.raises(buffer.BufferHatasi, match="publickey"):  # eskiden yalnız "exit status 1"
        buffer._site(lambda kopya: "mesaj")


def test_buffer_duserse_hikaye_harcanmaz_sonraki_kosu_yeniden_yayinlar(tmp_path, monkeypatch):
    db = durum.baglan(tmp_path / "d.db")
    paket = type("P", (), {"anahtar": "ezop:The Fox", "hash": "h", "kol": "ezop", "tur": "masal"})()
    meta = {"baslik": "B", "secim": {"kaynak": {}}, "sure_sn": 30, "neuron": 1500, "zaman_sn": {}}
    monkeypatch.setattr(gunluk, "HIKAYE", True)
    monkeypatch.setattr(gunluk, "hikaye_uret", lambda *a: (paket, "karakter", "illustrasyon",
                                                          {"degisti": [], "odul_sayisi": 0}, tmp_path, meta))  # fmt: skip
    monkeypatch.setattr(gunluk, "hazirla", lambda d: {"yerel": {}, "atlanan": [], "kota": False})

    def duser(*a):
        raise RuntimeError("Buffer 900 sn'de gitmedi")

    monkeypatch.setattr(gunluk, "yayinla_buffer", duser)
    teslim = []
    monkeypatch.setattr(gunluk, "teslime_koy", lambda d, g, a="": teslim.append(a) or gunluk.KOK / "teslim")
    kayit, alarmlar = {}, []
    an = dt.datetime(2026, 10, 15, 20, tzinfo=dt.UTC)
    gunluk.bir_video([paket], db, an.date(), an, "buffer", kayit, alarmlar)
    assert kayit["video_id"] is None and teslim == ["ezop:The Fox"]
    assert durum.taze_mi(db, paket, an.date(), gunluk.HIKAYE_TEKRAR_GUN)  # hazır üretim sonraki koşuda kullanır
    assert "yeniden yayınlamayı" in alarmlar[0]


def test_teslim_dosya_adi_hikayeyi_tasir(tmp_path, monkeypatch):
    monkeypatch.setattr(gunluk, "KOK", tmp_path)
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "video.mp4").write_bytes(b"v")
    (tmp_path / "d" / "meta.json").write_text(json.dumps({"baslik": "B", "aciklama": "A", "etiketler": []}), "utf-8")
    hedef = gunluk.teslime_koy(tmp_path / "d", dt.date(2026, 10, 15), "wiki:Great Molasses Flood")
    assert sorted(p.name for p in hedef.iterdir()) == ["2026-10-15_Great-Molasses-Flood_YUKLE.md",
                                                       "2026-10-15_Great-Molasses-Flood_video.mp4"]  # fmt: skip


def test_buffer_sinirina_yaklasinca_toplam_tum_kanallardan(tmp_path, monkeypatch):
    for ad, istek in (("a", 1500), ("b", 1200)):
        (tmp_path / ad).mkdir()
        (tmp_path / ad / "gunluk.jsonl").write_text(
            _kosu("2026-10-10", "tamam", buffer_istek=istek) + "\n" + _kosu("2026-08-01", "tamam", buffer_istek=999)
            + "\n", encoding="utf-8")  # fmt: skip
    monkeypatch.setattr(gunluk.kanal, "hepsi", lambda: ["a", "b"])
    monkeypatch.setattr(gunluk.kanal, "yukle", lambda k: type("K", (), {"raporlar": Path(tmp_path / k)})())
    assert gunluk.buffer_istekleri(dt.date(2026, 10, 13)) == 2700 > gunluk.BUFFER_ESIK  # 30 günden eskisi sayılmaz
