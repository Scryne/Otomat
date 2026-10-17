"""2026-10-15 üçüncü denetim: her test düzeltmeden önceki hatalı davranışı reddeder."""

import datetime as dt
import json
from datetime import UTC

import httplib2
import pytest
from googleapiclient.errors import HttpError
from PIL import Image

from otomat import durum, gunluk
from otomat.yayin import youtube


def _http_hatasi(neden: str, durum_kodu: int = 403) -> HttpError:
    govde = {"error": {"code": durum_kodu, "message": "m", "errors": [{"reason": neden, "message": "m"}]}}
    return HttpError(httplib2.Response({"status": durum_kodu}), json.dumps(govde).encode())


def test_kota_hatasi_nedenden_taninir_alarm_satiri_nedeni_tasir():
    """10-14 alarmı: ham HttpError metni 200 karakterde kesildi, nedeni ("quotaExceeded") görünmüyordu."""
    assert youtube.kota_hatasi(_http_hatasi("quotaExceeded"))
    assert not youtube.kota_hatasi(_http_hatasi("forbidden"))
    assert not youtube.kota_hatasi(RuntimeError("quotaExceeded"))
    assert youtube.kisa_hata(_http_hatasi("quotaExceeded")) == "HttpError 403 quotaExceeded"


def test_kotaya_takilan_altyazi_kuyruga_girer_kalanlar_denenmez(tmp_path, monkeypatch):
    """10-14 Ganesha (CgRlUjXj9F8): fr/pt kotaya takıldı; alarm çaldı ama hiçbir koşu yeniden denemiyordu."""
    from otomat.yayin import buffer

    db = durum.baglan(tmp_path / "d.db")
    (tmp_path / "meta.json").write_text(json.dumps({"baslik": "B", "aciklama": "A", "etiketler": []}), "utf-8")
    for dil in ("de", "en", "es", "fr", "pt"):
        (tmp_path / f"{dil}.srt").write_text("1", encoding="utf-8")
    monkeypatch.setattr(buffer, "medya_koy", lambda *a: "u")
    monkeypatch.setattr(buffer, "gonder", lambda *a: "vid")
    monkeypatch.setattr(buffer, "medya_kaldir", lambda *a: None)
    monkeypatch.setattr(youtube, "servis", lambda: object())
    monkeypatch.setattr(youtube, "duzenle", lambda *a, **k: None)
    denenen = []

    def altyazi(vid, dil, metin, yt):
        denenen.append(dil)
        if dil == "fr":
            raise _http_hatasi("quotaExceeded")

    monkeypatch.setattr(youtube, "altyazi_ekle", altyazi)
    alarmlar = []
    assert gunluk.yayinla_buffer(tmp_path, None, "2026-10-16", alarmlar, db=db) == "vid"
    assert denenen == ["de", "en", "es", "fr"]  # pt denenmedi: aynı gün o da düşerdi
    assert sorted(d for (d,) in db.execute("SELECT dil FROM altyazi_eksik")) == ["fr", "pt"]
    assert alarmlar == []  # kuyrukta: onarım vazgeçerse kendisi alarm çalar
    assert durum.altyazi_bekliyor(db)


class _Yt:
    def __init__(self, izler):
        self.izler = izler

    def captions(self):
        return self

    def list(self, part, videoId):
        self._y = {
            "items": [{"snippet": {"language": d, "trackKind": "standard"}} for d in self.izler.get(videoId, [])]
        }
        return self

    def execute(self, **_):
        return self._y


def _kuyruk(tmp_path, monkeypatch):
    db = durum.baglan(tmp_path / "d.db")
    db.execute(
        "INSERT INTO secimler VALUES ('2026-10-16', 'wiki:G', 'h', 'k', 'kalip', 's', 'B', ?, 'vid', NULL)",
        ("2026-10-16T14:00:00+00:00",),
    )
    durum.altyazi_eksik(db, "vid", ["fr", "pt"])
    klasor = tmp_path / "onceki" / "kosu" / "2026-10-16" / "wiki_G"
    klasor.mkdir(parents=True)
    (klasor / "meta.json").write_text(json.dumps({"paket": {"anahtar": "wiki:G"}}), encoding="utf-8")
    (klasor / "fr.srt").write_text("1\nfr", encoding="utf-8")
    (klasor / "pt.srt").write_text("1\npt", encoding="utf-8")
    monkeypatch.setattr(gunluk, "uretim_dosyalari", lambda ad: [klasor / ad])
    return db


def test_altyazi_onarimi_eksigi_tamamlar_var_olani_yeniden_acmaz(tmp_path, monkeypatch):
    db = _kuyruk(tmp_path, monkeypatch)
    yuklenen = []
    monkeypatch.setattr(youtube, "altyazi_ekle", lambda v, d, m, yt=None: yuklenen.append((v, d, m)))
    kayit, alarmlar = {}, []
    gunluk.altyazi_onarimi(db, _Yt({"vid": ["en", "fr"]}), kayit, alarmlar)  # fr yüklenmiş, yanıtı kaybolmuş
    assert yuklenen == [("vid", "pt", "1\npt")] and alarmlar == []
    assert kayit["altyazi_onarimi"] == [{"video_id": "vid", "dil": "pt"}] and not durum.altyazi_bekliyor(db)


def test_altyazi_onarimi_kotada_saymaz_kalici_hatada_vazgecer(tmp_path, monkeypatch):
    db = _kuyruk(tmp_path, monkeypatch)

    def kota(*a, **k):
        raise _http_hatasi("quotaExceeded")

    monkeypatch.setattr(youtube, "altyazi_ekle", kota)
    for _ in range(5):
        gunluk.altyazi_onarimi(db, _Yt({}), {}, [])
    assert db.execute("SELECT max(deneme) FROM altyazi_eksik").fetchone()[0] == 0  # kota hikâyenin suçu değil

    def yasak(*a, **k):
        raise _http_hatasi("forbidden")

    monkeypatch.setattr(youtube, "altyazi_ekle", yasak)
    alarmlar = []
    for _ in range(gunluk.ALTYAZI_DENEME):
        gunluk.altyazi_onarimi(db, _Yt({}), {}, alarmlar)
    assert not durum.altyazi_bekliyor(db) and len(alarmlar) == 1 and "forbidden" in alarmlar[0]


def test_geri_cekilen_videonun_altyazisi_beklemez(tmp_path):
    db = durum.baglan(tmp_path / "d.db")
    durum.altyazi_eksik(db, "v", ["fr"])
    assert durum.altyazi_bekliyor(db)
    durum.geri_cek(db, ["v"], dt.datetime.now(UTC).date(), "kalite")
    assert not durum.altyazi_bekliyor(db)


# --- kart (K-25) ---


def _kart(**degis):
    from test_hikaye_kart import IYI

    from otomat.hikaye import kart

    d = {**IYI, **degis}
    return kart.Kart(d["title"], d["hook"], list(d["sentences"]), d["image"], d["mood"])


def test_kart_isarete_bitisik_yazi_ayrilmaz():
    """Hobby Lobby kartı: "[[Hobby Lobby]]'s" ekrana "Lobby 's" diye çıkıyordu."""
    from otomat.hikaye import kart

    k = kart.kelimeler(['[[Hobby Lobby]]\'s [[25]]-foot wave, said "[[cursed]]" ([[tank]]).'])
    assert [w for w, _ in k] == ["Hobby", "Lobby's", "25-foot", "wave,", "said", '"cursed"', "(tank)."]
    assert dict(k)["Lobby's"] == 0 and dict(k)["(tank)."] == 0 and dict(k)["wave,"] == -1


@pytest.mark.parametrize(
    "cumle",
    ["A [[big [[tank]] burst]] open in Boston's North End.", "A tank [[burst]] b]] open [[c in Boston's North End."],
)
def test_kart_bozuk_isaret_kod_kapisinda_kalir(cumle):
    """İç içe/sırası bozuk işaret ekrana parantezle çıkıyordu; açıklama düz metni gördüğü için kabul ediliyordu."""
    from test_hikaye_kart import IYI, KAYNAK

    from otomat.hikaye import kart

    k = _kart(sentences=[cumle, *IYI["sentences"][1:]])
    assert any("broken [[ ]] marks" in r for _, r in kart.kod_kontrolu(k, KAYNAK))


def test_kart_onarimi_cumle_ekler_siler_bozuk_ogeyi_atlar():
    """Cümle sayısı onarılamıyordu (yalnız var olan satır değişirdi); boş metin kabulde render'dan sonra düşüyordu."""
    from test_hikaye_kart import IYI

    from otomat.hikaye import kart

    k = _kart(sentences=IYI["sentences"][:2])
    kart.onarim_uygula(k, [{"line": 4, "text": IYI["sentences"][2]}, {"line": 0, "text": "[[Boston]] flood"},
                           {"line": "x"}, "bozuk", {"line": 3, "text": ""}])  # fmt: skip
    assert k.cumleler == [IYI["sentences"][0], IYI["sentences"][2]] and k.baslik == "Boston flood"
    kart.onarim_uygula(k, None)  # şemasız yanıt koşuyu düşürmez


def test_kart_ekrana_sigmayan_paragraf_kapida_kalir():
    """54 uzun kelimelik paragraf 40 puntoda da görsele taşıyordu; ne kapı ne kabul bakıyordu."""
    from test_hikaye_kart import KAYNAK

    from otomat.hikaye import kart

    uzun = "Extraordinarily misunderstood archaeological consequences overwhelmed internationally"
    k = _kart(sentences=[f"{uzun} [[{w}]] {uzun}." for w in ("Boston", "molasses", "residents")] + [f"{uzun}."] * 2)
    assert not kart.yerlesim(kart.duz(k.kanca), k.cumleler)[-1]
    assert any("too long to fit" in r for _, r in kart.kod_kontrolu(k, KAYNAK))


@pytest.mark.parametrize(
    "lisans,serbest",
    [("CC BY-SA 4.0", True), ("CC BY 2.0", True), ("CC BY-NC-SA 4.0", False), ("CC BY-ND 2.0", False),
     ("CC BY-NC 3.0", False), ("Public domain", True), ("CC0", True), ("Attribution-NonCommercial", False)],
)  # fmt: skip
def test_kart_lisans_suzgeci_nc_nd_gecmez(lisans, serbest):
    from otomat.hikaye import kart

    assert (bool(kart.LISANS.match(lisans)) and not kart.SERBEST_DEGIL.search(lisans)) is serbest


def test_kart_yazar_restoratoru_korur_yasak_karakter_tasimaz():
    from otomat.hikaye import kart

    assert kart._yazar({"Artist": {"value": "Unknown photographer; restored by Adam Cuerden"}}) == (
        "restored by Adam Cuerden"
    )
    assert kart._yazar({"Artist": {"value": "Unknown authorUnknown author"}}) == ""
    assert "<" not in kart._yazar({"Artist": {"value": "Jo &lt;jo@x&gt;"}})


def test_kart_saydam_png_siyaha_donmez(tmp_path, monkeypatch):
    from PIL import Image

    from otomat.hikaye import kart

    saydam = tmp_path / "s.png"
    Image.new("RGBA", (500, 500), (0, 0, 0, 0)).save(saydam)

    class _Yanit:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return saydam.read_bytes()

    monkeypatch.setattr(kart.urllib.request, "urlopen", lambda *a, **k: _Yanit())
    kart._indir("https://u/s.png", tmp_path / "g.jpg")
    assert Image.open(tmp_path / "g.jpg").getpixel((250, 250)) > (240, 240, 240)


def test_kart_ai_gorseli_yatay_istenir(tmp_path, monkeypatch):
    """Dikey 768×1344 kare bandın %70'ini dışarıda bırakıyordu: 10-17 kartında masadaki tabletler kırpılmıştı."""
    from test_hikaye_uctan_uca import _paket

    from otomat.hikaye import cf, kart, panel, yazi

    boyutlar = []

    def gorsel(istem, yol, tohum, boyut=cf.GORSEL_BOYUT, **_):
        boyutlar.append(boyut)
        Image.new("RGB", boyut, "gray").save(yol)

    monkeypatch.setattr(kart, "wiki_gorseli", lambda b: None)
    monkeypatch.setattr(cf, "gorsel", gorsel)
    monkeypatch.setattr(panel, "panelli", lambda y: False)
    monkeypatch.setattr(yazi, "oku", lambda y: [])
    kart.gorsel_al(_paket(), _kart(), tmp_path, 1)
    assert boyutlar == [(1344, 768)]


def test_ceviri_kartta_bos_altyazi_listesi_dili_dusurmez(monkeypatch):
    from otomat.yayin import ceviri

    monkeypatch.setattr(ceviri, "_uret", lambda *a: {"title": "Título", "description": "Descripción", "captions": [""]})
    assert ceviri._cevir("es", "Title", "Description", [])["title"] == "Título"


def test_hazir_uretim_eski_bicimin_videosunu_almaz(tmp_path, monkeypatch):
    """K-25: Earth karta geçti; artifact'taki yayınlanmamış sahneli video kart deneyine karışıyordu."""
    meta = {"bicim": "kart", "paket": {"anahtar": "a", "hash": "h"}}
    yol = tmp_path / "k" / "meta.json"
    yol.parent.mkdir()
    yol.write_text(json.dumps(meta), encoding="utf-8")
    monkeypatch.setattr(gunluk, "uretim_dosyalari", lambda ad: [yol])
    monkeypatch.setattr(gunluk.durum, "taze_mi", lambda *a: True)

    class P:
        anahtar, hash = "a", "h"

    monkeypatch.setattr("otomat.hikaye.kabul.denetle", lambda y: pytest.fail("biçimi tutmayan üretim denetlendi"))
    assert gunluk._K.bicim == "sahne" and gunluk.hazir_uretim([P()], None, dt.date(2026, 10, 15)) is None


@pytest.mark.parametrize(
    "cumle,isaretli",
    [
        ("The article speculated it was a secret experiment from the nearby lab.", True),  # Montauk kartı, 10-19
        ("According to Wikipedia, the flood smelled of molasses for decades.", True),
        ("A local newspaper article called it a monster, and the article spread fast.", False),
        ("The story spread fast, and a piece of the tank landed blocks away.", False),
    ],
)
def test_kaynaga_gonderme_kapida_kalir(cumle, isaretli):
    """Montauk kartı "The article speculated..." dedi; makale hiç anılmamıştı (Wikipedia'daki gazete yazısı)."""
    from test_hikaye_kart import IYI

    from otomat.hikaye import kart, senaryo

    k = _kart(sentences=[*IYI["sentences"][:3], cumle])
    assert any("source document" in r or "never introduced" in r for _, r in kart.kod_kontrolu(k, "")) is isaretli
    assert bool(senaryo.kaynak_gondermesi(["Title", cumle])) is isaretli
