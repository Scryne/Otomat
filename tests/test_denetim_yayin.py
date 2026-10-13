"""2026-10-13 tam denetiminin orkestrasyon ve yayın bulguları: her test düzeltmeden önceki hatalı davranışı reddeder."""

import datetime as dt
import json
from datetime import UTC

import pytest

from otomat import durum, gunluk
from otomat.yayin import ceviri, hazirla, youtube


def _secim(db, tarih: str, yayin_ani: str, video_id: str | None) -> None:
    db.execute(
        "INSERT INTO secimler VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
        (tarih, f"k:{tarih}", f"h{tarih}", "k", "kalip", "sablon", f"B {tarih}", yayin_ani, video_id),
    )


def _ortam(tmp_path, monkeypatch, db, uretim):
    monkeypatch.setenv("OTOMAT_YAYIN", "buffer")
    monkeypatch.setattr(gunluk.durum, "baglan", lambda: db)
    monkeypatch.setattr(gunluk, "RAPOR", tmp_path / "gunluk.jsonl")
    monkeypatch.setattr(gunluk, "ALARM", tmp_path / "alarm.md")
    monkeypatch.setattr(gunluk.rapor, "RAPORLAR", tmp_path)
    monkeypatch.setattr(gunluk, "HIKAYE", False)
    monkeypatch.setattr(gunluk, "analitik_adimi", lambda *a: (None, None))
    monkeypatch.setattr(youtube, "servis", lambda *a, **k: object())
    monkeypatch.setattr(gunluk, "topla", lambda: ([], []))
    monkeypatch.setattr(gunluk, "bir_video", uretim)


class _Yt:
    """videos().list/update çağrılarını kaydeden sahte YouTube servisi."""

    def __init__(self, durumlar=None):
        self.durumlar, self.guncellenen, self._yanit = durumlar or {}, [], {}

    def videos(self):
        return self

    def list(self, part, id):
        self._yanit = {"items": [{"id": v, "status": self.durumlar[v]} for v in id.split(",") if v in self.durumlar]}
        return self

    def update(self, part, body):
        self.guncellenen.append((part, body))
        self._yanit = {}
        return self

    def execute(self, **_):
        return self._yanit


def test_token_dusmusse_uretime_girmez_hikaye_harcamaz(tmp_path, monkeypatch):
    """Token düşükken Buffer videoyu private yüklüyor, planlama düşüyor, slot dolu sayılıyordu (C1)."""
    db = durum.baglan(tmp_path / "d.db")
    cagri = []
    _ortam(tmp_path, monkeypatch, db, lambda *a: cagri.append(a))

    def yetkisiz(*a, **k):
        raise youtube.YetkiHatasi("invalid_grant")

    monkeypatch.setattr(youtube, "servis", yetkisiz)
    with pytest.raises(youtube.YetkiHatasi):
        gunluk.main()
    assert cagri == [] and db.execute("SELECT count(*) FROM secimler").fetchone()[0] == 0
    assert "gh secret set" in (tmp_path / "alarm.md").read_text(encoding="utf-8")  # çözüm adımları alarmda


def test_pist_denetimi_plansizi_yeniden_planlar_kayibi_bildirir(tmp_path, monkeypatch):
    db = durum.baglan(tmp_path / "d.db")
    simdi = dt.datetime(2026, 10, 13, 18, tzinfo=UTC)
    _secim(db, "2026-10-14", "2026-10-14T14:00:00+00:00", "plansiz")
    _secim(db, "2026-10-15", "2026-10-15T14:00:00+00:00", "kayip")
    _secim(db, "2026-10-16", "2026-10-16T14:00:00+00:00", "planli")
    _secim(db, "2026-10-12", "2026-10-12T14:00:00+00:00", "gecmis")  # yayınlanmış: denetlenmez
    _secim(db, "2026-10-17", "2026-10-17T14:00:00+00:00", "cekilen")
    _secim(db, "2026-10-18", "2026-10-18T14:00:00+00:00", "elle")  # Studio'dan elle private: dokunulmaz
    durum.geri_cek(db, ["cekilen"], simdi.date(), "kalite")
    durum.planlanamadi(db, "plansiz", dt.datetime(2026, 10, 14, 14, tzinfo=UTC))  # Buffer yükledi, planlama düştü
    yt = _Yt({"plansiz": {"privacyStatus": "private", "selfDeclaredMadeForKids": False},
              "planli": {"privacyStatus": "private", "publishAt": "2026-10-16T14:00:00Z"},
              "elle": {"privacyStatus": "private"}})  # fmt: skip
    kayit, alarmlar = {}, []
    gunluk.pist_denetimi(db, yt, simdi, kayit, alarmlar)
    assert kayit["pist"] == {"denetlenen": 4, "onarilan": ["plansiz"], "kayip": ["kayip"], "plansiz": ["elle"]}
    assert len(yt.guncellenen) == 1  # yalnız kaydedilmiş başarısızlık
    part, govde = yt.guncellenen[0]
    assert govde["id"] == "plansiz" and govde["status"]["publishAt"] == "2026-10-14T14:00:00.000Z"
    assert govde["status"]["publicStatsViewable"] is True and govde["status"]["selfDeclaredMadeForKids"] is False
    assert len(alarmlar) == 3 and any("kayip" in a for a in alarmlar) and any(":** elle." in a for a in alarmlar)
    assert db.execute("SELECT count(*) FROM planlanamayan").fetchone()[0] == 0  # onarılan kayıttan düşer


def test_uzak_slot_ust_uste_iki_kez_duserse_alarm(tmp_path, monkeypatch):
    """Uzak slotta düşüş alarmsızdı; sistemik bir kapı hatası havuzu her koşu 3 hikâye yakıyordu (A1)."""
    db = durum.baglan(tmp_path / "d.db")
    bugun = dt.datetime.now(UTC).date()
    for i in (0, 1):  # bugün ve yarın planlı: sıradaki slot pistin uzak günü (T+2)
        g = dt.datetime.combine(bugun + dt.timedelta(days=i), dt.time(gunluk.YAYIN_SAATI_UTC), UTC)
        _secim(db, g.date().isoformat(), g.isoformat(), f"v{i}")

    def duser(*a):
        raise gunluk.HikayeDustu("3 hikâye de hakemden geçmedi")

    _ortam(tmp_path, monkeypatch, db, duser)
    gunluk.main()
    assert not (tmp_path / "alarm.md").exists()  # ilk düşüş: alarm yok
    gunluk.main()
    assert "üst üste" in (tmp_path / "alarm.md").read_text(encoding="utf-8")


def test_duzenle_gecmis_yayin_anini_hemen_public_yapar(monkeypatch):
    yt = _Yt()
    monkeypatch.setattr(youtube, "KATEGORI", "27", raising=False)
    gecmis = dt.datetime.now(UTC) - dt.timedelta(minutes=10)
    youtube.duzenle("v", "Başlık burada", "Açıklama", ["e"], gecmis, None, yt=yt)
    durum_ = yt.guncellenen[0][1]["status"]
    assert durum_["privacyStatus"] == "public" and "publishAt" not in durum_
    ileri = dt.datetime.now(UTC) + dt.timedelta(days=1)
    youtube.duzenle("v", "Başlık burada", "Açıklama", ["e"], ileri, None, yt=yt)
    planli = yt.guncellenen[1][1]["status"]
    assert planli["privacyStatus"] == "private" and "publishAt" in planli


def test_planla_gecmis_ani_public_yapar_mfk_videodan_gelir():
    yt = _Yt({"v": {"privacyStatus": "private", "selfDeclaredMadeForKids": True}})
    youtube.planla("v", dt.datetime.now(UTC) - dt.timedelta(hours=1), yt=yt)
    durum_ = yt.guncellenen[0][1]["status"]
    assert durum_["privacyStatus"] == "public" and durum_["selfDeclaredMadeForKids"] is True


def test_ceviri_kotada_kalan_dilleri_denemez(tmp_path, monkeypatch):
    """10-15 Earth: dört dilin dördü kotaya takıldı, her dil 3 tohumla boşa denendi, sonuç sessizce çevirisizdi."""
    meta = {"baslik": "B", "aciklama": "A", "altyazi": [{"bas": 0.0, "son": 1.0, "metin": "One two three"}]}
    (tmp_path / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    cagri = []

    def cevir(dil, *a, **k):
        cagri.append(dil)
        raise ceviri.CeviriKotasi("kota")

    monkeypatch.setattr(ceviri, "cevir", cevir)
    sonuc = hazirla.hazirla(tmp_path)
    assert len(cagri) == 1 and sonuc["kota"] is True and len(sonuc["atlanan"]) == len(sonuc["atlanan"]) > 0
    assert json.loads((tmp_path / "yerel.json").read_text(encoding="utf-8"))["kota"] is True


@pytest.mark.parametrize(
    "yanit",
    [
        {"title": "", "description": "d", "captions": ["Uno dos tres"]},
        {"title": "t", "description": "d", "captions": [None]},
        {"description": "d", "captions": ["Uno dos tres"]},
    ],
)
def test_ceviri_bos_ya_da_bozuk_alani_reddeder(monkeypatch, yanit):
    monkeypatch.setattr(ceviri, "_uret", lambda *a: yanit)
    assert ceviri._cevir("es", "t", "d", ["One two three"]) is None  # eskiden 400 ya da KeyError/TypeError


def test_aciklama_bayt_sinirinda_kesilir():
    metin = "ü" * 3000  # 6000 bayt
    k = ceviri.kes(metin, 5000)
    assert len(k.encode("utf-8")) <= 5000 and k == "ü" * 2500


def test_altyazi_biri_duserse_digerleri_yuklenir(tmp_path, monkeypatch):
    from otomat.yayin import buffer

    meta = {"baslik": "B", "aciklama": "A", "etiketler": []}
    (tmp_path / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    for dil in ("de", "en", "es"):
        (tmp_path / f"{dil}.srt").write_text("1", encoding="utf-8")
    monkeypatch.setattr(buffer, "medya_koy", lambda *a: "u")
    monkeypatch.setattr(buffer, "gonder", lambda *a: "vid")
    monkeypatch.setattr(buffer, "medya_kaldir", lambda *a: None)
    monkeypatch.setattr(youtube, "servis", lambda: object())
    monkeypatch.setattr(youtube, "duzenle", lambda *a, **k: None)
    yuklenen = []

    def altyazi(vid, dil, metin, yt):
        if dil == "de":
            raise RuntimeError("quotaExceeded")
        yuklenen.append(dil)

    monkeypatch.setattr(youtube, "altyazi_ekle", altyazi)
    alarmlar = []
    assert gunluk.yayinla_buffer(tmp_path, None, "2026-10-14", alarmlar) == "vid"
    assert yuklenen == ["en", "es"] and "de" in alarmlar[0]  # eskiden ilk hata kalanları atlıyordu


def test_ceviri_onarimi_planli_videonun_eksik_dillerini_tamamlar(tmp_path, monkeypatch):
    """10-15 Earth: dört dil kotaya takıldı, video çevirisiz planlandı ve hiçbir koşu tamamlamıyordu."""
    db = durum.baglan(tmp_path / "d.db")
    simdi = dt.datetime(2026, 10, 13, 22, tzinfo=UTC)
    _secim(db, "2026-10-15", "2026-10-15T14:00:00+00:00", "vid")
    db.execute("UPDATE secimler SET anahtar = 'wiki:Heraclitus'")
    _secim(db, "2026-10-12", "2026-10-12T14:00:00+00:00", "yayinda")  # yayınlanmış: dokunulmaz
    klasor = tmp_path / "onceki" / "2026-10-15" / "wiki_Heraclitus"
    klasor.mkdir(parents=True)
    (klasor / "meta.json").write_text(json.dumps({"paket": {"anahtar": "wiki:Heraclitus"}}), encoding="utf-8")
    (klasor / "yerel.json").write_text(json.dumps({"yerel": {}, "atlanan": ["es", "de"], "kota": True}), "utf-8")
    (klasor / "es.srt").write_text("1\nes", encoding="utf-8")
    monkeypatch.setattr(gunluk, "uretim_dosyalari", lambda ad: [klasor / ad])
    monkeypatch.setattr(gunluk, "hazirla", lambda d: {"yerel": {"es": {"title": "T", "description": "D"}},
                                                       "atlanan": ["de"], "kota": True})  # fmt: skip
    yerel, altyazi = [], []
    monkeypatch.setattr(youtube, "yerellestir", lambda v, y, yt=None: yerel.append((v, sorted(y))))
    monkeypatch.setattr(youtube, "altyazi_ekle", lambda v, d, m, yt=None: altyazi.append((v, d)))
    kayit, alarmlar = {}, []
    gunluk.ceviri_onarimi(db, object(), simdi, kayit, alarmlar)
    assert yerel == [("vid", ["es"])] and altyazi == [("vid", "es")] and alarmlar == []
    assert kayit["ceviri_onarimi"] == [{"video_id": "vid", "diller": ["es"]}]
