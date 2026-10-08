"""Hikâye motoru: havuz süzgeçleri, kod kapıları, kelime zamanlaması, kenar kırpma (Cloudflare'e gitmeden)."""

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
