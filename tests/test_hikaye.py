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

    def __init__(self, ad, aciklama="", mfk=False):
        self.oge = {"id": "UC1", "snippet": {"title": ad}, "brandingSettings": {"channel": {"description": aciklama}},
                    "status": {"selfDeclaredMadeForKids": mfk}}  # fmt: skip
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


def test_marka_ad_degisene_kadar_bekler(kanal_sec):
    from otomat.yayin import marka

    kanal_sec("uzay")
    yt = _SahteKanal("Orbit Ruler")
    assert marka.kontrol(yt) == "ad bekleniyor" and yt.guncellemeler == []
    m = marka.ayarlar()
    yt = _SahteKanal("Lanternbug Tales", m["aciklama"]["en"], mfk=True)
    assert marka.kontrol(yt) == "tamam" and yt.guncellemeler == []
    assert (marka.KOK / m["banner"]).exists() and (marka.KOK / m["filigran"]).exists()


def test_marka_yedek_adla_da_uygulanir(kanal_sec, monkeypatch):
    from otomat.yayin import marka

    kanal_sec("earth")
    uygulanan = []
    monkeypatch.setattr(marka, "uygula", lambda yt, oge, m: uygulanan.append(oge["snippet"]["title"]))
    assert marka.kontrol(_SahteKanal("Inkwell Oddities Stories")) == "uygulandı"  # YouTube asıl adı reddetti
    assert marka.kontrol(_SahteKanal("Earth in Numbers")) == "ad bekleniyor"
    assert uygulanan == ["Inkwell Oddities Stories"]


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
