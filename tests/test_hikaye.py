"""Hikâye motoru: havuz süzgeçleri, kod kapıları, kelime zamanlaması, kenar kırpma (Cloudflare'e gitmeden)."""

import datetime as dt
import itertools
import json

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
    assert len(tuhaf) > 500 and len(masal) > 200  # 2026-10-08: 713 ve 144; 10-13 genel kitle: 245
    assert all(p.anahtar.startswith("wiki:") for p in tuhaf)
    assert len({p.anahtar for p in tuhaf}) == len(tuhaf), "aynı makale iki kez"
    anahtarlar = {p.anahtar for p in masal}
    assert "ezop:The Lion And The Mouse" in anahtarlar
    assert "ezop:The Wolf And The Lamb" in anahtarlar  # 10-13'e kadar dışarıdaydı (kuzu yenir, 3-7 yaş)
    assert "ezop:The Blackamoor" not in anahtarlar and "ezop:The Runaway Slave" not in anahtarlar


def test_suzgec_esikleri():
    assert not kaynaklar.tuhaf_uygun({"hikaye": 0.9, "hassas": 0.1})  # siyaset sorulmamış: geçemez
    assert kaynaklar.tuhaf_uygun({"hikaye": 0.9, "hassas": 0.1, "siyaset": 0.1})
    assert not kaynaklar.tuhaf_uygun({"hikaye": 0.9, "hassas": 0.6, "siyaset": 0.1})
    # genel kitle (K-24, 10-13): ölüm ve çocuğun anlayışı eleme nedeni değil, yetişkin teması hâlâ
    assert kaynaklar.ezop_uygun({"olum": 0.9, "siddet": 0.9, "yetiskin": 0.1, "anlasilir": 0.4})
    assert not kaynaklar.ezop_uygun({"olum": 0.2, "siddet": 0.1, "yetiskin": 0.7, "anlasilir": 1.8})


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
    oran = ["Mapped at a 1:4-million scale on maps."] + ["A short line with exactly eight words here."] * 6
    assert (1, "spell out symbols as words for the narrator: 1:4") in senaryo.kod_kontrolu("masal", "B", oran, "")
    assert not senaryo.SEMBOL.search("In 1973, at dawn: the tree fell.")
    assert not senaryo.SEMBOL.search("At 12:30 p.m., the tank collapsed.")  # saat doğru okunuyor
    assert senaryo.SEMBOL.search("a 1:50,000 map") and senaryo.SEMBOL.search("odds of 3:1")
    uzun = ["word " * 16] + ["A short line with exactly eight words here."] * 6
    assert any("too long" in s for _, s in senaryo.kod_kontrolu("masal", "B", uzun, ""))


def test_kod_kontrolu_sayi_yigini():
    kaynak = "In 1919 a 50 foot tank of 2.3 million gallons burst at 12:30 and 21 died."
    dolu = ["In 1919 the tank burst open.", "It was 50 feet tall, holding 2.3 million gallons.", "At 12:30 it went."]
    dolu += ["Then the dark wave rolled down the street."] * 5
    sorun = senaryo.kod_kontrolu("tuhaf", "Baslik", dolu, kaynak)
    # ilk iki sayıdan sonrakini taşıyan her satır (10-12 Loret: yalnız son satır işaretlenince sorun kapanmadı)
    assert [n for n, s in sorun if "may hold only 2" in s] == [2, 3]
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
    tamam = _SahteKanal("Orbit Ruler", m["aciklama"]["en"], mfk=False, yerel_ad="Orbit Ruler")
    assert marka.kontrol(tamam) == "tamam (ad bekleniyor)"
    # 10-13: Orbit genel kitleye geçti; kanal hâlâ MFK ise kimlik yeniden uygulanır
    assert marka.kontrol(_SahteKanal("Orbit Ruler", m["aciklama"]["en"], True, "Orbit Ruler")).startswith("uygulandı")
    uygulanan.pop()
    assert marka.kontrol(_SahteKanal("Lanternbug Tales", m["aciklama"]["en"], False, "Orbit Ruler")) == "uygulandı"
    assert marka.kontrol(_SahteKanal("Lanternbug Tales", m["aciklama"]["en"], False, "Lanternbug Tales")) == "tamam"
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
    # 10-12: "Lord Bloody Wog Rolo" (etnik hakaret) TypeSafe süzgecinden geçip 10-13'e planlanmıştı
    assert any("hakaret" in h for h in bozuk(baslik="Lord Bloody Wog Rolo: Guest of Her Majesty"))
    assert any("hakaret" in h for h in bozuk(paket={**meta.get("paket", {}), "anahtar": "wiki:Lord Bloody Wog Rolo"}))
    assert not any("hakaret" in h for h in bozuk(baslik="The Boy Who Outran Michael Fagan"))
    # 10-13: Orbit genel kitleye geçti; artifact'ta kalan çocuk formatı üretimi (MFK) yayına çıkmaz
    kanal_sec("uzay")
    (tmp_path / "meta.json").write_text(json.dumps({**meta, "mfk": True}), encoding="utf-8")
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
    # kalite yüzünden geri çekilen masal çocuk içeriğidir: "çocuklara özel değil"e çevrilmez (10-12)
    durum.geri_cek(db, ["masal"], dt.date(2026, 10, 12), "kalite: masalda olmayan iki ayı")
    monkeypatch.setattr(durum, "baglan", lambda: db)
    guncellenen = []

    class _Video:
        def videos(self):
            return self

        def update(self, part, body):
            guncellenen.append((part, body))
            return _Calistir({})

    assert marka.eski_videolari_ayir(_Video()) == ["eski1", "eski2"]
    # tam gövde (10-13 denetimi): kısmi status embeddable/publicStatsViewable/license'ı varsayılana çekiyordu
    assert all(p == "status" and b["status"]["privacyStatus"] == "private"
               and b["status"]["selfDeclaredMadeForKids"] is False and b["status"]["publicStatsViewable"] is True
               and b["status"]["license"] == "youtube" for p, b in guncellenen)  # fmt: skip


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


def _hikaye_paketi(anahtar="wiki:Tank", hash_="h1"):
    P = type("P", (), {})
    p = P()
    p.anahtar, p.hash, p.tur, p.konu, p.kol = anahtar, hash_, "tuhaf", "konu", "k"
    p.gorsel = {"baslik": "Tank"}
    return p


def _sahte_senaryo(satir="Old line here"):
    return senaryo.Senaryo("Başlık", "mysterious", "Boston, 1919.", ["Ann: a girl in red"],
                           [satir] * 7, [f"scene {i}" for i in range(7)])  # fmt: skip


def test_senaryo_kota_kesintisinden_sonra_surer_eski_gorseller_karismaz(kanal_sec, tmp_path, monkeypatch):
    """Kotaya takılan üretim aynı slotta yeniden seçilince yeni senaryo yazılıyor, önceki senaryonun sahne görselleri
    `cf.gorsel`in "varsa üretme" kuralıyla yeni sahnelere karışıyordu. Hakemden geçmiş senaryo artık sürer."""
    kanal_sec("earth")
    yazilan = []
    monkeypatch.setattr(uretim.kaynaklar, "metin", lambda p: "kaynak")

    def yaz(*a):
        yazilan.append(a)
        return _sahte_senaryo(f"Line {len(yazilan)} here")

    monkeypatch.setattr(uretim.senaryo, "yaz", yaz)
    p = _hikaye_paketi()
    sc, kalip, istemler = uretim.senaryo_al(p, "kisi", tmp_path)
    assert len(yazilan) == 1 and len(istemler) == 7 and (tmp_path / uretim.SENARYO).exists()
    for i in range(3):  # kota üç görselden sonra bitti
        (tmp_path / f"sahne_{i}.jpg").write_bytes(b"x")
    sc2, kalip2, istemler2 = uretim.senaryo_al(p, "detay", tmp_path)  # yeniden deneme: aynı senaryo, aynı görseller
    assert len(yazilan) == 1 and sc2.satirlar == sc.satirlar and istemler2 == istemler and kalip2 == "kisi"
    assert len(list(tmp_path.glob("sahne_*.jpg"))) == 3
    # kanal stili değişti (sahne 1'in kayıtlı istemi farklı): o görsel yeniden çizilir, senaryo kalır
    d = json.loads((tmp_path / uretim.SENARYO).read_text(encoding="utf-8"))
    d["istemler"][1] = "eski stil"
    (tmp_path / uretim.SENARYO).write_text(json.dumps(d), encoding="utf-8")
    uretim.senaryo_al(p, "kisi", tmp_path)
    assert sorted(x.name for x in tmp_path.glob("sahne_*.jpg")) == ["sahne_0.jpg", "sahne_2.jpg"]
    # başka paket (hash değişti): yeni senaryo, eski çıktılar silinir
    (tmp_path / "yerel.json").write_text("{}", encoding="utf-8")
    uretim.senaryo_al(_hikaye_paketi(hash_="h2"), "kisi", tmp_path)
    assert len(yazilan) == 2 and not list(tmp_path.glob("sahne_*.jpg")) and not (tmp_path / "yerel.json").exists()


def test_yarim_uretim_onceki_kosudan_getirilir(kanal_sec, tmp_path, monkeypatch):
    import json

    from otomat import gunluk

    kanal_sec("earth")
    monkeypatch.setattr(gunluk, "KOK", tmp_path)
    p = _hikaye_paketi()
    for kosu, satir in (("100", "eski"), ("200", "yeni")):
        d = tmp_path / "calisma" / "onceki" / kosu / "2026-10-11" / "wiki_Tank"
        d.mkdir(parents=True)
        (d / "senaryo.json").write_text(json.dumps({"anahtar": p.anahtar, "hash": p.hash, "s": satir}), "utf-8")
        (d / "sahne_0.jpg").write_bytes(satir.encode())
    baska = tmp_path / "calisma" / "onceki" / "300" / "2026-10-11" / "wiki_Baska"
    baska.mkdir(parents=True)
    (baska / "senaryo.json").write_text(json.dumps({"anahtar": "wiki:Baska", "hash": "x"}), "utf-8")
    hedef = tmp_path / "calisma" / "gunluk" / "2026-10-12" / "wiki_Tank"
    assert gunluk.yarim_uretimi_getir(p, hedef).endswith("onceki/200/2026-10-11/wiki_Tank")  # en yeni koşu
    assert (hedef / "sahne_0.jpg").read_bytes() == b"yeni" and (hedef / "senaryo.json").exists()
    assert gunluk.yarim_uretimi_getir(p, hedef) is None  # klasörde senaryo zaten var


def test_kaynagi_kullanilamayan_hikaye_duser_siradaki_denenir(tmp_path, monkeypatch):
    """Silinmiş/taşınmış Wikipedia makalesi tüm koşuyu düşürüyordu; artık yalnız o hikâye düşer."""
    from otomat import durum, gunluk
    from otomat.hikaye import kabul
    from otomat.hikaye import uretim as h_uretim

    db = durum.baglan(tmp_path / "d.db")
    sira = iter([_hikaye_paketi("wiki:Yok"), _hikaye_paketi("wiki:Var", "h2")])
    monkeypatch.setattr(gunluk, "sec", lambda *a: (next(sira), "kisi", "sablon", {}))
    monkeypatch.setattr(gunluk, "KOK", tmp_path)
    monkeypatch.setattr(kabul, "denetle", lambda *a: [])

    def uret(paket, *a):
        if paket.anahtar == "wiki:Yok":
            raise kaynaklar.KaynakHatasi("makale bulunamadı: Yok")
        return {"baslik": "ok", "secim": {"kalip": "zitlik"}}

    monkeypatch.setattr(h_uretim, "uret", uret)
    kayit = {}
    paket, kalip, *_ = gunluk.hikaye_uret([], db, dt.date(2026, 10, 9), kayit)
    assert paket.anahtar == "wiki:Var" and kalip == "zitlik"  # kalıp üretilen senaryonunki
    assert kayit["dusen_hikayeler"][0]["anahtar"] == "wiki:Yok" and "neuron" in kayit["dusen_hikayeler"][0]


def test_kisa_makale_kaynak_hatasi(monkeypatch):
    monkeypatch.setattr(kaynaklar, "_wiki", lambda params: {"query": {"pages": [{"extract": "Too short."}]}})
    with pytest.raises(kaynaklar.KaynakHatasi, match="kısa"):
        kaynaklar.metin(_hikaye_paketi())
    monkeypatch.setattr(kaynaklar, "_wiki", lambda params: {"query": {"pages": [{"missing": True}]}})
    with pytest.raises(kaynaklar.KaynakHatasi, match="bulunamadı"):
        kaynaklar.metin(_hikaye_paketi())


def _senaryo_yaz(monkeypatch, satirlar, hakemler, cast=(), changes=()):
    """`yaz`ı sahte modelle koşturur: ilk çağrı senaryo, sonra hakem (sırayla `hakemler`) ve onarım (değişiklik yok)."""
    ilk = {"title": "The Vat That Burst", "mood": "m", "world": "A London street in 1814, brown and gray.",
           "cast": list(cast), "changes": list(changes),
           "scenes": [{"line": s, "image": f"image {i}"} for i, s in enumerate(satirlar, 1)]}  # fmt: skip
    hakem = iter(hakemler)
    istemler = []

    def sohbet(istem, sema):
        istemler.append(istem)
        if "title" in sema["properties"]:
            return ilk
        if "problems" in sema["properties"]:
            return {"problems": [{"line": n, "reason": r} for n, r in next(hakem)]}
        return {"fixes": []}

    monkeypatch.setattr(senaryo.cf, "sohbet", sohbet)
    return istemler


def test_son_turda_kalan_ara_satir_cikarilir_hakem_onaylarsa(monkeypatch):
    """10-11/12: Earth'te düşen 8 hikâyenin 5'i son turda tek sorunla düştü; ara satır çıkarılıp yeniden sorulur."""
    satirlar = [f"The beer wave rolled down street {k} that day." for k in "abcdefgh"]
    kalan = [(5, "repeats line 3")]
    _senaryo_yaz(monkeypatch, satirlar, [kalan] * senaryo.TUR_SAYISI + [[]])
    sc = senaryo.yaz("tuhaf", "London Beer Flood", "a beer wave rolled down the street that day", "", "detay", ["m"])
    assert len(sc.satirlar) == len(sc.gorseller) == 7 and sc.cikarilan == [satirlar[4]]
    assert "image 5" not in sc.gorseller and sc.turlar[-1] == []  # kabul son turun temiz olmasını ister

    # kanca, son satır ya da 2'den fazla satır çıkarılmaz; çıkarılmış hali de hakemden geçmezse senaryo düşer
    for sorun, sonra in [([(1, "x")], []), ([(8, "x")], []), ([(3, "x"), (4, "y"), (5, "z")], []), (kalan, kalan)]:
        _senaryo_yaz(monkeypatch, satirlar, [sorun] * senaryo.TUR_SAYISI + [sonra])
        with pytest.raises(senaryo.SenaryoHatasi):
            senaryo.yaz("tuhaf", "London Beer Flood", "a beer wave rolled down the street that day", "", "detay", ["m"])


def test_onarim_istemi_yeni_ayrinti_eklemeyi_yasaklar():
    assert "add no new detail, purpose, cause or number" in senaryo.ONARIM_ISTEM


def test_baslikta_buyuk_harfli_kelime_ad_sayilmaz_bos_satir_onarima_gider():
    kaynak = "In 1986 Hanshin Tigers fans threw a statue of Colonel Sanders into a river."
    satirlar = ["Fans threw a statue into the river."] * 6 + ["The Tigers won."] + ["Then"]
    sorun = senaryo.kod_kontrolu("tuhaf", "Colonel Sanders' Curse Haunts the Tigers", satirlar, kaynak)
    assert not [s for s in sorun if s[0] == 0]  # 10-09: "name not in source: Haunts" boş tur harcatıyordu
    assert (8, "too short; write a full spoken line of 4-12 words") in sorun
    assert senaryo.kod_kontrolu("tuhaf", "1987 Curse", satirlar[:7], kaynak)[0] == (0, "number not in source: 1987")


def test_muzik_indirilemezse_ayni_moodun_siradaki_parcasi(kanal_sec, tmp_path, monkeypatch):
    import urllib.error

    kanal_sec("uzay")
    monkeypatch.setattr(uretim, "MUZIK_DIZIN", tmp_path)
    parcalar = kanal.aktif().muzik["wistful"]
    istenen = []
    mp3 = b"ID3" + b"\0" * uretim.MUZIK_EN_AZ
    yanitlar = iter([None, b"<html>404</html>" * 10_000, mp3])  # kapalı, hata sayfası (mp3 değil), gerçek parça

    class Yanit:
        def __init__(self, veri):
            self.veri = veri

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return self.veri

    def urlopen(istek, timeout):
        istenen.append(istek.full_url)
        if (veri := next(yanitlar)) is None:
            raise urllib.error.URLError("incompetech kapalı")
        return Yanit(veri)

    monkeypatch.setattr(uretim.urllib.request, "urlopen", urlopen)
    tohum = "x"
    bas = sum(map(ord, tohum)) % len(parcalar)
    yol, ad = uretim.muzik_sec("wistful", tohum)
    # hata sayfası önbelleğe girmez (birleştirme o parçada hep düşerdi); üçüncü parça indirilir
    assert ad == parcalar[(bas + 2) % len(parcalar)] and yol.read_bytes() == mp3 and len(istenen) == 3
    assert not list(tmp_path.glob("*.tmp")) and len(list(tmp_path.glob("*.mp3"))) == 1
    # tohumun parçası önbellekteyse indirilmeden o kullanılır
    monkeypatch.setattr(uretim.urllib.request, "urlopen", lambda *a, **k: pytest.fail("önbellek varken indirme"))
    (tmp_path / f"{parcalar[bas]}.mp3").write_bytes(b"ilk")
    assert uretim.muzik_sec("wistful", tohum) == (tmp_path / f"{parcalar[bas]}.mp3", parcalar[bas])


def test_gorsel_yanitsiz_donerse_dosya_yazilmaz(tmp_path, monkeypatch):
    from otomat.hikaye import cf

    monkeypatch.setattr(cf, "_istek", lambda *a, **k: {"result": {}, "success": True})
    monkeypatch.setattr(cf.time, "sleep", lambda _: None)
    with pytest.raises(cf.CFHatasi, match="görsel"):
        cf.gorsel("a cat", tmp_path / "sahne_0.jpg", 1)
    assert not list(tmp_path.iterdir())  # yarım/boş dosya sonraki koşuda "var" sayılmasın


def test_hakaretli_makale_havuza_girmez():
    havuz = [
        {"baslik": b, "bolum": "People", "tanim": "t", "ts": {"hikaye": 0.9, "hassas": 0.1, "siyaset": 0.1}}
        for b in ["Lord Bloody Wog Rolo", "The boy Jones", "Raccoon wedding"]
    ]
    assert [p.anahtar for p in kaynaklar._tuhaf(havuz, "2026-10-12")] == ["wiki:The boy Jones", "wiki:Raccoon wedding"]


def test_yazi_ocr_esigi():
    """S12 ölçümü (87 sahne): masal karelerinde OCR Çince karakter, tek harf, rakam uyduruyor; sayılmaz."""
    from otomat.hikaye import yazi

    assert yazi.sayilir("ABOLISHA FoR", 0.94) and yazi.sayilir("BWRE", 0.74)
    assert not yazi.sayilir("米火粥", 0.9) and not yazi.sayilir("C", 0.81) and not yazi.sayilir("1832", 0.9)
    assert not yazi.sayilir("lade", 0.56)


def test_yazi_tasiyan_nesne_tarifte_bulunur_olumsuz_sayilmaz():
    """Sister Boom Boom / Wog Rolo tarifleri (10-12): tabela, pankart, tırnaklı söz anlamsız harf olarak çizildi."""
    s = senaryo.yazi_tasiyanlar(
        "Sydney streets of the late twentieth century, neon signs, denim and leather.",
        [
            "Rolo marching with a large sandwich board covered with anti-monarchy slogans.",
            'A car with a "For Sale" card on the windshield.',
            "A small fox sits by a bush, no signs or letters anywhere.",
            "Close-up of a metal jail cell door slightly ajar.",
        ],
    )
    assert [n for n, _ in s] == [0, 1, 2]
    assert "neon" in s[0][1] and "slogans" in s[1][1] and '"for sale"' in s[2][1]


def test_yazisiz_yazi_tasiyan_yan_cumleyi_duser_stile_dokunmaz(kanal_sec):
    """Bartman (10-12): skor tabelası iki onarım turunda ve OCR yeniden çiziminde kaldı, "WACTER" diye çizildi."""
    skor = ("Mark Prior winding up to throw a wild pitch; the ball crosses home plate, Luis Castillo and Juan Pierre "
            "sprinting toward third; the scoreboard shows the run tally climbing.")  # fmt: skip
    assert senaryo.yazisiz(skor) == (
        "Mark Prior winding up to throw a wild pitch; the ball crosses home plate, Luis Castillo and Juan Pierre "
        "sprinting toward third."
    )
    assert senaryo.yazisiz("A tank of 2.3 million gallons bursts, molasses everywhere, a huge brown wave.") == (
        "A tank of 2.3 million gallons bursts, molasses everywhere, a huge brown wave."
    )
    assert senaryo.yazisiz("A neon sign glows.") == "A neon sign glows."  # geriye tarif kalmıyorsa dokunulmaz
    stil = kanal.aktif().stil
    istem = uretim.gorsel_istemi(stil, "Wrigley Field at dusk.", [], skor)
    assert senaryo.yazisiz(istem).startswith(f"{stil}. A single full-frame scene") and "scoreboard" not in (
        senaryo.yazisiz(istem)
    )


def test_gorsel_temizle_forma_duzlesir_onarim_tutmazsa_yan_cumle_duser(monkeypatch):
    sc = senaryo.Senaryo(
        "B", "m", "Wrigley Field in 2003, ivy walls.", ["Moises Alou: a tall man in a white jersey"], ["l"] * 2,
        ["Moises Alou (white jersey, red cap) leaps near the wall, glove out, crowd behind.",
         "Mark Prior throws a wild pitch toward home plate; the scoreboard shows the run tally climbing."],
    )  # fmt: skip
    # model tarifleri hiç değiştirmeden geri verdi (10-12 Bartman: iki turda da aynı işaretler kaldı)
    ayni = {"world": sc.dunya, "scenes": [{"scene": 2, "image": sc.gorseller[1]}]}
    monkeypatch.setattr(senaryo.cf, "sohbet", lambda istem, sema: ayni)
    senaryo.gorsel_temizle(sc)
    assert "jersey" not in " ".join([*sc.gorseller, *sc.oyuncular]) and "white uniform" in sc.oyuncular[0]
    assert sc.gorseller[1] == "Mark Prior throws a wild pitch toward home plate."
    assert sc.gorsel_onarim == [[[2, "scoreboard"]], []]


def test_gorsel_temizle_atif_donen_tarifi_almaz_ikinci_tur_kalani_onarir(monkeypatch):
    """S12: model iki sahneye tarif yerine "SCENE 2" yazdı; kare ana karaktersiz boş sokak çıktı."""
    sc = senaryo.Senaryo(
        "B", "m", "A city at night with neon signs everywhere.", [], ["l"] * 3,
        ["A nun holds a placard in the rain.", "A nun at a ballot box.", "A nun on marble steps at dusk."],
    )  # fmt: skip
    cevaplar = iter([
        {"world": "A rainy city at night bathed in pink and turquoise light from street lamps.",
         "scenes": [{"scene": 1, "image": "SCENE 1"},
                    {"scene": 2, "image": "A nun in white robes drops a folded slip into a wooden box."}]},
        {"world": "", "scenes": [{"scene": 1, "image": "A nun in white robes raises her fist in the rain, a crowd."}]},
    ])  # fmt: skip
    istemler = []
    monkeypatch.setattr(senaryo.cf, "sohbet", lambda istem, sema: istemler.append(istem) or next(cevaplar))
    senaryo.gorsel_temizle(sc)
    assert sc.gorseller[0].startswith("A nun in white robes raises") and "wooden box" in sc.gorseller[1]
    assert sc.gorseller[2] == "A nun on marble steps at dusk." and "neon" not in sc.dunya
    isaretli = istemler[1].split("FLAGGED")[1].split("Rewrite")[0]
    assert "scene 1: placard" in isaretli and "scene 2" not in isaretli and "world" not in isaretli
    assert sc.gorsel_onarim[1] == [] and len(sc.gorsel_onarim[0]) == 3


def test_yazili_sahne_yeniden_cizilir_az_yazili_kalir_hak_sinirli(tmp_path, monkeypatch):
    from otomat.hikaye import cf, yazi

    for i in range(5):
        (tmp_path / f"sahne_{i}.jpg").write_bytes(b"eski")
    ilk = {0: [], 1: ["SITER BOOM"], 2: ["BATER"], 3: ["NUN OF THE"], 4: ["ABVE"]}
    sonra = {1: [], 2: ["BATERRRR"], 3: ["NUN"]}  # 1 temizlendi, 2 daha yazılı (eskisi kalır), 3 daha az yazılı
    cizilen = set()

    def oku(yol):
        i = int(yol.stem.split("_")[1])
        return sonra[i] if i in cizilen else ilk[i]

    tohumlar = []

    def gorsel(istem, yol, tohum):
        assert istem.endswith(uretim.YAZISIZ)
        tohumlar.append(tohum)
        cizilen.add(int(yol.stem.split("_")[1]))
        yol.write_bytes(b"yeni")
        return yol

    monkeypatch.setattr(yazi, "oku", oku)
    monkeypatch.setattr(cf, "gorsel", gorsel)
    k = uretim.yazilari_ayikla([f"istem {i}" for i in range(5)], tmp_path, 100)
    assert k["yeniden"] == uretim.YAZI_YENIDEN == 3 and tohumlar == [115, 125, 135]
    assert [(tmp_path / f"sahne_{i}.jpg").read_bytes() for i in range(5)] == [
        b"eski",
        b"yeni",
        b"eski",
        b"yeni",
        b"eski",
    ]
    assert k["son"] == {2: ["BATER"], 3: ["NUN"], 4: ["ABVE"]}  # 4: hak bitti
    assert set(k["ilk"]) == {1, 2, 3, 4} and not list(tmp_path.glob("yazili_*"))


def test_yazili_sahne_kotaya_takilirsa_eski_kare_yerinde_kalir(tmp_path, monkeypatch):
    from otomat.hikaye import cf, yazi

    (tmp_path / "sahne_0.jpg").write_bytes(b"eski")
    monkeypatch.setattr(yazi, "oku", lambda yol: ["SALE"])

    def kota(*a):
        raise cf.KotaHatasi("kota")

    monkeypatch.setattr(cf, "gorsel", kota)
    with pytest.raises(cf.KotaHatasi):
        uretim.yazilari_ayikla(["istem"], tmp_path, 0)
    assert (tmp_path / "sahne_0.jpg").read_bytes() == b"eski" and not list(tmp_path.glob("yazili_*"))
    monkeypatch.setattr(yazi, "oku", lambda yol: None)  # OCR kurulu değil: denetim atlanır, video yine çıkar
    assert uretim.yazilari_ayikla(["istem"], tmp_path, 0) == {"ocr": "yok"}


def test_yazi_ocr_gercek_karede_yaziyi_bulur_bos_karede_bulmaz(tmp_path):
    """CI `--extra gorsel` ile kurar: Linux runner'da OCR gerçekten yükleniyor mu (opencv libGL ister)."""
    pytest.importorskip("rapidocr_onnxruntime")
    from PIL import ImageDraw, ImageFont

    from otomat.hikaye import yazi

    font = ImageFont.truetype("otomat/varliklar/fontlar/BarlowCondensed-Bold.ttf", 90)
    dolu, bos = Image.new("RGB", (768, 400), "#e8dcc0"), Image.new("RGB", (768, 400), "#e8dcc0")
    ImageDraw.Draw(dolu).text((60, 140), "NUN OF THE ABOVE", font=font, fill="#202020")
    dolu.save(tmp_path / "dolu.jpg")
    bos.save(tmp_path / "bos.jpg")
    assert any("ABOVE" in m.upper() for m in yazi.oku(tmp_path / "dolu.jpg"))
    assert yazi.oku(tmp_path / "bos.jpg") == []


KUYRUK = {"who": "Felix", "from_scene": 3, "look": "a tailless fox with a round bare rump and a pink bandage",
          "question": "Does the orange fox have a tail?", "expected": False}  # fmt: skip


def test_degisimler_suzulur_olumsuz_gorunus_alinmaz():
    """10-15 Orbit: "his tail gone" yazan sahnede klein kuyruğu çizdi (S13: olumsuz 2/2 kuyruklu, olumlu 2/2
    kuyruksuz)."""
    oyuncular = ["Felix: a bright orange fox in a red scarf"]
    assert senaryo.degisimler([dict(KUYRUK, who="felix")], oyuncular, 7) == [
        {"kim": "Felix", "sahne": 3, "gorunum": KUYRUK["look"], "soru": KUYRUK["question"], "beklenen": False}
    ]
    for bozuk in [{"who": "Willow"}, {"from_scene": 1}, {"from_scene": 8}, {"look": "his tail gone now forever"},
                  {"look": "tailless"}, {"question": "Tail visible"}]:  # fmt: skip
        assert senaryo.degisimler([dict(KUYRUK, **bozuk)], oyuncular, 7) == []
    assert senaryo.degisimler(None, oyuncular, 7) == []


def test_degisen_gorunus_sonraki_sahnelerin_istemine_girer():
    gorseller = ["Felix smiling.", "Felix caught in a snare.", "Felix on a log.", "A wise gray fox."]
    sc = senaryo.Senaryo("T", "m", "A forest.", ["Felix: a bright orange fox"], ["l"] * 4, gorseller)
    sc.degisimler = senaryo.degisimler([KUYRUK], sc.oyuncular, 4)
    istemler = uretim.istemleri_kur("Stil", sc)
    assert [("is now a tailless fox" in i) for i in istemler] == [False, False, True, False]  # 4: Felix sahnede yok
    assert istemler[2].index("Felix is a bright orange fox.") < istemler[2].index("Felix is now")


def test_cikarilan_sahne_degisimin_sahnesini_kaydirir(monkeypatch):
    satirlar = [f"Felix the fox walked down path {k} that day." for k in "abcdefgh"]
    _senaryo_yaz(monkeypatch, satirlar, [[(4, "repeats line 2")]] * senaryo.TUR_SAYISI + [[]],
                 cast=["Felix: an orange fox"], changes=[dict(KUYRUK, from_scene=6)])  # fmt: skip
    sc = senaryo.yaz("tuhaf", "Fox", "felix the fox walked down the path that day", "", "detay", ["m"])
    assert sc.cikarilan == [satirlar[3]] and sc.degisimler[0]["sahne"] == 5
    _senaryo_yaz(monkeypatch, satirlar, [[(4, "x")]] * senaryo.TUR_SAYISI + [[]],
                 cast=["Felix: an orange fox"], changes=[dict(KUYRUK, from_scene=4)])  # fmt: skip
    sc = senaryo.yaz("tuhaf", "Fox", "felix the fox walked down the path that day", "", "detay", ["m"])
    assert sc.degisimler[0]["sahne"] == 4  # değişimin ilk sahnesi çıktı: yeni görünüş sonraki sahneden (eski 5)


def _durum_senaryosu():
    sc = senaryo.Senaryo("T", "m", "A forest.", ["Felix: a fox"], ["l"] * 4,
                         ["Felix smiling.", "Felix caught.", "Felix on a log.", "Felix playing."])  # fmt: skip
    sc.degisimler = senaryo.degisimler([KUYRUK], sc.oyuncular, 4)
    return sc


def test_degisen_gorunus_tutmayan_kare_yeniden_cizilir(tmp_path, monkeypatch):
    from otomat.hikaye import cf

    for i in range(4):
        (tmp_path / f"sahne_{i}.jpg").write_bytes(b"kuyruklu")
    sorulan, tohumlar = [], []

    def sor(yol, soru):
        sorulan.append(yol.name)
        return yol.read_bytes() == b"kuyruklu", 0.95  # kuyruk var mı?

    def gorsel(istem, yol, tohum):
        tohumlar.append(tohum)
        yol.write_bytes(b"kuyruksuz")
        return yol

    monkeypatch.setattr(cf, "gorsel_sor", sor)
    monkeypatch.setattr(cf, "gorsel", gorsel)
    k = uretim.durumlari_denetle(_durum_senaryosu(), ["i"] * 4, tmp_path, 100)
    # önce değişimden önceki son kare (1) sınanır, 0 sorulmaz
    assert sorulan == ["sahne_1.jpg", "sahne_2.jpg", "sahne_2.jpg", "sahne_3.jpg", "sahne_3.jpg"]
    assert k == {"soru": 5, "yeniden": 2, "tutmayan": {}, "hata": 0, "ayirmayan": []} and tohumlar == [128, 138]

    # yeniden çizim de tutmazsa hak bitince hikâye düşer; az emin cevap kareyi reddetmez
    monkeypatch.setattr(cf, "gorsel", lambda istem, yol, tohum: yol.write_bytes(b"kuyruklu") and yol)
    for i in range(4):
        (tmp_path / f"sahne_{i}.jpg").write_bytes(b"kuyruklu")
    with pytest.raises(uretim.DurumHatasi, match="tutmadı"):
        uretim.durumlari_denetle(_durum_senaryosu(), ["i"] * 4, tmp_path, 100)
    monkeypatch.setattr(cf, "gorsel_sor", lambda yol, soru: (True, 0.4))
    assert uretim.durumlari_denetle(_durum_senaryosu(), ["i"] * 4, tmp_path, 100)["yeniden"] == 0

    # değişimden önceki karede de beklenen cevap çıkıyor: soru ayırt etmiyor (ya da expected ters), denetlenmez
    monkeypatch.setattr(cf, "gorsel_sor", lambda yol, soru: (False, 0.9))
    k = uretim.durumlari_denetle(_durum_senaryosu(), ["i"] * 4, tmp_path, 100)
    assert k["ayirmayan"] == [KUYRUK["question"]] and k["soru"] == 1 and k["yeniden"] == 0


def test_gorme_modeli_yanit_vermezse_kare_denetlenmemis_sayilir_kota_yukari_firlar(tmp_path, monkeypatch):
    from otomat.hikaye import cf

    for i in range(4):
        (tmp_path / f"sahne_{i}.jpg").write_bytes(b"x")

    def hata(yol, soru):
        raise cf.CFHatasi("yanıt yok")

    monkeypatch.setattr(cf, "gorsel_sor", hata)
    assert uretim.durumlari_denetle(_durum_senaryosu(), ["i"] * 4, tmp_path, 0)["hata"] == 3  # sınama + 2 kare

    def kota(yol, soru):
        raise cf.KotaHatasi("kota")

    monkeypatch.setattr(cf, "gorsel_sor", kota)
    with pytest.raises(cf.KotaHatasi):
        uretim.durumlari_denetle(_durum_senaryosu(), ["i"] * 4, tmp_path, 0)


def test_degisen_gorunus_tutmayan_hikaye_duser_siradaki_denenir(tmp_path, monkeypatch):
    from otomat import durum, gunluk
    from otomat.hikaye import kabul
    from otomat.hikaye import uretim as h_uretim

    db = durum.baglan(tmp_path / "d.db")
    paketler = [type("P", (), {"anahtar": f"ezop:{i}", "hash": f"h{i}", "kol": "k", "tur": "t"})() for i in range(2)]
    sira = iter(paketler)
    monkeypatch.setattr(gunluk, "sec", lambda *a: (next(sira), "kalip", "sablon", {}))
    monkeypatch.setattr(gunluk, "KOK", tmp_path)
    monkeypatch.setattr(kabul, "denetle", lambda *a: [])

    def uret(paket, *a):
        if paket.anahtar == "ezop:0":
            raise h_uretim.DurumHatasi("değişen görünüş karede tutmadı: {'2': 'tail?'}")
        return {"baslik": "ok"}

    monkeypatch.setattr(h_uretim, "uret", uret)
    kayit = {}
    paket, *_ = gunluk.hikaye_uret([], db, dt.date(2026, 10, 13), kayit)
    assert paket.anahtar == "ezop:1" and "tutmadı" in kayit["dusen_hikayeler"][0]["sorunlar"][0]
