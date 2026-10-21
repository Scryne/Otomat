"""Film kanalı haftalık raporu: ağsız, sahte YouTube Data ve Analytics istemcisiyle."""

import datetime as dt
import json

import pytest

from otomat import portfoy
from otomat.film import rapor, yukle

GERCEK_KIMLIK = yukle.kimlik  # conftest testte gerçek kimliği kapatır; burada ağsız token okuması denenir


def _video(vid, baslik, yayin, sure, durum="public", aciklama=""):
    return {
        "id": vid,
        "snippet": {"title": baslik, "publishedAt": f"{yayin}T19:00:00Z", "description": aciklama},
        "status": {"privacyStatus": durum},
        "contentDetails": {"duration": sure},
    }


VIDEOLAR = [
    _video("film0000001", "What If You Joined the Klondike Gold Rush in 1897?", "2026-10-24", "PT10M38S"),
    _video("kesit000001", "You Just Caught Klondicitis", "2026-10-26", "PT49S",
           aciklama="You Just Caught Klondicitis\n\nFull film: https://www.youtube.com/watch?v=film0000001\n\nSources"),
    _video("film0000002", "Titanic Was Only Her Second Disaster at Sea", "2026-10-31", "PT7M43S"),
    _video("planli00001", "What If You Were a Lowell Mill Girl in 1836?", "2026-11-07", "PT8M27S", durum="private"),
    _video("kisa0000001", "Bağlantısız kısa video", "2026-10-25", "PT40S"),
]  # fmt: skip


class _Istek:
    def __init__(self, sonuc):
        self.sonuc = sonuc

    def execute(self, **_):
        return self.sonuc


class _SahteYT:
    def channels(self):
        return self

    def playlistItems(self):  # noqa: N802 — Google istemcisinin adı
        return self

    def videos(self):
        return self

    def list(self, part, **k):
        if "playlistId" in k:
            return _Istek({"items": [{"contentDetails": {"videoId": v["id"]}} for v in VIDEOLAR]})
        if "id" in k:
            return _Istek({"items": [v for v in VIDEOLAR if v["id"] in k["id"].split(",")]})
        return _Istek({"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU"}},
                                  "statistics": {"subscriberCount": "12"}}]})  # fmt: skip


class _SahteYA:
    def __init__(self):
        self.sorgular = []

    def reports(self):
        return self

    def query(self, **k):
        self.sorgular.append(k)
        boyut, filtre, m = k.get("dimensions"), k.get("filters", ""), k["metrics"]
        if boyut == "elapsedVideoTimeRatio":
            return _Istek({"rows": [[i / 100, 1 - 2 * i / 100] for i in range(1, 101)]})
        if boyut == "insightTrafficSourceType":
            return _Istek({"rows": [["RELATED_VIDEO", 300], ["YT_SEARCH", 100], ["YENI_KAYNAK", 0]]})
        if boyut == "video":
            return _Istek({"rows": [["kesit000001", 900, 300, 85.0]]})
        if m == "estimatedMinutesWatched":
            return _Istek({"rows": [[1200]]})
        if m == "views":
            return _Istek({"rows": [[5000 if "film0000001" in filtre else 800]]})
        if filtre:
            return _Istek({"rows": [[2000, 6000, 190, 30.5, 7]]})
        return _Istek({"rows": [[3000, 9000, 9, 2]]})


def test_sure_ve_bicim():
    assert rapor.sure_sn("PT10M38S") == 638 and rapor.sure_sn("PT49S") == 49 and rapor.sure_sn("PT1H2M") == 3720
    assert rapor.bicim("What If You Joined…") == "What if you" and rapor.bicim("Titanic Was…") == "anlatı"
    with pytest.raises(ValueError):
        rapor.sure_sn("8 dakika")


def test_ayir_kesiti_filmine_baglar_planli_ve_baglantisizi_atlar():
    filmler, kesitler = rapor.ayir(VIDEOLAR, dt.date(2026, 11, 1))
    assert [f["id"] for f in filmler] == ["film0000001", "film0000002"]
    assert [(k["id"], k["film_id"]) for k in kesitler] == [("kesit000001", "film0000001")]
    filmler, kesitler = rapor.ayir(VIDEOLAR, dt.date(2026, 10, 25))  # hafta sonundan sonra yayınlanan sayılmaz
    assert [f["id"] for f in filmler] == ["film0000001"] and kesitler == []


def test_kalan_orani_30_saniyeye_en_yakin_nokta():
    egri = [[i / 100, 1 - i / 100] for i in range(1, 101)]
    assert rapor.kalan_orani(egri, 600) == pytest.approx(0.95)  # 30/600 = 0,05
    assert rapor.kalan_orani([], 600) is None and rapor.kalan_orani(egri, 25) is None


def test_bekleyen_ilk_haftadan_ve_gecikmeden_sonra(tmp_path, monkeypatch):
    monkeypatch.setattr(rapor, "RAPORLAR", tmp_path)
    assert rapor.bekleyen(dt.date(2026, 10, 27)) is None  # H43 pazar biter, Analytics 3 gün
    assert rapor.bekleyen(dt.date(2026, 10, 28)) == (2026, 43)  # H42 ilk haftadan önce: beklenmez
    (tmp_path / "2026-H43.md").write_text("r", encoding="utf-8")
    assert rapor.bekleyen(dt.date(2026, 10, 28)) is None
    assert rapor.bekleyen(dt.date(2026, 11, 4)) == (2026, 44)


def test_rapor_uctan_uca_sahte_istemciyle(tmp_path, monkeypatch):
    monkeypatch.setattr(rapor, "RAPORLAR", tmp_path)
    ya = _SahteYA()
    yol = rapor.yaz(2026, 44, _SahteYT(), ya, bugun=dt.date(2026, 11, 10))
    metin = yol.read_text(encoding="utf-8")
    assert "Bu hafta 3.000 görüntüleme, 150,0 saat izlenme, abone net +7" in metin
    assert "YPP: uzun videoların son 365 günde izlenme saati 20,0 / 4.000 · abone 12 / 1.000" in metin
    satir = next(s for s in metin.splitlines() if "film0000001" in s and "Klondike" in s)
    assert "| What if you | 2026-10-24 | 7/7 | 2.000 | 100,0 | 3:10 / 10:38 | %30 | %90 | +7 | 5.000 |" in satir
    assert "| anlatı | 2026-10-31 | 2/7 |" in metin  # pencere haftanın sonuna kırpılır
    assert "| You Just Caught Klondicitis (`kesit000001`) | What If You Joined" in metin and "| %33 | %85 |" in metin
    assert "- önerilen video: 300 (%75)" in metin and "YENI_KAYNAK" not in metin  # 0'lı kaynak yazılmaz
    assert "Lowell" not in metin and "Bağlantısız" not in metin
    pencere = [q for q in ya.sorgular if q.get("filters") == "video==film0000002" and q["metrics"].startswith("views,")]
    assert pencere[0]["startDate"] == "2026-10-31" and pencere[0]["endDate"] == "2026-11-01"
    sayilar = json.loads(yol.with_suffix(".json").read_text(encoding="utf-8"))
    assert sayilar["abone_toplam"] == 12 and len(sayilar["filmler"]) == 2


def test_public_film_yoksa_rapor_yine_yazilir(tmp_path, monkeypatch):
    monkeypatch.setattr(rapor, "RAPORLAR", tmp_path)
    metin = rapor.yaz(2026, 43, _SahteYT(), _SahteYA(), bugun=dt.date(2026, 10, 23)).read_text(encoding="utf-8")
    assert "Bu hafta sonuna kadar public film yok." in metin and "Public kesit yok." in metin


def test_film_tokeni_ortam_degiskeninden(monkeypatch, tmp_path):
    from google.oauth2.credentials import Credentials

    monkeypatch.setattr(yukle, "TOKEN", tmp_path / "yok.json")
    bilgi = {
        "token": "t",
        "refresh_token": "r",
        "client_id": "c",
        "client_secret": "s",
        "expiry": "2999-01-01T00:00:00Z",
    }
    monkeypatch.setenv(yukle.TOKEN_DEGISKENI, json.dumps(bilgi))
    monkeypatch.setattr(Credentials, "valid", property(lambda _: True))
    assert GERCEK_KIMLIK().refresh_token == "r"


def test_portfoy_film_bolumu():
    film = {"hafta": {"views": 3000, "saat": 150.0, "abone_net": 7}, "abone_toplam": 12, "filmler": [{}, {}],
            "ypp_saat": 20.0}  # fmt: skip
    metin = portfoy.olustur(2026, 44, [], None, film)
    assert "## Film kanalı (One Ticket Back)" in metin
    assert "bu hafta 3.000 görüntüleme, 150.0 saat izlenme, abone net +7 (toplam 12); 2 public film" in metin
    assert "## Film kanalı" not in portfoy.olustur(2026, 44, [], None)
