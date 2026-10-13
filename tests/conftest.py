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
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "GITHUB_STEP_SUMMARY",
):
    os.environ.pop(_ad, None)
