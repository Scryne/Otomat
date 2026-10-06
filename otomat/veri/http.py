"""Basit JSON indirici: tekrar deneme, zaman aşımı, kimlikli User-Agent."""

import json
import ssl
import time
import urllib.error
import urllib.request

KIMLIK = "Otomat/0.1 (open-data shorts; github.com/Scryne)"
# Windows'ta Python sistem deposu bazı kökleri (JPL) tembel yüklüyor ve doğrulama düşüyor: certifi paketi tek kaynak.
try:
    import certifi

    BAGLAM = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # pragma: no cover
    BAGLAM = ssl.create_default_context()


def json_al(url: str, deneme: int = 3, zaman_asimi: float = 60) -> object:
    hata: Exception | None = None
    for i in range(deneme):
        try:
            istek = urllib.request.Request(url, headers={"User-Agent": KIMLIK, "Accept": "application/json"})
            with urllib.request.urlopen(istek, timeout=zaman_asimi, context=BAGLAM) as yanit:
                return json.loads(yanit.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            hata = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"indirilemedi: {url}") from hata
