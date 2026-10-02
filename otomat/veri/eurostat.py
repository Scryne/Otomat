"""Eurostat API adaptörü (JSON-stat 2.0, CC BY 4.0 + atıf)."""

import urllib.parse
from collections import defaultdict

from otomat.veri import Kaynak, OlguPaketi
from otomat.veri.http import json_al
from otomat.veri.siralama import referans_yili, siralama_paketleri

API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
LISANS = "CC BY 4.0 (Eurostat)"

# Eurostat iki harfli kodları ISO 3166-1'den iki yerde ayrılır: EL (Yunanistan), UK.
ISO3 = {
    "AL": "ALB", "AT": "AUT", "BA": "BIH", "BE": "BEL", "BG": "BGR", "CH": "CHE", "CY": "CYP", "CZ": "CZE",
    "DE": "DEU", "DK": "DNK", "EE": "EST", "EL": "GRC", "ES": "ESP", "FI": "FIN", "FR": "FRA", "HR": "HRV",
    "HU": "HUN", "IE": "IRL", "IS": "ISL", "IT": "ITA", "LI": "LIE", "LT": "LTU", "LU": "LUX", "LV": "LVA",
    "MD": "MDA", "ME": "MNE", "MK": "MKD", "MT": "MLT", "NL": "NLD", "NO": "NOR", "PL": "POL", "PT": "PRT",
    "RO": "ROU", "RS": "SRB", "SE": "SWE", "SI": "SVN", "SK": "SVK", "TR": "TUR", "UA": "UKR", "UK": "GBR",
    "XK": "XKX", "GE": "GEO", "AM": "ARM", "AZ": "AZE", "BY": "BLR", "RU": "RUS",
}  # fmt: skip
ISIM_DUZELT = {"Kosovo*": "Kosovo"}


def veri_url(kod: str, filtre: dict, baslangic: int) -> str:
    sorgu = {"format": "JSON", "lang": "EN", "sinceTimePeriod": str(baslangic), **filtre}
    return f"{API}/{kod}?{urllib.parse.urlencode(sorgu)}"


def indir(kod: str, filtre: dict, baslangic: int) -> tuple[dict, str]:
    url = veri_url(kod, filtre, baslangic)
    yanit = json_al(url, zaman_asimi=120)
    if "error" in yanit:
        raise RuntimeError(f"Eurostat hatası: {kod}: {yanit['error']}")
    return yanit, url


def yil_tablosu(js: dict) -> tuple[dict[int, dict[str, float]], dict[str, str]]:
    """JSON-stat -> {yıl: {ISO3: değer}}, {ISO3: ad}. geo/time dışındaki boyutlar tek değerli olmalı."""
    boyutlar, buyuklukler = js["id"], js["size"]
    for b, n in zip(boyutlar, buyuklukler, strict=True):
        if b not in ("geo", "time") and n != 1:
            raise ValueError(f"filtre eksik: '{b}' boyutunda {n} değer var")
    adim = {}
    carpan = 1
    for b, n in reversed(list(zip(boyutlar, buyuklukler, strict=True))):
        adim[b] = carpan
        carpan *= n
    geo = js["dimension"]["geo"]["category"]
    zaman = js["dimension"]["time"]["category"]["index"]
    tablo: dict[int, dict[str, float]] = defaultdict(dict)
    isimler = {}
    for kod, gi in geo["index"].items():
        if kod not in ISO3:
            continue  # EU27_2020, EA20 gibi toplamlar
        iso = ISO3[kod]
        ad = geo["label"][kod]
        isimler[iso] = ISIM_DUZELT.get(ad, ad.split(" (")[0])
        for yil, ti in zaman.items():
            deger = js["value"].get(str(gi * adim["geo"] + ti * adim["time"]))
            if deger is not None:
                tablo[int(yil[:4])][iso] = float(deger)
    return dict(tablo), isimler


def paketler(veri_seti: dict, js: dict, url: str, cekildi: str) -> list[OlguPaketi]:
    tablo, isimler = yil_tablosu(js)
    yil = referans_yili(tablo)
    if yil is None:
        return []
    eski_yil = yil - 10 if (yil - 10) in tablo else None
    return siralama_paketleri(
        kol="eurostat",
        kod=veri_seti["kod"],
        ad=veri_seti["ad"],
        birim=veri_seti["birim"],
        ondalik=veri_seti["ondalik"],
        yil=yil,
        degerler=tablo[yil],
        isimler=isimler,
        kaynak=Kaynak("Eurostat", url, LISANS, cekildi),
        kapsam="Europe",
        eski=tablo.get(eski_yil) if eski_yil else None,
        eski_yil=eski_yil,
    )
