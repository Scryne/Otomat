"""USGS deprem adaptörü (FDSN olay servisi, kamu malı).

`indir` ham GeoJSON'u getirir; `paketler` saf fonksiyondur (kayıtlı yanıtla test edilir).
"""

import datetime as dt
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from otomat.veri import Kaynak, Olgu, OlguPaketi
from otomat.veri.adlar import goster
from otomat.veri.http import json_al

SERVIS = "https://earthquake.usgs.gov/fdsnws/event/1/query"
LISANS = "public domain"
ASGARI_ULKE_OLAYI = 25
_YON = re.compile(
    r"^(?:\d+\s*km\s+)?(?:(?:north|south|east|west|northern|southern|eastern|western|central|off the coast of)"
    r"[\w\s-]*?\s+of\s+|near the coast of\s+|off the coast of\s+)?(?:the\s+)?",
    re.I,
)


@dataclass(frozen=True)
class Deprem:
    zaman: float  # unix saniye
    boylam: float
    enlem: float
    buyukluk: float
    bolge: str


_OKYANUS = re.compile(
    r"\b(Ridge|Rise|Passage|Ocean|Sea|Basin|Trench|Gulf|Strait|Fracture Zone|Junction|Channel)\b|^[a-z]"
)


def bolge(yer: str | None) -> str:
    """'80 km ENE of Tadine, New Caledonia' -> 'New Caledonia'; 'south of the Fiji Islands' -> 'Fiji'."""
    if not yer:
        return "Unknown"
    ad = yer.rsplit(",", 1)[1].strip() if "," in yer else (_YON.sub("", yer.strip()).strip() or yer.strip())
    ad = re.sub(r"\s+region$", "", ad)
    return goster(ad)


def kara_mi(bolge_adi: str) -> bool:
    """Okyanus sırtı, geçit vb. 'senin ülken' çerçevesine girmez."""
    return bolge_adi != "Unknown" and not _OKYANUS.search(bolge_adi)


def sorgu_url(baslangic: dt.date, bitis: dt.date, min_buyukluk: float = 4.5) -> str:
    return (
        f"{SERVIS}?format=geojson&starttime={baslangic.isoformat()}&endtime={bitis.isoformat()}"
        f"&minmagnitude={min_buyukluk}&orderby=time-asc"
    )


def indir(gun: int = 365, min_buyukluk: float = 4.5, bugun: dt.date | None = None) -> tuple[dict, str]:
    bugun = bugun or dt.datetime.now(dt.UTC).date()
    url = sorgu_url(bugun - dt.timedelta(days=gun), bugun + dt.timedelta(days=1), min_buyukluk)
    return json_al(url, zaman_asimi=120), url


def depremler(geojson: dict) -> list[Deprem]:
    sonuc = []
    for f in geojson["features"]:
        p = f["properties"]
        if p.get("mag") is None or p.get("type", "earthquake") != "earthquake":
            continue
        boylam, enlem, _ = f["geometry"]["coordinates"]
        sonuc.append(Deprem(p["time"] / 1000, boylam, enlem, round(p["mag"], 1), bolge(p.get("place"))))
    return sorted(sonuc, key=lambda d: d.zaman)


def _yuzde(x: float) -> int | float:
    """%10 ve üstü tam sayı, altı tek ondalık (küçük bölgeler '%0' görünmesin)."""
    return int(round(x)) if x >= 10 else round(x, 1)


def _gun_ay_yil(t: float) -> str:
    d = dt.datetime.fromtimestamp(t, dt.UTC)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def _kutu(olaylar: list[Deprem], pay: float = 4.0) -> dict:
    boylamlar = [d.boylam for d in olaylar]
    kaydir = max(boylamlar) - min(boylamlar) > 180
    if kaydir:
        boylamlar = [b + 360 if b < 0 else b for b in boylamlar]
    enlemler = [d.enlem for d in olaylar]
    return {
        "boylam": [min(boylamlar) - pay, max(boylamlar) + pay],
        "enlem": [max(min(enlemler) - pay, -85), min(max(enlemler) + pay, 85)],
        "boylam_kaydir": kaydir,
    }


def _noktalar(olaylar: list[Deprem]) -> list[list[float]]:
    return [[d.zaman, d.boylam, d.enlem, d.buyukluk] for d in olaylar]


def paketler(geojson: dict, url: str, cekildi: str, gun: int = 365) -> list[OlguPaketi]:
    tum = depremler(geojson)
    if not tum:
        return []
    son = tum[-1].zaman
    kaynak = Kaynak("USGS", url, LISANS, cekildi)
    sonuc: list[OlguPaketi] = []

    # 1) Son 30 gün, dünya geneli
    otuz = [d for d in tum if d.zaman >= son - 30 * 86400]
    if otuz:
        en = max(otuz, key=lambda d: d.buyukluk)
        bol, bol_sayi = Counter(d.bolge for d in otuz).most_common(1)[0]
        sonuc.append(
            OlguPaketi(
                kol="usgs",
                tur="dunya_30g",
                anahtar=f"usgs:dunya_30g:{_gun_ay_yil(son)}",
                konu="every strong earthquake on Earth in the last 30 days",
                olgular={
                    "total_quakes": Olgu(len(otuz), "number of earthquakes of magnitude 4.5 or more worldwide"),
                    "days": Olgu(30, "length of the period in days", "days"),
                    "strongest_magnitude": Olgu(en.buyukluk, "magnitude of the strongest earthquake"),
                    "strongest_region": Olgu(en.bolge, "region of the strongest earthquake"),
                    "top_region": Olgu(bol, "region with the most earthquakes"),
                    "top_region_count": Olgu(bol_sayi, "number of earthquakes in top_region"),
                    "quakes_above_6": Olgu(sum(d.buyukluk >= 6 for d in otuz), "earthquakes of magnitude 6 or more"),
                },
                gorsel={"sablon": "nokta_harita", "olaylar": _noktalar(otuz), "kutu": None},
                kaynak=kaynak,
                etiketler=["earthquake", "world"],
            )
        )

    # 2) Bölge bazında bir yıl
    bolgeler: dict[str, list[Deprem]] = defaultdict(list)
    for d in tum:
        bolgeler[d.bolge].append(d)
    for ad, olaylar in sorted(bolgeler.items(), key=lambda x: -len(x[1])):
        if len(olaylar) < ASGARI_ULKE_OLAYI or not kara_mi(ad):
            continue
        en = max(olaylar, key=lambda d: d.buyukluk)
        aylar = Counter(dt.datetime.fromtimestamp(d.zaman, dt.UTC).strftime("%B %Y") for d in olaylar)
        yogun_ay, yogun_sayi = aylar.most_common(1)[0]
        sonuc.append(
            OlguPaketi(
                kol="usgs",
                tur="bolge_yillik",
                anahtar=f"usgs:bolge_yillik:{ad}",
                konu=f"every strong earthquake in {ad} over the past year",
                olgular={
                    "region": Olgu(ad, "the country or region of this video"),
                    "quake_count": Olgu(len(olaylar), "earthquakes of magnitude 4.5 or more in region"),
                    "days": Olgu(gun, "length of the period in days", "days"),
                    "strongest_magnitude": Olgu(en.buyukluk, "magnitude of the strongest earthquake in region"),
                    "strongest_date": Olgu(_gun_ay_yil(en.zaman), "date of the strongest earthquake in region"),
                    "share_of_world_pct": Olgu(
                        _yuzde(100 * len(olaylar) / len(tum)),
                        "region's share of all such earthquakes worldwide",
                        "%",
                    ),
                    "busiest_month": Olgu(yogun_ay, "month with the most earthquakes in region"),
                    "busiest_month_count": Olgu(yogun_sayi, "number of earthquakes in busiest_month"),
                },
                gorsel={"sablon": "nokta_harita", "olaylar": _noktalar(olaylar), "kutu": _kutu(olaylar)},
                kaynak=kaynak,
                etiketler=["earthquake", ad],
            )
        )

    # 3) Yılın en güçlü 10 depremi
    ilk10 = sorted(tum, key=lambda d: (-d.buyukluk, d.zaman))[:10]
    olgular = {
        "days": Olgu(gun, "length of the period in days", "days"),
        "quakes_above_7": Olgu(sum(d.buyukluk >= 7 for d in tum), "earthquakes of magnitude 7 or more in the period"),
    }
    for i, d in enumerate(ilk10[:3], 1):
        olgular[f"rank{i}_region"] = Olgu(d.bolge, f"region of the number {i} strongest earthquake")
        olgular[f"rank{i}_magnitude"] = Olgu(d.buyukluk, f"magnitude of the number {i} strongest earthquake")
    sonuc.append(
        OlguPaketi(
            kol="usgs",
            tur="en_guclu_10",
            anahtar=f"usgs:en_guclu_10:{_gun_ay_yil(son)}",
            konu="the 10 strongest earthquakes of the past year",
            olgular=olgular,
            gorsel={
                "sablon": "sirali_cubuk",
                "ogeler": [{"etiket": d.bolge, "deger": d.buyukluk, "not": _gun_ay_yil(d.zaman)} for d in ilk10],
                "birim": "magnitude",
                "ondalik": 1,
            },
            kaynak=kaynak,
            etiketler=["earthquake", "ranking"],
        )
    )
    return sonuc
