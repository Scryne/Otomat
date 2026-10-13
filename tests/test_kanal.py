"""Kanal profilleri: her profil motorun bildiği parçalara işaret eder; Earth in Numbers eski değerlerini korur."""

import re

import pytest
import yaml

from otomat import kanal
from otomat.ayarlar import KOK
from otomat.hikaye import kaynaklar as hikaye_kaynaklari
from otomat.hikaye.senaryo import KALIPLAR as HIKAYE_KALIPLARI
from otomat.veri.toplayici import KAYNAKLAR
from otomat.yayin.ceviri import DILLER

PASIF = {"veri-earth", "veri-uzay"}  # veri motorunun arşiv profilleri (testler bunlarla koşar)


@pytest.mark.parametrize("kimlik", kanal.hepsi())
def test_profil_gecerli(kimlik):
    k = kanal.yukle(kimlik)
    assert set(k.diller) <= set(DILLER), "çevirmenin bilmediği dil"
    assert k.veri.exists() and k.tasarim.exists()
    on = re.match(r"^---\n(.*?)\n---", k.tasarim.read_text(encoding="utf-8"), re.S)
    assert on and {"colors", "typography"} <= set(yaml.safe_load(on.group(1)))
    assert 0 <= k.yayin_saati_utc < 24
    if k.tur == "hikaye":
        assert set(k.kaynaklar) <= set(hikaye_kaynaklari.KAYNAKLAR), "bilinmeyen hikâye kaynağı"
        assert set(k.kaliplar) <= set(HIKAYE_KALIPLARI), "senaryonun bilmediği açılış kalıbı"
        assert k.stil and k.muzik and (KOK / k.font).exists()
    else:
        assert k.tur == "veri"
        assert set(k.kaynaklar) <= set(KAYNAKLAR), "bilinmeyen veri kaynağı"
        assert k.ornekler.startswith("- hook:")


def test_kanallar_birbirine_karismaz():
    profiller = [kanal.yukle(i) for i in kanal.hepsi()]
    for alan in ("ad", "durum", "raporlar", "sir_eki", "token_dosyasi"):
        degerler = [getattr(k, alan) for k in profiller]
        assert len(set(degerler)) == len(degerler), f"iki kanal aynı {alan} değerini paylaşıyor"


def test_earth_eski_duzeni_korur():
    # Hikâyeye döndü ama durum, rapor ve token yolları aynı: geçmiş, analitik eşleşmesi ve secret bozulmaz
    k = kanal.yukle("earth")
    assert k.durum == KOK / "durum" / "otomat.db"
    assert k.raporlar == KOK / "raporlar"
    assert k.token_degiskeni == "YT_TOKEN_JSON" and k.token_dosyasi == KOK / "sirlar" / "token.json"
    assert (k.tur, k.kaynaklar, k.mfk) == ("hikaye", ("tuhaf",), False)
    assert k.diller == ("es", "pt", "de", "fr")
    assert k.yayin_saati_utc == 14 and kanal.yukle("uzay").yayin_saati_utc == 20  # yayın saatleri değişmedi (K-11)
    assert "Earth in Numbers" in k.eski_adlar  # Studio'da yeniden adlandırma bitene kadar yükleme sürer


def test_veri_arsivi_eski_degerleri_korur():
    # Earth'ün veri formatı profili arşivde birebir: veri motoru ileride aynı davranışla geri açılabilsin
    k = kanal.yukle("veri-earth")
    assert k.tasarim == KOK / "DESIGN.md" and k.veri == KOK / "config" / "veri.toml"
    assert k.kaynaklar == ("usgs", "dunya_bankasi", "eurostat")
    assert (k.yayin_saati_utc, k.ses, k.kategori, k.tur) == (14, "am_michael", "28", "veri")


def test_masal_kanali_genel_kitle():
    """Orbit 10-08…10-13 çocuk kanalıydı (MFK): public 3 masal videosu 0 izlenme; genel kitleye geçti (K-20)."""
    k = kanal.yukle("uzay")
    assert (k.tur, k.kaynaklar, k.mfk) == ("hikaye", ("ezop",), False)
    assert k.token_degiskeni == "YT_TOKEN_JSON_UZAY" and k.durum == KOK / "durum" / "uzay.db"


def test_bilinmeyen_kanal():
    with pytest.raises(ValueError, match="kanal profili yok"):
        kanal.yukle("yok-boyle")


def test_is_akisi_matrisi_profillerle_uyumlu():
    is_akisi = yaml.safe_load((KOK / ".github" / "workflows" / "gunluk.yml").read_text(encoding="utf-8"))
    matris = is_akisi["jobs"]["uret"]["strategy"]["matrix"]["include"]
    assert matris, "matriste kanal yok"
    for satir in matris:
        assert satir["kanal"] not in PASIF, "arşiv profili yayına çıkamaz"
        k = kanal.yukle(satir["kanal"])  # profili olmayan kanal koşamaz
        assert satir["sir"] == k.sir_eki, f"{k.id}: matristeki token eki profille aynı olmalı"
    assert len({s["etiket"] for s in matris}) == len(matris), "iki kanal aynı Release önekini paylaşıyor"


class _SahteYT:
    def __init__(self, ad):
        self.ad = ad

    def channels(self):
        return self

    def list(self, **_):
        return self

    def execute(self, **_):
        return {"items": [{"snippet": {"title": self.ad}}]}


def test_yanlis_kanalin_tokeni_reddedilir(monkeypatch):
    from otomat.yayin import youtube

    monkeypatch.setenv("OTOMAT_KANAL", "earth")

    youtube._DOGRULANDI.clear()
    with pytest.raises(youtube.YetkiHatasi, match="beklenen 'Inkwell Oddities'"):
        youtube.kanal_dogrula(_SahteYT("Orbit Ruler"))
    youtube.kanal_dogrula(_SahteYT("Earth in Numbers"))  # yeniden adlandırma bitene kadar eski ad geçer
    assert youtube.GERCEK_AD["earth"] == "Earth in Numbers"
    youtube._DOGRULANDI.clear()
    youtube.kanal_dogrula(_SahteYT("Inkwell Oddities"))
    youtube.kanal_dogrula(_SahteYT("başka"))  # süreçte bir kez doğrulanır
    youtube._DOGRULANDI.clear()
