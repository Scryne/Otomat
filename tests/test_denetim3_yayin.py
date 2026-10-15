"""2026-10-15 üçüncü denetimin orkestrasyon, yayın, rapor ve hikâye hattı bulguları: her test düzeltmeden önceki
hatalı davranışı reddeder."""

import datetime as dt
import json
import subprocess
import threading
import time
from datetime import UTC

import pytest

from otomat import durum, gunluk, portfoy, rapor
from otomat.hikaye import cf, kabul, kaynaklar, senaryo, uretim
from otomat.veri import Kaynak, OlguPaketi
from otomat.yayin import buffer, youtube


def _paket(anahtar="wiki:X") -> OlguPaketi:
    return OlguPaketi(
        anahtar=anahtar, tur="tuhaf", kol="k", konu="k", olgular={},
        kaynak=Kaynak("Wikipedia", "https://w", "CC BY-SA 4.0", "2026-10-15"), gorsel={"baslik": "X"},
        etiketler=["e"],
    )  # fmt: skip


@pytest.fixture
def bir_video_ortami(tmp_path, monkeypatch):
    db = durum.baglan(tmp_path / "d.db")
    dizin = tmp_path / "u"
    dizin.mkdir()
    meta = {"baslik": "Başlık", "secim": {"kaynak": {}}, "sure_sn": 8.0, "neuron": 0, "zaman_sn": {}}
    (dizin / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    secim_logu = {"degisti": [], "odul_sayisi": 0}
    monkeypatch.setattr(gunluk, "HIKAYE", True)
    monkeypatch.setattr(gunluk, "hikaye_uret", lambda *a: (_paket(), "kalip", "s", secim_logu, dizin, meta))
    monkeypatch.setattr(gunluk, "hazirla", lambda d: {"yerel": {}, "atlanan": []})
    return db


def test_kosu_buffer_beklerken_kesilirse_hikaye_harcanir_secim_videosuz_yazilir(bir_video_ortami, monkeypatch):
    """33 dk adım sınırı Buffer beklemesinin ortasında: kayıt yoktu, sonraki koşu aynı videoyu yeniden gönderirdi."""
    db = bir_video_ortami

    def kesik(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(gunluk, "yayinla_buffer", kesik)
    an = dt.datetime(2026, 10, 18, 14, tzinfo=UTC)
    with pytest.raises(KeyboardInterrupt):
        gunluk.bir_video([], db, an.date(), an, "buffer", {}, [])
    assert not durum.taze_mi(db, _paket(), an.date(), 3650)  # hazır üretim ikinci kez göndermez
    assert db.execute("SELECT video_id FROM secimler").fetchall() == [(None,)]  # analitik başlıkla eşleştirir


def test_buffer_id_verince_kayit_hemen_yazilir_planlama_onarim_bekler(bir_video_ortami, monkeypatch):
    db = bir_video_ortami

    def yuklenip_kesik(dizin, an, ad, alarmlar, db=None, yuklendi=None):
        yuklendi("vid")
        raise KeyboardInterrupt  # planlama (duzenle) yapılamadan

    monkeypatch.setattr(gunluk, "yayinla_buffer", yuklenip_kesik)
    an = dt.datetime(2026, 10, 18, 14, tzinfo=UTC)
    with pytest.raises(KeyboardInterrupt):
        gunluk.bir_video([], db, an.date(), an, "buffer", {}, [])
    assert db.execute("SELECT video_id FROM secimler").fetchall() == [("vid",)]
    assert durum.planlanamayan_var(db)  # pist denetimi planlar


def test_yayinla_buffer_planlayinca_erken_kaydin_onarim_isareti_kalkar(tmp_path, monkeypatch):
    db = durum.baglan(tmp_path / "d.db")
    (tmp_path / "meta.json").write_text(json.dumps({"baslik": "B", "aciklama": "A", "etiketler": []}), "utf-8")
    monkeypatch.setattr(buffer, "medya_koy", lambda *a: "u")
    monkeypatch.setattr(buffer, "gonder", lambda *a: "vid")
    monkeypatch.setattr(buffer, "medya_kaldir", lambda *a: None)
    monkeypatch.setattr(youtube, "servis", lambda: object())
    monkeypatch.setattr(youtube, "duzenle", lambda *a, **k: None)
    gunluk.yayinla_buffer(tmp_path, None, "g", [], db=db, yuklendi=lambda v: durum.planlanamadi(db, v, None))
    assert not durum.planlanamayan_var(db)


def test_medya_konamazsa_da_siteden_kaldirilir(tmp_path, monkeypatch):
    """Pages beklemesi push'tan sonra düşünce video public repoda kalıyordu (medya_koy try'ın dışındaydı)."""
    (tmp_path / "meta.json").write_text(json.dumps({"baslik": "B", "aciklama": "A", "etiketler": []}), "utf-8")
    kaldirilan = []

    def pages_gelmedi(*a):
        raise buffer.BufferHatasi("Pages 600 sn'de yayınlamadı")

    monkeypatch.setattr(buffer, "medya_koy", pages_gelmedi)
    monkeypatch.setattr(buffer, "medya_kaldir", kaldirilan.append)
    with pytest.raises(buffer.BufferHatasi):
        gunluk.yayinla_buffer(tmp_path, None, "2026-10-18", [])
    assert kaldirilan == ["veri-earth-2026-10-18.mp4"]


def test_ikinci_video_sure_dolduysa_baslamaz(tmp_path, monkeypatch):
    """İkinci video 33 dk adım sınırını aşıp yayının ortasında kesilebiliyordu."""
    from test_denetim_yayin import _ortam

    db = durum.baglan(tmp_path / "d.db")
    uretilen = []

    def uret(paketler, db_, gun, an, mod, kayit, alarmlar):
        uretilen.append(gun)
        kayit.update(durum="tamam", video_id=f"v{gun}")
        durum.secim_kaydet(db_, gun, _paket(str(gun)), "k", "s", "B", an, f"v{gun}", None)

    _ortam(tmp_path, monkeypatch, db, uret)
    monkeypatch.setattr(gunluk, "BASLANGIC", time.monotonic() - gunluk.IKINCI_VIDEO_SN - 1)
    gunluk.main()
    assert len(uretilen) == 1


def test_bakim_kosusu_alarmi_kapatmaz_tam_kosu_kapatir(tmp_path, monkeypatch):
    """Bakım koşusu havuz/kimlik/Buffer sınırına bakmadan "temiz" sayılıp açık alarmı kapatıyordu."""
    monkeypatch.setattr(gunluk, "ALARM", tmp_path / "alarm.md")
    gunluk.alarm_yaz(dt.date(2026, 10, 15), [])
    assert not (tmp_path / "temiz").exists()
    gunluk.alarm_yaz(dt.date(2026, 10, 15), [], tam=True)
    assert (tmp_path / "temiz").exists()
    gunluk.alarm_yaz(dt.date(2026, 10, 15), ["sorun"], tam=True)
    assert not (tmp_path / "temiz").exists() and (tmp_path / "alarm.md").exists()


def test_yayin_modu_degiskeni_yoksa_alarm(tmp_path, monkeypatch):
    from test_denetim_yayin import _ortam

    db = durum.baglan(tmp_path / "d.db")
    _ortam(tmp_path, monkeypatch, db, lambda *a: a[5].update(durum="tamam", video_id=None))
    monkeypatch.setenv("OTOMAT_YAYIN", "teslim")
    monkeypatch.setenv("OTOMAT_YAYIN_TANIMLI", "0")
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    gunluk.main()
    assert "Yayın modu değişkeni yok" in (tmp_path / "alarm.md").read_text(encoding="utf-8")


def test_ceviri_onarimi_klasoru_olmayan_videodan_vazgecer(tmp_path, monkeypatch):
    """Artifact'ı pencereden çıkmış video her cron'u yayınına kadar boşuna bakım koşusuna çeviriyordu."""
    db = durum.baglan(tmp_path / "d.db")
    ileri = (dt.datetime.now(UTC) + dt.timedelta(days=2)).replace(microsecond=0)
    satir = {"tarih": ileri.date().isoformat(), "durum": "tamam", "video_id": "v", "yayin_ani": ileri.isoformat(),
             "diller": [], "ceviri_atlanan": ["es"]}  # fmt: skip
    (tmp_path / "gunluk.jsonl").write_text(json.dumps(satir) + "\n", encoding="utf-8")
    monkeypatch.setattr(gunluk, "RAPOR", tmp_path / "gunluk.jsonl")
    monkeypatch.setattr(gunluk, "uretim_dosyalari", lambda ad: [])
    alarmlar = []
    for _ in range(gunluk.CEVIRI_DENEME):
        assert durum.ceviri_bekliyor(db, gunluk.RAPOR, dt.datetime.now(UTC))
        gunluk.ceviri_onarimi(db, object(), {}, alarmlar)
    assert not durum.ceviri_bekliyor(db, gunluk.RAPOR, dt.datetime.now(UTC))
    assert len(alarmlar) == 1 and "vazgeçildi" in alarmlar[0]


# --- Buffer ---


def test_buffer_yoklamasinda_tek_hickirik_gonderiyi_belirsiz_yapmaz(monkeypatch):
    """GraphQL tek bir `errors` yanıtı iyi giden gönderiyi "belirsiz" yapıp hikâyeyi harcıyordu."""
    gitti = {"post": {"status": "sent", "externalLink": "https://youtube.com/shorts/abcdefghijk"}}
    yanitlar = iter([buffer.BufferHatasi("Buffer API: [{'message': 'internal'}]"), gitti])

    def sorgu(metin, degiskenler=None, tekrar=True):
        if "createPost" in metin:
            return {"createPost": {"post": {"id": "p1"}}}
        y = next(yanitlar)
        if isinstance(y, Exception):
            raise y
        return y

    monkeypatch.setattr(buffer, "sorgu", sorgu)
    monkeypatch.setattr(buffer, "kanal_id", lambda: "k")
    monkeypatch.setattr(buffer, "YOKLAMA_SN", 0)
    assert buffer.gonder("https://u", "B", "A") == "abcdefghijk"


def _git(*arg, cwd=None):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *arg], cwd=cwd, check=True,
                   capture_output=True)  # fmt: skip


def test_medya_kaldirilinca_site_tarihcesi_tek_commite_iner(tmp_path, monkeypatch):
    """Silinen her video public otomat-site tarihçesinde kalıyordu (10 günde 294 MB, geri çekilenler dahil)."""
    uzak = tmp_path / "site.git"
    _git("init", "--bare", "-b", "main", str(uzak))
    yerel = tmp_path / "y"
    _git("clone", str(uzak), str(yerel))
    (yerel / "index.html").write_text("site", encoding="utf-8")
    (yerel / "media").mkdir()
    for ad in ("a.mp4", "b.mp4"):
        (yerel / "media" / ad).write_bytes(b"v")
        _git("add", "-A", cwd=yerel)
        _git("commit", "-m", ad, cwd=yerel)
    _git("push", "origin", "HEAD:main", cwd=yerel)
    monkeypatch.setattr(buffer, "SITE_GIT", uzak.as_uri())
    buffer.medya_kaldir("a.mp4")  # b.mp4 hâlâ yayında (öbür kanalın gönderisi): sıkıştırma yok
    say = subprocess.run(["git", "rev-list", "--count", "main"], cwd=uzak, capture_output=True, text=True).stdout
    assert int(say) == 3
    buffer.medya_kaldir("b.mp4")
    say = subprocess.run(["git", "rev-list", "--count", "main"], cwd=uzak, capture_output=True, text=True).stdout
    agac = subprocess.run(["git", "ls-tree", "-r", "--name-only", "main"], cwd=uzak, capture_output=True, text=True)
    assert int(say) == 1 and agac.stdout.split() == ["index.html"]


# --- YouTube ---


def test_youtube_metninde_acili_parantez_temizlenir():
    """Commons yazar alanından gelen < > videos.update'i 400'le düşürüp planlamayı kaybettiriyordu."""
    govde, _ = youtube._govde("A <b> title", "Image: Jo <jo@x>", [], None, {"es": {"title": "<t>", "description": "d"}})
    assert "<" not in json.dumps(govde) and ">" not in json.dumps(govde)


def test_youtube_birim_maliyeti():
    assert youtube._maliyet("youtube.captions.insert") == 400
    assert youtube._maliyet("youtube.captions.list") == 50
    assert youtube._maliyet("youtube.videos.update") == 50
    assert youtube._maliyet("youtube.channels.list") == 1


def test_portfoy_olculen_birimi_kullanir_kartta_altyazi_saymaz():
    """Tahmin her videoya beş altyazı izi sayıyordu: altyazısız kart (K-25) için 2.050 yerine ~50."""
    assert portfoy._api_birimi({"video_id": "v", "yt_birim": 73}) == 73
    assert portfoy._api_birimi({"video_id": "v", "sure_sn": 8.0, "diller": ["es", "de"]}) == portfoy.API_VIDEO


# --- rapor ---


def test_rapor_konu_haydudun_kolu_kota_dusen_sayilmaz(tmp_path, monkeypatch):
    monkeypatch.setattr(rapor, "RAPORLAR", tmp_path)
    db = durum.baglan(tmp_path / "d.db")
    db.execute(
        "INSERT INTO secimler VALUES ('2026-10-14', 'wiki:X', 'h', 'religion', 'k', 's', 'B', "
        "'2026-10-14T14:00:00+00:00', 'v', NULL)"
    )
    satirlar = [{"tarih": "2026-10-14", "mod": "buffer", "durum": "kota"},
                {"tarih": "2026-10-14", "mod": "buffer", "durum": "tamam", "anahtar": "wiki:X", "baslik": "B",
                 "kalip": "k", "video_id": "v"}]  # fmt: skip
    (tmp_path / "gunluk.jsonl").write_text("\n".join(json.dumps(s) for s in satirlar) + "\n", encoding="utf-8")
    metin = rapor.olustur(db, 2026, 42, None, None)
    assert "düşen **0**" in metin and "| religion |" in metin


# --- hikâye hattı ---


def test_sahne_cizimi_ilk_hatada_kuyrugu_iptal_eder(tmp_path, monkeypatch):
    """Sırayla result() beklerken boşalan işçiler kuyruktan yeni sahne alıyordu (~470 neuron boşa)."""
    cizilen, kilit = [], threading.Lock()

    def gorsel(istem, yol, tohum, **_):
        with kilit:
            cizilen.append(istem)
        if istem == "s1":
            raise cf.FiltreHatasi("3030")
        time.sleep(0.2 if istem == "s0" else 0.05)
        return yol

    monkeypatch.setattr(cf, "gorsel", gorsel)
    monkeypatch.setattr(uretim, "PARALEL", 2)
    with pytest.raises(cf.FiltreHatasi):
        uretim.sahneleri_ciz([f"s{i}" for i in range(8)], tmp_path, 0)
    assert len(cizilen) < 5


def test_ad_kapisi_unicode_unvan_ve_aksan():
    kaynak = "Juan Pérez met Dr. Grayson near the Tree of Ténéré."
    assert senaryo.sayi_ad_kapisi("Later he met Pérez there.", kaynak) == []
    assert senaryo.sayi_ad_kapisi("Later he met Gómez there.", kaynak) == ["name not in source: Gómez"]
    assert senaryo.sayi_ad_kapisi("He hired Dr. Smithers.", kaynak) == ["name not in source: Smithers"]
    assert senaryo.sayi_ad_kapisi("It stood alone at Tenere for years.", kaynak) == []


def test_hakaret_bitisik_kufuru_de_yakalar():
    assert kaynaklar.HAKARET.search("what a load of bullshit")
    assert kaynaklar.HAKARET.search("motherfucking") and not kaynaklar.HAKARET.search("Fagan")


def test_yeni_duzenlenmis_makale_bu_kosuda_anlatilmaz(monkeypatch):
    """Senaryo, kapı ve hakem aynı canlı metne bakıyor: dakikalar önceki vandalizm her denetimden geçerdi."""
    simdi = dt.datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    monkeypatch.setattr(kaynaklar, "_wiki", lambda p: {"query": {"pages": [
        {"extract": "x" * 500, "revisions": [{"timestamp": simdi}]}]}})  # fmt: skip
    with pytest.raises(kaynaklar.KaynakTaze):
        kaynaklar.metin(_paket())
    eski = (dt.datetime.now(UTC) - dt.timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    monkeypatch.setattr(kaynaklar, "_wiki", lambda p: {"query": {"pages": [
        {"extract": "x" * 500, "revisions": [{"timestamp": eski}]}]}})  # fmt: skip
    assert kaynaklar.metin(_paket()) == "x" * 500


def test_uzun_tire_tek_basina_kelime_olmaz():
    assert cf.duzelt("The tank burst — and molasses flowed.") == "The tank burst, and molasses flowed."
    assert "-" not in cf.duzelt("a—b").split()


def test_kabul_bos_cumle_listesinde_cokmez(tmp_path):
    (tmp_path / "meta.json").write_text(json.dumps({"baslik": "Yeterince uzun başlık", "cumleler": []}), "utf-8")
    assert "cümleler eksik ya da 3 kelimeden kısa" in kabul.denetle(tmp_path / "meta.json")


def test_surdurulen_senaryo_yeni_istemleri_kaydeder(tmp_path, monkeypatch):
    """Stil değişince sürdürme kareleri siliyor ama senaryo.json'u güncellemiyordu: her sürdürme yeni stille
    çizilmiş kareleri de yeniden siliyordu."""
    from test_denetim2_hikaye import _sc

    sc = _sc()
    paket = _paket("ezop:Fox")
    istemler = uretim.istemleri_kur("YENI STIL", sc)
    monkeypatch.setattr(uretim, "bicim_imzasi", lambda tur, k: "imza")
    d = {"anahtar": paket.anahtar, "hash": paket.hash, "bicim": "imza", "kalip": "ders", "senaryo": uretim.asdict(sc),
         "istemler": ["eski"] * len(istemler)}  # fmt: skip
    (tmp_path / uretim.SENARYO).write_text(json.dumps(d), encoding="utf-8")
    monkeypatch.setattr(uretim, "istemleri_kur", lambda stil, sc_: istemler)
    uretim.senaryo_al(paket, "ders", tmp_path)
    assert json.loads((tmp_path / uretim.SENARYO).read_text(encoding="utf-8"))["istemler"] == istemler
