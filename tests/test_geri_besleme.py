import datetime as dt
import json
import random

import pytest

from otomat import analitik, durum, gunluk, haydut, rapor
from otomat.veri import Kaynak, OlguPaketi
from otomat.yayin.youtube import YetkiHatasi

GUN = dt.date(2026, 10, 5)


def paket(kol="usgs", anahtar="usgs:bolge_yillik:Chile"):
    return OlguPaketi(
        kol, "bolge_yillik", anahtar, "quakes", {}, {"sablon": "nokta_harita"}, Kaynak("U", "u", "PD", "t")
    )


def secim(db, gun, kol, kalip, baslik, video_id=None, anahtar=None):
    p = paket(kol, anahtar or f"{kol}:{gun}")
    an = dt.datetime.combine(gun, dt.time(14), dt.UTC)
    durum.secim_kaydet(db, gun, p, kalip, "nokta_harita", baslik, an, video_id, None)


def olcum(db, video_id, gun, engaged, yuzde):
    db.execute(
        "INSERT INTO olcumler VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (video_id, gun.isoformat(), (gun + dt.timedelta(days=5)).isoformat(), engaged, engaged, yuzde, 20.0, 0),
    )
    db.commit()


@pytest.fixture
def db(tmp_path):
    return durum.baglan(tmp_path / "t.db")


@pytest.mark.parametrize("a,b", [(1, 1), (2, 1), (1, 2), (3.4, 7.2), (40, 12)])
def test_beta_ters_cdf_tutarli(a, b):
    for u in (0.01, 0.3, 0.5, 0.9, 0.999):
        assert haydut.beta_cdf(haydut.beta_ters(u, a, b), a, b) == pytest.approx(u, abs=1e-9)
    assert haydut.beta_cdf(0.5, 2, 1) == pytest.approx(0.25)  # F(x) = x²
    assert haydut.beta_cdf(0.5, 1, 2) == pytest.approx(0.75)  # F(x) = 1 - (1 - x)²
    assert haydut.beta_ters(0.37, 1, 1) == pytest.approx(0.37)


def test_odul_komsulara_gore_sira(db):
    secim(db, GUN, "usgs", "soru", "A", "v1")
    olcum(db, "v1", GUN, 100, 50.0)
    assert haydut.oduller(db, GUN + dt.timedelta(days=10)) == []  # tek video: kıyas yok, ödül yok
    secim(db, GUN + dt.timedelta(days=1), "eurostat", "olcek", "B", "v2")
    olcum(db, "v2", GUN + dt.timedelta(days=1), 300, 40.0)
    secim(db, GUN + dt.timedelta(days=30), "usgs", "olcek", "C", "v3")  # v1'e 30 gün uzak: komşu değil
    olcum(db, "v3", GUN + dt.timedelta(days=30), 10_000, 90.0)
    od = {o["video_id"]: o["odul"] for o in haydut.oduller(db, GUN + dt.timedelta(days=35))}
    assert od == {"v1": 0.3, "v2": 0.7}  # v1: izlenme sırası 0, yüzde sırası 1 → 0,3; v3'ün komşusu yok
    assert haydut.oduller(db, GUN + dt.timedelta(days=60)) == []  # 56 günden eski ödül posteriora girmez


def test_veri_yokken_secim_degismez(db):
    konu, kalip, log = haydut.sec(db, GUN, ["eurostat", "usgs"], ["olcek", "soru"], random.Random(1))
    assert log["degisti"] == [] and log["odul_sayisi"] == 0
    assert (konu, kalip) == (log["veri_olmadan"]["konu"], log["veri_olmadan"]["kalip"])
    assert all(k["a"] == k["b"] == 1 and k["theta"] == k["u"] for k in log["konu"].values())


def test_analitik_secimi_degistirir_ve_loga_yazar(db):
    # 40 gün, kancalar dönüşümlü: "olcek" hep komşularını geçer, "soru" hep geride kalır → posterior olcek'e kayar
    for i in range(40):
        g = GUN - dt.timedelta(days=i + 5)
        kalip, deger = ("olcek", 1000) if i % 2 else ("soru", 10)
        secim(db, g, "usgs", kalip, f"v{i}", f"v{i}")
        olcum(db, f"v{i}", g, deger, deger / 20)
    degisen = 0
    for tohum in range(40):
        _, kalip, log = haydut.sec(db, GUN, ["usgs"], ["olcek", "soru"], random.Random(tohum))
        assert kalip == "olcek"
        assert log["kalip"]["olcek"]["n"] == 20
        degisen += log["degisti"] == ["kalip"]
        assert (log["veri_olmadan"]["kalip"] != kalip) == (log["degisti"] == ["kalip"])
    assert 5 < degisen < 35  # veri olmadan yarı yarıya "soru" seçilirdi


class Sahte:
    """googleapiclient zincirini taklit eder: servis.kaynak().metod(**k).execute()."""

    def __init__(self, yanitlar):
        self.yanitlar, self.cagrilar = yanitlar, []

    def __getattr__(self, kaynak):
        def metodlar():
            sahte = self

            class M:
                def __getattr__(self, metod):
                    def cagir(**k):
                        sahte.cagrilar.append((kaynak, metod, k))
                        y = sahte.yanitlar[(kaynak, metod)]
                        return type("I", (), {"execute": lambda _s, num_retries=0: y(k) if callable(y) else y})()

                    return cagir

            return M()

        return metodlar


def test_eslestir_ve_olc(db):
    secim(db, GUN, "usgs", "soru", "Earthquakes in Chile  Over the Past Year")
    secim(db, GUN + dt.timedelta(days=1), "eurostat", "olcek", "Emigration in Europe")
    secim(db, GUN + dt.timedelta(days=2), "usgs", "soru", "Yüklenmemiş")
    yt = Sahte(
        {
            ("channels", "list"): {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU1"}}}]},
            ("playlistItems", "list"): {
                "items": [
                    {"snippet": {"resourceId": {"videoId": "vB"}, "title": "emigration in europe"}},
                    {"snippet": {"resourceId": {"videoId": "vA"}, "title": "Earthquakes in Chile Over the Past Year"}},
                    {"snippet": {"resourceId": {"videoId": "vX"}, "title": "Elle yüklenmiş başka video"}},
                ]
            },
            ("videos", "list"): {
                "items": [
                    {
                        "id": "vA",
                        "status": {"privacyStatus": "public"},
                        "snippet": {"publishedAt": "2026-10-06T14:00:00Z"},
                    },
                    {
                        "id": "vB",
                        "status": {"privacyStatus": "private"},
                        "snippet": {"publishedAt": "2026-10-07T14:00:00Z"},
                    },
                ]
            },
        }
    )
    ya = Sahte({("reports", "query"): {"rows": [[1200, 1000, 61.5, 18.2, 3]]}})
    assert analitik.topla(db, GUN + dt.timedelta(days=4), yt, ya) == {
        "eslesen": [("2026-10-05", "vA"), ("2026-10-06", "vB")],
        "olculen": [],  # vA'nın penceresi 10-06…10-08, gecikmeyle en erken 10-11
    }
    sonuc = analitik.topla(db, dt.date(2026, 10, 11), yt, ya)
    assert sonuc == {"eslesen": [], "olculen": ["vA"]}  # vB private: ölçülmez
    sorgu = ya.cagrilar[-1][2]
    assert (sorgu["startDate"], sorgu["endDate"], sorgu["filters"]) == ("2026-10-06", "2026-10-08", "video==vA")
    assert db.execute("SELECT engaged_views, ort_izlenme_yuzde FROM olcumler").fetchall() == [(1000, 61.5)]
    assert analitik.topla(db, dt.date(2026, 10, 12), yt, ya)["olculen"] == []  # bir kez ölçülür


def test_gecmis_tasima_tekrarsiz(db, tmp_path):
    yol = tmp_path / "g.jsonl"
    satirlar = [
        {"tarih": "2026-10-02", "durum": "tamam", "anahtar": "eurostat:x", "hash": "h1", "kalip": "duygusal",
         "sablon": "koroplet", "baslik": "B1", "yayin_ani": "2026-10-03T14:00:00+00:00", "video_id": None},
        {"tarih": "2026-10-03", "durum": "hata", "hata": "x"},
    ]  # fmt: skip
    yol.write_text("\n".join(json.dumps(s) for s in satirlar) + "\n", encoding="utf-8")
    assert durum.gecmisi_doldur(db, yol) == 1
    assert durum.gecmisi_doldur(db, yol) == 0
    assert db.execute("SELECT konu, kalip, baslik FROM secimler").fetchall() == [("eurostat", "duygusal", "B1")]


def test_haftalik_rapor(db, tmp_path, monkeypatch):
    monkeypatch.setattr(rapor, "RAPORLAR", tmp_path)
    (tmp_path / "gunluk.jsonl").write_text(
        json.dumps({"tarih": "2026-10-05", "mod": "teslim", "durum": "tamam", "kaynak_hatalari": ["usgs: zaman aşımı"]})
        + "\n"
        + json.dumps({"tarih": "2026-10-06", "mod": "teslim", "durum": "hata", "hata": "RuntimeError: x"})
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "dokunus.jsonl").write_text(json.dumps({"tarih": "2026-10-07", "dk": 3, "ne": "Plan B yükleme"}) + "\n")
    secim(db, GUN, "usgs", "soru", "Deprem", "vA")
    log = {"degisti": ["kalip"]}
    db.execute("UPDATE secimler SET gunluk = ?", (json.dumps(log),))
    olcum(db, "vA", GUN - dt.timedelta(days=5), 500, 70.0)
    kanal = {"views": 1500, "engaged_views": 1200, "abone_net": 4, "abone_toplam": 4, "video_sayisi": 1}
    metin = rapor.olustur(db, 2026, 41, kanal, {**kanal, "views": 1500})
    assert "hafta 41 (2026-10-05 – 2026-10-11)" in metin
    assert "Üretilen **1** · düşen **1** · kanala ulaşan **1**" in metin
    assert "usgs: zaman aşımı" in metin and "RuntimeError: x" in metin
    assert "1.500 / 1.200.000 görüntüleme" in metin
    assert "2026-10-05 (kalip)" in metin
    assert "Toplam 3 dk" in metin
    assert "Analitik alınamadı: YetkiHatasi" in rapor.olustur(db, 2026, 41, None, None, "YetkiHatasi: x")


def test_rapor_yalniz_pazartesi_gecen_hafta(db, monkeypatch, tmp_path):
    yazilan = []
    monkeypatch.setattr(rapor, "dosya", lambda y, h: tmp_path / f"{y}-{h}.md")
    monkeypatch.setattr(rapor, "yaz", lambda db, y, h, *a: yazilan.append((y, h)) or tmp_path / "x")
    monkeypatch.setattr(gunluk, "KOK", tmp_path)
    gunluk.rapor_adimi(db, dt.date(2026, 10, 6), None, None, {}, [])  # salı
    gunluk.rapor_adimi(db, dt.date(2026, 10, 5), None, None, {}, [])  # pazartesi → hafta 40
    assert yazilan == [(2026, 40)]


def test_alarm(tmp_path, monkeypatch):
    monkeypatch.setattr(gunluk, "ALARM", tmp_path / "alarm.md")
    assert "gh secret set YT_TOKEN_JSON" in gunluk._hata(YetkiHatasi("token yenilenemedi (invalid_grant?)"))
    assert "secret" not in gunluk._hata(RuntimeError("x"))
    gunluk.alarm_yaz(GUN, ["a", "b"])
    assert (tmp_path / "alarm.md").read_text(encoding="utf-8") == "Günlük koşu 2026-10-05:\n\na\n\n---\n\nb\n"
    gunluk.alarm_yaz(GUN, [])
    assert not (tmp_path / "alarm.md").exists()


def test_gun_zaten_uretildiyse_kosu_atlanir(db, tmp_path, monkeypatch):
    bugun = dt.datetime.now(dt.UTC).date()
    monkeypatch.setattr(gunluk.durum, "baglan", lambda: db)
    monkeypatch.setattr(gunluk, "RAPOR", tmp_path / "gunluk.jsonl")
    monkeypatch.setattr(gunluk, "analitik_adimi", lambda *a: pytest.fail("ikinci koşu üretime girdi"))
    assert not durum.bugun_secildi_mi(db, bugun)
    secim(db, bugun, "usgs", "soru", "A")
    assert durum.bugun_secildi_mi(db, bugun)
    gunluk.main()
    assert not (tmp_path / "gunluk.jsonl").exists()
