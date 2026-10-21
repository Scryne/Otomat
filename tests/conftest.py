"""Veri motoru testleri pasif arşiv profilleriyle koşar (kanallar/veri-earth, veri-uzay): Earth ve Orbit kanalları
hikâye motoruna döndü (2026-10-08). Modüller etkin kanalı import anında okuduğu için değişken burada, ilk importtan
önce kurulur; kanalı kendisi seçen test (monkeypatch) bunu ezer.

Kabuktan gelen değerler ezilir (setdefault değil): calistir skill'i komutları `OTOMAT_KANAL=earth` ile verir, açık
kalan kabukta test koşusu 4-5 testte düşüyordu. Sırlar da silinir: bir test yanlışlıkla gerçek uca gitmesin."""

import os

os.environ["OTOMAT_KANAL"] = "veri-earth"
for _ad in (
    "OTOMAT_YAYIN",
    "OTOMAT_DURUM",
    "OTOMAT_LLM",
    "BUFFER_API_KEY",
    "OTOMAT_SITE_ANAHTAR",
    "CF_ACCOUNT_ID",
    "CF_API_TOKEN",
    "YT_ISTEMCI_JSON",
    "YT_TOKEN_JSON",
    "YT_TOKEN_JSON_UZAY",
    "YT_TOKEN_JSON_FILM",
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "GITHUB_STEP_SUMMARY",
):
    os.environ.pop(_ad, None)


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _gercek_sir_yok(monkeypatch):
    """Ortam değişkeni silmek yetmiyor: Cloudflare kimliği `sirlar/cloudflare.json`'a, YouTube token'ı `sirlar/`a,
    Buffer anahtarı `.env`'e düşüyor. Earth kart biçimine geçince (K-25) senaryosu sahtelenmiş bir test kart yoluna
    sapıp yerelde gerçek Cloudflare'e istek attı (CI'da dosya olmadığı için görünmüyordu). Gerçek uca giden her test
    burada düşer."""
    from otomat.film import yukle
    from otomat.hikaye import cf
    from otomat.yayin import buffer, youtube

    def yok(ad):
        def _yok(*a, **k):
            raise RuntimeError(f"testte gerçek {ad} kimliği kullanılamaz")

        return _yok

    monkeypatch.setattr(cf, "kimlik", yok("Cloudflare"))
    monkeypatch.setattr(youtube, "kimlik", yok("YouTube"))
    monkeypatch.setattr(buffer, "anahtar", yok("Buffer"))
    monkeypatch.setattr(yukle, "kimlik", yok("One Ticket Back"))  # film raporu ve yükleyici
