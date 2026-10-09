"""Hikâye motoru: havuz süzgeçleri, kod kapıları, kelime zamanlaması, kenar kırpma (Cloudflare'e gitmeden)."""

import datetime as dt
import itertools

import numpy as np
import pytest
from PIL import Image

from otomat import kanal
from otomat.hikaye import kaynaklar, senaryo, uretim
from otomat.ses import Parca


@pytest.fixture
def kanal_sec(monkeypatch):
    def sec(kimlik):
        monkeypatch.setenv("OTOMAT_KANAL", kimlik)
        kanal._aktif.cache_clear()

    yield sec
    kanal._aktif.cache_clear()


def test_havuzlar_suzulur(kanal_sec):
    kanal_sec("earth")
    tuhaf, _ = kaynaklar.topla()
    kanal_sec("uzay")
    masal, _ = kaynaklar.topla()
    assert len(tuhaf) > 500 and len(masal) > 100  # 2026-10-08: 713 ve 144
    assert all(p.anahtar.startswith("wiki:") for p in tuhaf)
    assert len({p.anahtar for p in tuhaf}) == len(tuhaf), "aynı makale iki kez"
    anahtarlar = {p.anahtar for p in masal}
    assert "ezop:The Lion And The Mouse" in anahtarlar
    assert "ezop:The Wolf And The Lamb" not in anahtarlar  # kuzu yenir: 3-7 yaşa uygun değil


def test_suzgec_esikleri():
    assert not kaynaklar.tuhaf_uygun({"hikaye": 0.9, "hassas": 0.1})  # siyaset sorulmamış: geçemez
    assert kaynaklar.tuhaf_uygun({"hikaye": 0.9, "hassas": 0.1, "siyaset": 0.1})
    assert not kaynaklar.tuhaf_uygun({"hikaye": 0.9, "hassas": 0.6, "siyaset": 0.1})
    assert not kaynaklar.ezop_uygun({"olum": 0.9, "siddet": 0.9, "yetiskin": 0.1, "anlasilir": 1.5})
    assert kaynaklar.ezop_uygun({"olum": 0.2, "siddet": 0.8, "yetiskin": 0.1, "anlasilir": 1.8})


def test_sayi_ad_kapisi():
    kaynak = "On 17 October 1814 a vat at Meux's brewery in London burst, releasing 128,000 to 323,000 gallons."
    assert senaryo.sayi_ad_kapisi("In 1814, a vat burst in London.", kaynak) == []
    assert senaryo.sayi_ad_kapisi("Londoners watched 323,000 gallons flow.", kaynak) == []
    assert senaryo.sayi_ad_kapisi("A wave of 300,000 gallons hit Paris.", kaynak) == [
        "number not in source: 300,000",
        "name not in source: Paris",
    ]


def test_kod_kontrolu_sembol_ve_uzunluk():
    satirlar = ["It was 40°F that day."] + ["A short line with exactly eight words here."] * 7
    sorun = senaryo.kod_kontrolu("masal", "Baslik", satirlar, "")
    assert any("symbols" in s for _, s in sorun)
    uzun = ["word " * 16] + ["A short line with exactly eight words here."] * 6
    assert any("too long" in s for _, s in senaryo.kod_kontrolu("masal", "B", uzun, ""))


def test_kod_kontrolu_sayi_yigini():
    kaynak = "In 1919 a 50 foot tank of 2.3 million gallons burst at 12:30 and 21 died."
    dolu = ["In 1919 the tank burst open.", "It was 50 feet tall, holding 2.3 million gallons.", "At 12:30 it went."]
    dolu += ["Then the dark wave rolled down the street."] * 5
    sorun = senaryo.kod_kontrolu("tuhaf", "Baslik", dolu, kaynak)
    assert [n for n, s in sorun if "too many numbers" in s] == [3]  # sorunlu sayı son sayılı satıra yazılır
    seyrek = ["In 1919 the tank burst open."] + ["Then the dark wave rolled down the street."] * 7
    assert not [s for _, s in senaryo.kod_kontrolu("tuhaf", "Baslik", seyrek, kaynak) if "numbers" in s]


def test_kelime_zamanlari_satiri_doldurur():
    z = uretim.kelime_zamanlari([Parca(0.0, 2.0, "one two three four five")])
    assert [len(g) for _, _, g, _ in z] == [3, 3, 3, 2, 2]  # 3'lük gruplar, grup başına vurgu sırası
    assert z[0][0] == 0.0 and z[-1][1] == pytest.approx(2.0)
    assert all(a[1] == pytest.approx(b[0]) for a, b in itertools.pairwise(z))  # boşluksuz


def test_kenar_kirp_kagidi_atar():
    a = np.full((400, 300, 3), 245, np.uint8)  # kâğıt
    a[30:370, 20:280] = 90  # resim
    b = uretim.kenar_kirp(Image.fromarray(a))
    assert b.size == (260 - 12, 340 - 12)
    tam = Image.fromarray(np.full((400, 300, 3), 90, np.uint8))
    assert uretim.kenar_kirp(tam).size == (300 - 12, 400 - 12)  # kâğıt yoksa yalnız güvenlik payı


@pytest.mark.parametrize("ad", list(uretim.HAREKETLER))
def test_kamera_hareketi_resmin_icinde_kalir(ad):
    """Kadraj resmin dışına taşarsa PIL siyah doldurur: kenarda siyah şerit yok, kadraj gerçekten hareket eder."""
    img = Image.fromarray(np.full((1344, 768, 3), 200, np.uint8))
    kareler = list(uretim.sahne_kareleri(img, 12, ad))
    for k in kareler:
        a = np.asarray(k)
        assert k.size == (1080, 1920) and min(a[0].mean(), a[-1].mean(), a[:, 0].mean(), a[:, -1].mean()) > 150
    desen = Image.fromarray(np.random.default_rng(0).integers(0, 255, (1344, 768, 3), dtype=np.uint8))
    ilk, son = (np.asarray(k, dtype=np.int16) for k in list(uretim.sahne_kareleri(desen, 12, ad))[::11])
    assert np.abs(ilk - son).mean() > 5
    assert uretim.hareket(0) == "iceri"  # kanca sahnesi hep içeri girer


class _SahteKanal:
    """channels().list/update zinciri; update gövdelerini kaydeder."""

    def __init__(self, ad, aciklama="", mfk=False, yerel_ad=None):
        self.oge = {"id": "UC1", "snippet": {"title": ad}, "brandingSettings": {"channel": {"description": aciklama}},
                    "status": {"selfDeclaredMadeForKids": mfk}}  # fmt: skip
        if yerel_ad:
            self.oge["localizations"] = {"en_US": {"title": yerel_ad}}
        self.guncellemeler = []

    def channels(self):
        return self

    def list(self, **_):
        return _Calistir({"items": [self.oge]})

    def update(self, part, body):
        self.guncellemeler.append(part)
        return _Calistir({})


class _Calistir:
    def __init__(self, sonuc):
        self.sonuc = sonuc

    def execute(self, **_):
        return self.sonuc


def test_marka_adi_beklemez_ad_degisince_yerel_adi_gunceller(kanal_sec, monkeypatch):
    """Ad 14 günde 2 değişiklik sınırına takıldı (2026-10-09): kimlik (banner, açıklama, MFK) adı beklemeden uygulanır;
    Studio'da ad değişince çevirili kanal adları bir kez daha güncellenir."""
    from otomat.yayin import marka

    kanal_sec("uzay")
    m = marka.ayarlar()
    uygulanan = []
    monkeypatch.setattr(marka, "uygula", lambda yt, oge, m: uygulanan.append(oge["snippet"]["title"]))
    assert marka.kontrol(_SahteKanal("Orbit Ruler")) == "uygulandı (ad bekleniyor)"
    tamam = _SahteKanal("Orbit Ruler", m["aciklama"]["en"], mfk=True, yerel_ad="Orbit Ruler")
    assert marka.kontrol(tamam) == "tamam (ad bekleniyor)"
    assert marka.kontrol(_SahteKanal("Lanternbug Tales", m["aciklama"]["en"], True, "Orbit Ruler")) == "uygulandı"
    assert marka.kontrol(_SahteKanal("Lanternbug Tales", m["aciklama"]["en"], True, "Lanternbug Tales")) == "tamam"
    assert uygulanan == ["Orbit Ruler", "Lanternbug Tales"]
    assert (marka.KOK / m["banner"]).exists() and (marka.KOK / m["filigran"]).exists()


def test_marka_yedek_adla_da_uygulanir(kanal_sec, monkeypatch):
    from otomat.yayin import marka

    kanal_sec("earth")
    uygulanan = []
    monkeypatch.setattr(marka, "uygula", lambda yt, oge, m: uygulanan.append(oge["snippet"]["title"]))
    assert marka.kontrol(_SahteKanal("Inkwell Oddities Stories")) == "uygulandı"  # YouTube asıl adı reddetti


def _sahte_video(genislik=1080, yukseklik=1920, ses=True, sure=37.71):
    akislar = [{"codec_type": "video", "codec_name": "h264", "width": genislik, "height": yukseklik}]
    if ses:
        akislar.append({"codec_type": "audio", "codec_name": "aac"})
    return lambda _yol: {"streams": akislar, "format": {"duration": str(sure)}}


def test_kabul_referansi_kabul_eder_kusurlari_reddeder(kanal_sec, tmp_path):
    import json
    import shutil
    from pathlib import Path

    from otomat.hikaye import kabul

    kanal_sec("earth")
    ref = Path(__file__).parent / "veri" / "hikaye_ref" / "meta.json"
    meta = json.loads(ref.read_text(encoding="utf-8"))
    shutil.copy(ref, tmp_path / "meta.json")
    (tmp_path / "video.mp4").write_bytes(b"\0" * 300_000)
    for i in range(len(meta["cumleler"])):
        (tmp_path / f"sahne_{i}.jpg").write_bytes(b"x")
    assert kabul.denetle(tmp_path / "meta.json", _sahte_video()) == []
    assert any("sessiz" in h for h in kabul.denetle(tmp_path / "meta.json", _sahte_video(ses=False)))
    assert any("1080x1920" in h for h in kabul.denetle(tmp_path / "meta.json", _sahte_video(1920, 1080)))

    def bozuk(**degisim):
        (tmp_path / "meta.json").write_text(json.dumps({**meta, **degisim}), encoding="utf-8")
        return kabul.denetle(tmp_path / "meta.json", _sahte_video())

    assert bozuk(mfk=True)  # Earth MFK değil
    assert bozuk(aciklama=meta["aciklama"].replace("Kevin MacLeod", "someone"))
    assert bozuk(senaryo={**meta["senaryo"], "hakem_turlari": [[[3, "wrong date"]]]})
    assert bozuk(cumleler=[*meta["cumleler"][:-1], "Please subscribe for more stories."])
    kanal_sec("uzay")
    (tmp_path / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    assert any("MFK" in h for h in kabul.denetle(tmp_path / "meta.json", _sahte_video()))


def test_hizalama_whisper_zamanini_kullanir_eksigi_doldurur():
    from otomat.hikaye import hizala

    p = [Parca(0.0, 2.0, "It held 2.3 million gallons."), Parca(2.3, 3.5, "Then it burst.")]
    # Whisper "2.3"ü "2" + "3" diye böler: o kelime eşleşmez, komşu eşleşmeler arasına yerleşir
    gercek = [(0.0, "it"), (0.2, "held"), (0.5, "2"), (0.7, "3"), (1.2, "million"), (1.6, "gallons"),
              (2.3, "then"), (2.6, "it"), (3.0, "burst")]  # fmt: skip
    b = hizala.baslangiclar(p, gercek)
    assert b[0][1] == 0.2 and b[0][3] == 1.2 and b[0][4] == 1.6 and b[1] == [2.3, 2.6, 3.0]
    assert 0.2 < b[0][2] < 1.2  # eşleşmeyen "2.3"
    assert all(x < y for x, y in itertools.pairwise(b[0]))
    assert hizala.baslangiclar(p, None)[0][0] == 0.0  # Whisper yoksa orantılı
    # başka satıra düşen eşleşmeye güvenilmez, satır sınırı korunur
    kayik = hizala.baslangiclar(p, [(t + 5, w) for t, w in gercek])
    assert all(p[i].bas <= x < p[i].son for i in range(2) for x in kayik[i])


def test_mfk_kanalinda_eski_videolar_cocuk_icerigi_sayilmaz(kanal_sec, monkeypatch, tmp_path):
    """Kanal düzeyi MFK eski videolara da işler; geri çekilen uzay videoları video düzeyinde MFK değil kalmalı."""
    from otomat import durum
    from otomat.yayin import marka

    kanal_sec("uzay")
    db = durum.baglan(tmp_path / "d.db")
    durum.geri_cek(db, ["eski1", "eski2"], dt.date(2026, 10, 8), "format değişimi")
    monkeypatch.setattr(durum, "baglan", lambda: db)
    guncellenen = []

    class _Video:
        def videos(self):
            return self

        def update(self, part, body):
            guncellenen.append((part, body))
            return _Calistir({})

    assert marka.eski_videolari_ayir(_Video()) == ["eski1", "eski2"]
    assert all(p == "status" and b["status"] == {"privacyStatus": "private", "selfDeclaredMadeForKids": False}
               for p, b in guncellenen)  # fmt: skip


def test_kabul_videoyu_ffprobesuz_okur(tmp_path):
    """2026-10-09: Actions'ta ffprobe yok, kabul her videoyu reddetti. Gerçek ffmpeg ile küçük video üretip okunur."""
    import subprocess

    import imageio_ffmpeg

    from otomat.hikaye import kabul

    video = tmp_path / "v.mp4"
    subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=108x192:d=1",
         "-f", "lavfi", "-i", "sine=d=1", "-shortest", "-c:v", "libx264", "-c:a", "aac", str(video)],
        check=True,
    )  # fmt: skip
    b = kabul._ffprobe(video)
    akislar = {s["codec_type"]: s for s in b["streams"]}
    assert (akislar["video"]["width"], akislar["video"]["height"]) == (108, 192) and "audio" in akislar
    assert 0.9 < float(b["format"]["duration"]) < 1.2
    with pytest.raises(FileNotFoundError):
        kabul._ffprobe(tmp_path / "yok.mp4")


def test_filtreye_takilan_hikaye_duser_siradaki_denenir(tmp_path, monkeypatch):
    """2026-10-09: bir sahne görseli güvenlik filtresine takıldı (3030), tüm koşu düştü. Artık hikâye düşer."""
    from otomat import durum, gunluk
    from otomat.hikaye import cf, kabul
    from otomat.hikaye import uretim as h_uretim

    db = durum.baglan(tmp_path / "d.db")
    paketler = [type("P", (), {"anahtar": f"wiki:{i}", "hash": f"h{i}", "kol": "k", "tur": "t"})() for i in range(2)]
    sira = iter(paketler)
    monkeypatch.setattr(gunluk, "sec", lambda *a: (next(sira), "kalip", "sablon", {}))
    monkeypatch.setattr(gunluk, "KOK", tmp_path)
    monkeypatch.setattr(kabul, "denetle", lambda *a: [])

    def uret(paket, *a):
        if paket.anahtar == "wiki:0":
            raise cf.FiltreHatasi("görsel üretilemedi (400): 3030")
        return {"baslik": "ok"}

    monkeypatch.setattr(h_uretim, "uret", uret)
    kayit = {}
    paket, *_, meta = gunluk.hikaye_uret([], db, dt.date(2026, 10, 9), kayit)
    assert paket.anahtar == "wiki:1" and meta == {"baslik": "ok"}
    assert kayit["dusen_hikayeler"][0]["anahtar"] == "wiki:0" and "3030" in kayit["dusen_hikayeler"][0]["sorunlar"][0]


def test_hazir_uretim_kotasiz_kullanilir_yayinlanan_ve_kusurlu_atlanir(kanal_sec, tmp_path, monkeypatch):
    """10-09: ffprobe hatası kabulden geçecek 5 videoyu attı, kota boşa gitti. Artifact'tan dönen üretim kullanılır."""
    import json

    from otomat import durum, gunluk
    from otomat.hikaye import kabul
    from otomat.hikaye import uretim as h_uretim

    kanal_sec("earth")
    db = durum.baglan(tmp_path / "d.db")
    P = type("P", (), {})
    paketler = []
    for i, ad in enumerate(["wiki:Kusurlu", "wiki:Hazir", "wiki:Yayinda"]):
        p = P()
        p.anahtar, p.hash, p.kol, p.tur, p.gorsel = ad, f"h{i}", "k", "tuhaf", {}
        paketler.append(p)
        d = tmp_path / "calisma" / "gunluk" / "2026-10-10" / ad.replace(":", "_")
        d.mkdir(parents=True)
        meta = {"paket": {"anahtar": ad, "hash": f"h{i}"}, "secim": {"kalip": "kisi", "sablon": "s"}, "baslik": ad}
        (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    durum.kaydet(db, paketler[2], dt.date(2026, 10, 9), "vid")
    monkeypatch.setattr(gunluk, "KOK", tmp_path)
    monkeypatch.setattr(durum, "taze_mi", lambda db, p, *a: p.anahtar != "wiki:Yayinda")
    monkeypatch.setattr(kabul, "denetle", lambda m, *a, **k: ["kusur"] if "Kusurlu" in str(m) else [])
    monkeypatch.setattr(h_uretim, "uret", lambda *a: pytest.fail("hazır varken üretim (kota) harcandı"))
    kayit = {}
    paket, kalip, _, log, dizin, meta = gunluk.hikaye_uret(paketler, db, dt.date(2026, 10, 11), kayit)
    assert paket.anahtar == "wiki:Hazir" and kalip == "kisi" and meta["baslik"] == "wiki:Hazir"
    assert dizin == tmp_path / "calisma" / "gunluk" / "2026-10-11" / "wiki_Hazir" and (dizin / "meta.json").exists()
    assert kayit["hazir"].endswith("2026-10-10/wiki_Hazir") and log["degisti"] == []


def test_gorsel_istemi_karakter_tarifini_her_sahnede_tasir():
    """Orbit 10-09: tarif yalnız ilk sahnede vardı, horoz her karede başka renkti."""
    oyuncular = ["Cock: a bright yellow rooster with orange comb", "Farmer: an old man in a straw hat"]
    i = uretim.gorsel_istemi("Soft crayon", "A farmyard.", oyuncular, "Cock pecking at corn by the fence.")
    assert "Cock is a bright yellow rooster with orange comb." in i and "straw hat" not in i
    assert i.startswith("Soft crayon. A single full-frame scene") and i.endswith("Cock pecking at corn by the fence.")
    tam = "Close-up of Cock, a bright yellow rooster with orange comb, smiling."
    assert uretim.gorsel_istemi("S", "W.", oyuncular, tam).count("bright yellow") == 1  # tarif zaten varsa tekrar yok
    assert "Cocktail" not in uretim.gorsel_istemi("S", "W.", ["Cock: x"], "A cocktail glass.") and "is x" not in (
        uretim.gorsel_istemi("S", "W.", ["Cock: x"], "A cocktail glass.")
    )
