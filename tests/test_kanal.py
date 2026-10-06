"""Kanal profilleri: her profil motorun bildiği parçalara işaret eder; Earth in Numbers eski değerlerini korur."""

import re

import pytest
import yaml

from otomat import kanal
from otomat.ayarlar import KOK
from otomat.veri.toplayici import KAYNAKLAR
from otomat.yayin.ceviri import DILLER


@pytest.mark.parametrize("kimlik", kanal.hepsi())
def test_profil_gecerli(kimlik):
    k = kanal.yukle(kimlik)
    assert set(k.kaynaklar) <= set(KAYNAKLAR), "bilinmeyen veri kaynağı"
    assert set(k.diller) <= set(DILLER), "çevirmenin bilmediği dil"
    assert k.veri.exists() and k.tasarim.exists()
    on = re.match(r"^---\n(.*?)\n---", k.tasarim.read_text(encoding="utf-8"), re.S)
    assert on and {"colors", "typography"} <= set(yaml.safe_load(on.group(1)))
    assert 0 <= k.yayin_saati_utc < 24
    assert k.ornekler.startswith("- hook:")


def test_kanallar_birbirine_karismaz():
    profiller = [kanal.yukle(i) for i in kanal.hepsi()]
    for alan in ("ad", "durum", "raporlar", "sir_eki", "token_dosyasi"):
        degerler = [getattr(k, alan) for k in profiller]
        assert len(set(degerler)) == len(degerler), f"iki kanal aynı {alan} değerini paylaşıyor"


def test_earth_eski_duzeni_korur():
    k = kanal.yukle("earth")
    assert k.ad == "Earth in Numbers"
    assert k.durum == KOK / "durum" / "otomat.db"
    assert k.raporlar == KOK / "raporlar"
    assert k.tasarim == KOK / "DESIGN.md"
    assert k.token_degiskeni == "YT_TOKEN_JSON" and k.token_dosyasi == KOK / "sirlar" / "token.json"
    assert k.kaynaklar == ("usgs", "dunya_bankasi", "eurostat")
    assert (k.yayin_saati_utc, k.ses, k.kategori) == (14, "am_michael", "28")
    assert k.diller == ("es", "pt", "de", "fr")


def test_bilinmeyen_kanal():
    with pytest.raises(ValueError, match="kanal profili yok"):
        kanal.yukle("yok-boyle")


def test_is_akisi_matrisi_profillerle_uyumlu():
    is_akisi = yaml.safe_load((KOK / ".github" / "workflows" / "gunluk.yml").read_text(encoding="utf-8"))
    matris = is_akisi["jobs"]["uret"]["strategy"]["matrix"]["include"]
    assert matris, "matriste kanal yok"
    for satir in matris:
        k = kanal.yukle(satir["kanal"])  # profili olmayan kanal koşamaz
        assert satir["sir"] == k.sir_eki, f"{k.id}: matristeki token eki profille aynı olmalı"
    assert len({s["etiket"] for s in matris}) == len(matris), "iki kanal aynı Release önekini paylaşıyor"
