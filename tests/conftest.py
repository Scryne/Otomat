"""Veri motoru testleri pasif arşiv profilleriyle koşar (kanallar/veri-earth, veri-uzay): Earth ve Orbit kanalları
hikâye motoruna döndü (2026-10-08). Modüller etkin kanalı import anında okuduğu için değişken burada, ilk importtan
önce kurulur; kanalı kendisi seçen test (monkeypatch) bunu ezer."""

import os

os.environ.setdefault("OTOMAT_KANAL", "veri-earth")
