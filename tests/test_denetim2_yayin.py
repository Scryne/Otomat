"""2026-10-13 ikinci denetimin orkestrasyon, yayın ve rapor bulguları: her test düzeltmeden önceki hatalı davranışı
reddeder."""

import datetime as dt
import http.client
import io
import json
import sqlite3
from datetime import UTC

import pytest

from otomat import analitik, durum, gunluk, kanal, portfoy, rapor
from otomat.veri import Kaynak, OlguPaketi
from otomat.yayin import buffer, ceviri, youtube


def _secim(db, tarih: str, yayin_ani: str, video_id: str | None, anahtar: str | None = None) -> None:
    db.execute(
        "INSERT INTO secimler VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
        (tarih, anahtar or f"k:{tarih}", f"h{tarih}", "k", "kalip", "sablon", f"B {tarih}", yayin_ani, video_id),
    )


class _Yanit(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


# --- Buffer: gönderiden sonra her hata belirsizdir ---------------------------------------------------------------


def _buffer_ortami(monkeypatch, yanitlar):
    """urlopen sırayla `yanitlar`ı döner (bayt) ya da fırlatır (istisna)."""
    monkeypatch.setattr(buffer, "anahtar", lambda: "k")
    monkeypatch.setattr(buffer, "kanal_id", lambda: "kanal")
    monkeypatch.setattr(buffer.time, "sleep", lambda _: None)
    sira = iter(yanitlar)

    def urlopen(istek, timeout=0):
        y = next(sira)
        if isinstance(y, BaseException):
            raise y
        return _Yanit(y)

    monkeypatch.setattr(buffer.urllib.request, "urlopen", urlopen)


ACILDI = json.dumps({"data": {"createPost": {"post": {"id": "p1"}}}}).encode()


@pytest.mark.parametrize(
    "yoklama",
    [
        http.client.RemoteDisconnected("kapandı"),  # okurken kopan bağlantı: eskiden ham istisna kaçıyordu
        b"{yarim",  # yarım JSON
        json.dumps({"data": {"post": None}}).encode(),  # post: null -> TypeError
    ],
)
def test_buffer_gonderi_acildiktan_sonraki_her_hata_belirsizdir(monkeypatch, yoklama):
    """Gönderi açıldıktan sonra kaçan ham istisna bir_video'da "gönderi açılmadı" sayılıyor, hikâye harcanmıyor,
    sonraki koşunun hazır üretimi aynı videoyu ikinci kez Buffer'a gönderiyordu (kanalda iki kopya)."""
    _buffer_ortami(monkeypatch, [ACILDI, *([yoklama] * buffer.DENEME)])
    with pytest.raises(buffer.GonderiBelirsiz, match="p1"):
        buffer.gonder("https://x/v.mp4", "B", "A")


def test_buffer_createpost_yaniti_kopunca_belirsiz_reddedince_kesin(monkeypatch):
    _buffer_ortami(monkeypatch, [http.client.RemoteDisconnected("kapandı")])
    with pytest.raises(buffer.GonderiBelirsiz):
        buffer.gonder("https://x/v.mp4", "B", "A")
    _buffer_ortami(monkeypatch, [json.dumps({"errors": [{"message": "bad"}]}).encode()])
    with pytest.raises(buffer.BufferHatasi) as e:
        buffer.gonder("https://x/v.mp4", "B", "A")
    assert not isinstance(e.value, buffer.GonderiBelirsiz)


def test_buffer_okuma_kopan_baglantida_yeniden_dener(monkeypatch):
    _buffer_ortami(monkeypatch, [http.client.IncompleteRead(b""), json.dumps({"data": {"x": 1}}).encode()])
    assert buffer.sorgu("query { x }") == {"x": 1}


# --- Analitik: yetim Buffer videosu planlanır, ölçüm çift satırda düşmez ---------------------------------------------


def test_baslikla_eslesen_yetim_video_pistte_planlanir(tmp_path, monkeypatch):
    """GonderiBelirsiz'den sonra Buffer videoyu yine de yüklediyse analitik onu başlıkla bulup slotu dolu sayıyordu;
    video private ve plansız kalıyor, slot sessizce kayboluyordu."""
    db = durum.baglan(tmp_path / "d.db")
    _secim(db, "2026-10-16", "2026-10-16T14:00:00+00:00", None)
    monkeypatch.setattr(analitik, "servisler", lambda: ("yt", "ya"))
    monkeypatch.setattr(analitik, "topla", lambda db, b, yt, ya: {"eslesen": [("2026-10-16", "yetim")], "olculen": []})
    monkeypatch.setenv("OTOMAT_YAYIN", "buffer")
    kayit = {}
    assert gunluk.analitik_adimi(db, dt.date(2026, 10, 14), kayit, []) == ("yt", "ya")
    assert db.execute("SELECT video_id, yayin_ani FROM planlanamayan").fetchall() == [
        ("yetim", "2026-10-16T14:00:00+00:00")
    ]
    monkeypatch.setenv("OTOMAT_YAYIN", "teslim")  # Plan B'de elle yüklenen videoyu Scryne planlar
    db.execute("DELETE FROM planlanamayan")
    gunluk.analitik_adimi(db, dt.date(2026, 10, 14), {}, [])
    assert not durum.planlanamayan_var(db)


def test_analitik_toplama_duserse_servisler_yine_doner(tmp_path, monkeypatch):
    """Analytics 5xx'te pist denetimi ve çeviri onarımı da atlanıyordu (bakım koşusunun tek işi onlardı)."""
    db = durum.baglan(tmp_path / "d.db")
    monkeypatch.setattr(analitik, "servisler", lambda: ("yt", "ya"))

    def dus(*a):
        raise RuntimeError("Analytics 500")

    monkeypatch.setattr(analitik, "topla", dus)
    alarmlar = []
    assert gunluk.analitik_adimi(db, dt.date(2026, 10, 14), {}, alarmlar) == ("yt", "ya")
    assert "Analytics 500" in alarmlar[0]


def test_olcum_ayni_video_iki_secimde_olunca_dusmez(tmp_path, monkeypatch):
    db = durum.baglan(tmp_path / "d.db")
    _secim(db, "2026-10-01", "2026-10-01T14:00:00+00:00", "v1")
    _secim(db, "2026-10-02", "2026-10-02T14:00:00+00:00", "v1")  # hazır üretim aynı videoyu iki slota yazdı
    monkeypatch.setattr(
        analitik, "durumlar", lambda yt, v: {"v1": {"public": True, "yayin_gunu": dt.date(2026, 10, 1)}}
    )
    olcum = {
        "views": 5,
        "engaged_views": 4,
        "ort_izlenme_yuzde": 50.0,
        "ort_izlenme_sn": 10.0,
        "abone": 0,
        "bos": False,
    }
    monkeypatch.setattr(analitik, "pencere", lambda ya, v, g: olcum)
    assert analitik.olc(db, None, None, dt.date(2026, 10, 20)) == ["v1"]


# --- Pist denetimi -----------------------------------------------------------------------------------------------


class _Yt:
    def __init__(self, durumlar, dusen=()):
        self.durumlar, self.dusen, self.guncellenen = durumlar, set(dusen), []

    def videos(self):
        return self

    def list(self, part, id):
        self._y = {"items": [{"id": v, "status": self.durumlar[v]} for v in id.split(",") if v in self.durumlar]}
        return self

    def update(self, part, body):
        if body["id"] in self.dusen:
            raise RuntimeError(f"invalidTitle: {body['id']}")
        self.guncellenen.append(body["id"])
        self._y = {}
        return self

    def execute(self, **_):
        return self._y


def test_pist_denetimi_video_basina_cozer_kayip_ve_kalici_hatali_takilmaz(tmp_path, monkeypatch):
    """Kanalda olmayan video `planlanamayan`da kalıp her cron'u bakım koşusuna çeviriyordu; bir videonun kalıcı hatası
    döngüyü düşürüp önceden onarılanları ertesi koşuda yeniden onartıyordu (altyazılar çift)."""
    db = durum.baglan(tmp_path / "d.db")
    simdi = dt.datetime(2026, 10, 14, 6, tzinfo=UTC)
    for gun, v in [("2026-10-15", "a_bozuk"), ("2026-10-16", "b_iyi"), ("2026-10-17", "c_silinmis")]:
        _secim(db, gun, f"{gun}T14:00:00+00:00", v)
        durum.planlanamadi(db, v, dt.datetime.fromisoformat(f"{gun}T14:00:00+00:00"))
    yt = _Yt({"a_bozuk": {"privacyStatus": "private"}, "b_iyi": {"privacyStatus": "private"}}, dusen={"a_bozuk"})
    monkeypatch.setattr(gunluk, "uretim_dosyalari", lambda ad: [])
    for kosu in range(gunluk.PLAN_DENEME):
        kayit, alarmlar = {}, []
        gunluk.pist_denetimi(db, yt, simdi, kayit, alarmlar)
        kalan = {v for (v,) in db.execute("SELECT video_id FROM planlanamayan")}
        if kosu == 0:
            assert kayit["pist"]["onarilan"] == ["b_iyi"] and kayit["pist"]["kayip"] == ["c_silinmis"]
            assert kalan == {"a_bozuk"} and any("invalidTitle" in a for a in alarmlar)
    assert kalan == set() and any("denetimden çıktı" in a for a in alarmlar)
    assert yt.guncellenen == ["b_iyi"]  # iyi video bir kez onarıldı


def test_eski_veritabani_deneme_sutununu_alir(tmp_path):
    yol = tmp_path / "eski.db"
    eski = sqlite3.connect(yol)
    eski.execute("CREATE TABLE planlanamayan (video_id TEXT PRIMARY KEY, yayin_ani TEXT NOT NULL)")
    eski.execute("INSERT INTO planlanamayan VALUES ('v', '2026-10-15T14:00:00+00:00')")
    eski.commit()
    eski.close()
    db = durum.baglan(yol)
    assert durum.planlama_denemesi(db, "v") == 1
    durum.planlanamadi(db, "w", None)  # sütun sayısı değişti: VALUES (?, ?) düşerdi


# --- Çeviri onarımı --------------------------------------------------------------------------------------------


def _ceviri_klasoru(tmp_path, ad, anahtar):
    k = tmp_path / ad
    k.mkdir(parents=True)
    (k / "meta.json").write_text(json.dumps({"paket": {"anahtar": anahtar}}), encoding="utf-8")
    (k / "yerel.json").write_text(json.dumps({"yerel": {}, "atlanan": ["es"]}), encoding="utf-8")
    (k / "en.srt").write_text("1", encoding="utf-8")  # sahneli üretim; kart biçiminde srt hiç yok
    (k / "es.srt").write_text("1", encoding="utf-8")
    return k


def test_ceviri_onarimi_en_yakin_yayini_once_alir_altyazi_duserse_yine_kaydeder(tmp_path, monkeypatch):
    db = durum.baglan(tmp_path / "d.db")
    yakin = dt.datetime.now(UTC) + dt.timedelta(hours=6)
    uzak = yakin + dt.timedelta(days=2)
    _secim(db, uzak.date().isoformat(), uzak.isoformat(), "v_uzak", "wiki:Uzak")
    _secim(db, yakin.date().isoformat(), yakin.isoformat(), "v_yakin", "wiki:Yakin")
    # bu koşunun (uzak) klasörü önce gelir; eskiden hakkı o alıyordu
    klasorler = [_ceviri_klasoru(tmp_path, "bu", "wiki:Uzak"), _ceviri_klasoru(tmp_path, "onceki", "wiki:Yakin")]
    monkeypatch.setattr(gunluk, "uretim_dosyalari", lambda ad: [k / ad for k in klasorler])
    monkeypatch.setattr(gunluk, "hazirla", lambda d: {"yerel": {"es": {"title": "T", "description": "D"}}})
    yerellesen = []
    monkeypatch.setattr(youtube, "yerellestir", lambda v, y, yt=None: yerellesen.append(v))

    def altyazi_dus(*a, **k):
        raise RuntimeError("quotaExceeded")

    monkeypatch.setattr(youtube, "altyazi_ekle", altyazi_dus)
    kayit, alarmlar = {}, []
    gunluk.ceviri_onarimi(db, object(), kayit, alarmlar)
    assert yerellesen == ["v_yakin"] and kayit["ceviri_onarimi"] == [{"video_id": "v_yakin", "diller": ["es"]}]
    # yerelleştirme yazıldı: altyazı düştü diye bir daha çevrilmez (yeniden çeviri kota, yeniden altyazı çift iz)
    assert {v for (v,) in db.execute("SELECT video_id FROM ceviri_onarim")} == {"v_yakin"}
    assert any("quotaExceeded" in a for a in alarmlar)


def test_ceviri_bekliyor_pist_dolu_gunde_bakim_kosusu_acar(tmp_path):
    db = durum.baglan(tmp_path / "d.db")
    simdi = dt.datetime(2026, 10, 14, 6, tzinfo=UTC)
    rapor_yolu = tmp_path / "gunluk.jsonl"
    satirlar = [
        {"video_id": "v1", "yayin_ani": "2026-10-15T14:00:00+00:00", "ceviri_atlanan": ["es"]},
        {"video_id": "v2", "yayin_ani": "2026-10-13T14:00:00+00:00", "ceviri_atlanan": ["es"]},  # yayında
    ]
    rapor_yolu.write_text("\n".join(map(json.dumps, satirlar)) + "\n{yarım satır\n", encoding="utf-8")
    assert durum.ceviri_bekliyor(db, rapor_yolu, simdi)
    db.execute("INSERT INTO ceviri_onarim VALUES ('v1', '2026-10-14')")
    assert not durum.ceviri_bekliyor(db, rapor_yolu, simdi)
    assert len(durum.jsonl_oku(rapor_yolu)) == 2  # bozuk satır atlanır, koşuyu düşürmez


# --- Rapor ve portföy ------------------------------------------------------------------------------------------


def test_analitiksiz_rapor_gunde_bir_kez_yeniden_denenir(tmp_path, monkeypatch):
    monkeypatch.setattr(rapor, "RAPORLAR", tmp_path)
    bas, _ = rapor.hafta_araligi(2026, 41)
    (tmp_path / "gunluk.jsonl").write_text(json.dumps({"tarih": bas.isoformat(), "durum": "tamam"}) + "\n", "utf-8")
    rapor.dosya(2026, 41).write_text("rapor", encoding="utf-8")
    sayilar = {"analitik_hatasi": "YetkiHatasi", "yazildi": "2026-10-14"}
    rapor.dosya(2026, 41).with_suffix(".json").write_text(json.dumps(sayilar), encoding="utf-8")
    assert rapor.bekleyen(dt.date(2026, 10, 14)) is None  # bugün denendi: her cron'da tam koşu açmasın
    assert rapor.bekleyen(dt.date(2026, 10, 15)) == (2026, 41)


def test_uretimsiz_kosu_satiri_raporu_dusurmez(tmp_path, monkeypatch):
    monkeypatch.setattr(rapor, "RAPORLAR", tmp_path)
    satirlar = [{"tarih": "2026-10-12", "mod": "buffer", "durum": "bos"}, {"tarih": "2026-10-13", "mod": "buffer"}]
    (tmp_path / "gunluk.jsonl").write_text("\n".join(map(json.dumps, satirlar)), encoding="utf-8")
    metin = rapor.olustur(durum.baglan(tmp_path / "d.db"), 2026, 42, None, None)
    assert "düşen **1**" in metin  # durumsuz satır KeyError veriyordu; "boş" düşen sayılmaz


def test_k14_penceresi_ilk_public_videodan_baslar(monkeypatch):
    monkeypatch.setattr(portfoy, "ilk_public", lambda k: dt.date(2026, 10, 10))
    assert rapor.k14_araligi(dt.date(2026, 10, 18)) == (dt.date(2026, 10, 10), dt.date(2026, 10, 18))
    assert rapor.k14_araligi(dt.date(2027, 1, 3)) == (dt.date(2026, 10, 10), dt.date(2026, 12, 4))  # 56 gün
    assert rapor.k14_araligi(dt.date(2026, 10, 4)) is None  # sayaç başlamadı
    monkeypatch.setattr(portfoy, "ilk_public", lambda k: None)
    assert rapor.k14_araligi(dt.date(2026, 10, 18)) is None


def test_portfoy_slotu_bir_kez_sayar_planli_ilk_videoyu_eksi_gun_yazmaz():
    kanallar = [kanal.yukle("earth")]
    ozet = {"id": "earth", "ad": "Inkwell Oddities", "ilk_public": dt.date(2026, 10, 15), "son_56_gun": None,
            "hafta": None, "gunluk_neuron": {}, "gunluk_api": {}, "uretilen": 0, "kanala_cikan": 0, "dusen_hikaye": 0,
            "kota": 0, "hata": 0, "neuron": 0, "buffer_istek": 0, "buffer_30_gun": 0, "havuz": None,
            "analitik_hatasi": None, "rapor_var": True, "kayit_var": True}  # fmt: skip
    metin = portfoy.olustur(2026, 41, [ozet], None)
    assert "ilk yayın 2026-10-15 (planlı)" in metin and "/56 gün" not in metin
    assert kanallar


# --- Çeviri kapısı, YouTube, marka -------------------------------------------------------------------------------


def test_ceviri_kapisi_cevrilmemis_ciktiyi_reddeder(monkeypatch):
    monkeypatch.setattr(ceviri.kanal, "aktif", lambda: kanal.yukle("earth"))
    cumleler = ["The tank burst in 1919.", "Molasses filled the street."]

    def aynen(istem, sema, tohum):
        return {"title": "The Great Flood", "description": "Sweet disaster.", "captions": list(cumleler)}

    monkeypatch.setattr(ceviri, "_uret", aynen)
    assert ceviri._cevir("es", "The Great Flood", "Sweet disaster.", cumleler) is None

    def cevrilmis(istem, sema, tohum):
        return {"title": "La gran inundación", "description": "Desastre dulce.",
                "captions": ["El tanque reventó en 1919.", "La melaza llenó la calle."]}  # fmt: skip

    monkeypatch.setattr(ceviri, "_uret", cevrilmis)
    assert ceviri._cevir("es", "The Great Flood", "Sweet disaster.", cumleler)["title"] == "La gran inundación"


def test_api_yuklemesi_gecmis_ani_planlamaz_hemen_yayinlar(tmp_path, monkeypatch):
    govdeler = []

    class _Istek:
        def next_chunk(self, num_retries=0):
            return None, {"id": "yeni"}

    class _Servis:
        def videos(self):
            return self

        def insert(self, part, body, media_body):
            govdeler.append(body)
            return _Istek()

    monkeypatch.setattr("googleapiclient.http.MediaFileUpload", lambda *a, **k: None)
    gecmis = dt.datetime.now(UTC) - dt.timedelta(hours=1)
    assert youtube.yukle(tmp_path / "v.mp4", "B", "A", [], gecmis, yt=_Servis()) == "yeni"
    assert govdeler[0]["status"]["privacyStatus"] == "public" and "publishAt" not in govdeler[0]["status"]


def test_marka_ad_kilidinde_yalniz_yerellestirme_denenir(monkeypatch):
    from googleapiclient.errors import HttpError

    from otomat.yayin import marka

    class _Cevap(dict):
        status = 429
        reason = "rateLimitExceeded"

    class _Kanal:
        def channels(self):
            return self

        def update(self, part, body):
            raise HttpError(_Cevap(), b"{}")

    oge = {"id": "UC1", "snippet": {"title": "Yeni Ad"}}
    m = {"aciklama": {"en": "EN"}}
    assert marka.yerel_adi_yaz(_Kanal(), oge, m) is False


# --- Hikâye seçimi ---------------------------------------------------------------------------------------------


def _hikaye_paketi(ad: str) -> OlguPaketi:
    return OlguPaketi(kol="tuhaf", tur="tuhaf", anahtar=f"wiki:{ad}", konu="k", olgular={},
                      gorsel={"sablon": "illustrasyon", "baslik": ad},
                      kaynak=Kaynak("Wikipedia", "https://en.wikipedia.org/wiki/X", "CC BY-SA 4.0", "t"))  # fmt: skip


def test_yarim_uretim_secimden_bagimsiz_once_surdurulur(tmp_path, monkeypatch):
    """Yarım üretim yalnız aynı hikâye yeniden seçilirse sürüyordu: senaryonun ve görsellerin kotası boşa gidiyordu."""
    from otomat.hikaye import kabul
    from otomat.hikaye import uretim as h_uretim

    db = durum.baglan(tmp_path / "d.db")
    paketler = [_hikaye_paketi(a) for a in ("Bir", "Iki", "Uc")]
    yarim = tmp_path / "calisma" / "onceki" / "kosu" / "2026-10-13" / "wiki_Iki"
    yarim.mkdir(parents=True)
    kayit_ = {"anahtar": "wiki:Iki", "hash": paketler[1].hash, "kalip": "detay", "senaryo": {}}
    (yarim / h_uretim.SENARYO).write_text(json.dumps(kayit_), encoding="utf-8")
    monkeypatch.setattr(gunluk, "KOK", tmp_path)
    monkeypatch.setattr(gunluk, "_K", kanal.yukle("earth"))
    monkeypatch.setattr(gunluk, "HIKAYE", True)
    monkeypatch.setattr(gunluk, "sec", lambda *a: pytest.fail("yarım üretim varken haydut seçmemeli"))
    monkeypatch.setattr(kabul, "denetle", lambda *a: [])
    uretilen = []
    monkeypatch.setattr(h_uretim, "uret", lambda p, kalip, *a: uretilen.append((p.anahtar, kalip)) or {"baslik": "B"})
    paket, kalip, *_ = gunluk.hikaye_uret(paketler, db, dt.date(2026, 10, 14), {})
    assert (paket.anahtar, kalip) == ("wiki:Iki", "detay") and uretilen == [("wiki:Iki", "detay")]


def test_cloudflare_kesintisi_hikayeyi_yakmaz_kosuyu_dusurmez(tmp_path, monkeypatch):
    from otomat.hikaye import cf, kabul
    from otomat.hikaye import uretim as h_uretim

    db = durum.baglan(tmp_path / "d.db")
    paketler = [_hikaye_paketi(a) for a in ("Bir", "Iki")]
    sira = iter(paketler)
    monkeypatch.setattr(gunluk, "KOK", tmp_path)
    monkeypatch.setattr(gunluk, "sec", lambda *a: (next(sira), "detay", "illustrasyon", {}))
    monkeypatch.setattr(kabul, "denetle", lambda *a: [])

    def uret(p, *a):
        if p.anahtar == "wiki:Bir":
            raise cf.CFHatasi("görsel üretilemedi (502)")
        return {"baslik": "B"}

    monkeypatch.setattr(h_uretim, "uret", uret)
    kayit = {}
    paket, *_ = gunluk.hikaye_uret(paketler, db, dt.date(2026, 10, 14), kayit)
    assert paket.anahtar == "wiki:Iki" and "Cloudflare" in kayit["dusen_hikayeler"][0]["sorunlar"][0]
    assert durum.taze_mi(db, paketler[0], dt.date(2026, 10, 14), 3650)  # kesinti hikâyeyi havuzdan yakmadı


# --- main(), hikâye modunda uçtan uca ---------------------------------------------------------------------------


def test_main_hikaye_modunda_pisti_doldurur_kaydi_eksiksiz_yazar(tmp_path, monkeypatch):
    """Bütün main() testleri HIKAYE=False koşuyordu: canlı kanalların akışı (havuz, marka, çeviri onarımı, neuron
    alanları) hiç sınanmıyordu."""
    from otomat.hikaye import cf
    from otomat.hikaye import kaynaklar as hk
    from otomat.yayin import marka

    db = durum.baglan(tmp_path / "d.db")
    monkeypatch.setenv("OTOMAT_YAYIN", "buffer")
    monkeypatch.setattr(gunluk.durum, "baglan", lambda: db)
    monkeypatch.setattr(gunluk, "RAPOR", tmp_path / "gunluk.jsonl")
    monkeypatch.setattr(gunluk, "ALARM", tmp_path / "alarm.md")
    monkeypatch.setattr(gunluk.rapor, "RAPORLAR", tmp_path)
    monkeypatch.setattr(gunluk, "HIKAYE", True)
    monkeypatch.setattr(gunluk, "KOK", tmp_path)
    monkeypatch.setattr(gunluk, "buffer_istekleri", lambda _: 0)
    monkeypatch.setattr(gunluk, "analitik_adimi", lambda *a: (object(), object()))
    monkeypatch.setattr(gunluk, "pist_denetimi", lambda *a: None)
    monkeypatch.setattr(marka, "kontrol", lambda yt: "tamam")
    paketler = [_hikaye_paketi(f"H{i}") for i in range(30)]
    monkeypatch.setattr(hk, "topla", lambda: (paketler, []))
    sira = iter(paketler)

    def hikaye_uret(pk, db_, gun, kayit):
        p = next(sira)
        dizin = tmp_path / "u" / p.anahtar.replace(":", "_")
        dizin.mkdir(parents=True)
        cf.NEURON["toplam"] = 1800.0
        meta = {"baslik": f"Başlık {p.anahtar}", "secim": {"kaynak": {"senaryo": "m"}}, "sure_sn": 30.0,
                "neuron": 1800, "zaman_sn": {"senaryo": 1.0}}  # fmt: skip
        return p, "detay", "illustrasyon", {"degisti": [], "odul_sayisi": 0}, dizin, meta

    monkeypatch.setattr(gunluk, "hikaye_uret", hikaye_uret)

    def hazirla(dizin):
        cf.NEURON["toplam"] += 250  # çeviri kotası
        return {"yerel": {"de": {}}, "atlanan": ["es"]}

    monkeypatch.setattr(gunluk, "hazirla", hazirla)
    yayinlanan = []
    monkeypatch.setattr(gunluk, "yayinla_buffer", lambda d, an, ad, al, db=None: yayinlanan.append(an) or f"v{ad}")
    onarim = []
    monkeypatch.setattr(gunluk, "ceviri_onarimi", lambda db_, yt, kayit, al: onarim.append(kayit["video_id"]))

    gunluk.main()
    satirlar = durum.jsonl_oku(tmp_path / "gunluk.jsonl")
    assert len(satirlar) == gunluk.EN_COK == len(yayinlanan) and onarim == [satirlar[-1]["video_id"]]
    for s in satirlar:
        assert s["durum"] == "tamam" and s["marka"] == "tamam" and s["havuz_kalan"] == 30
        assert s["neuron"] == 1800 + 250 and s["ceviri_neuron"] == 250 and s["ceviri_atlanan"] == ["es"]
        assert s["diller"] == ["de"] and s["video_id"].startswith("v")
    assert not (tmp_path / "alarm.md").exists()
