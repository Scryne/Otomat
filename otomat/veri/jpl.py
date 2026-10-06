"""NASA/JPL Close Approach Data (CAD) adaptörü: Dünya'nın yakınından geçen asteroitler (uzay kanalı).

`indir` ham yanıtı getirir; `paketler` saf fonksiyondur (kayıtlı yanıtla test edilir). API anahtarsız; JPL aynı anda
tek istek ve tanımlı User-Agent ister (http.KIMLIK).

Doğruluk çizgileri:
- CAD küçük cisimlerin çoğunda çap vermez. Çap mutlak kadirden (H) tahmin edilir ve her zaman **aralık** olarak yazılır:
  D = 1329 km / √p × 10^(−H/5), yansıtma oranı p = 0,25 (küçük uç) ile 0,05 (büyük uç). Videoda "estimated".
- Mesafe, yaklaşımın nominal en yakın mesafesidir; "Ay mesafesi" (LD) = 384.400 km.
- Paketler tehlike/çarpma iddiası taşımaz; yalnız mesafe, tarih, hız ve tahmini boyut.
"""

import datetime as dt
import math
from dataclasses import dataclass

from otomat.veri import Kaynak, Olgu, OlguPaketi
from otomat.veri.http import json_al

SERVIS = "https://ssd-api.jpl.nasa.gov/cad.api"
SAYFA = "https://cneos.jpl.nasa.gov/ca/"
LISANS = "NASA/JPL, public data"
AU_KM = 149_597_870.7
LD_KM = 384_400.0
ONCE_GUN, SONRA_GUN = 3, 7  # pencere: üretim gününden 3 gün önce .. 7 gün sonra (yayın ~1 gün sonra)
MAKS_AU = 0.05  # ~19,5 LD
TEKIL_LD = 2.0  # tek asteroit videosu: Ay mesafesinin en çok 2 katı
TEKIL_EN_COK = 4
LISTE_EN_COK = 8


@dataclass(frozen=True)
class Gecis:
    ad: str  # "2026 TZ"
    an: dt.datetime  # UTC (CAD zamanı TDB; dakika farkı tarih için önemsiz)
    ld: float  # nominal en yakın mesafe, Ay mesafesi cinsinden
    km: float
    hiz: float  # km/s, Dünya'ya göre
    h: float  # mutlak kadir

    @property
    def cap_m(self) -> tuple[int, int]:
        """Tahmini çap aralığı (m), iki anlamlı basamağa yuvarlanmış."""
        return _yuvarla(_cap_km(self.h, 0.25) * 1000), _yuvarla(_cap_km(self.h, 0.05) * 1000)


def _cap_km(h: float, p: float) -> float:
    return 1329 / math.sqrt(p) * 10 ** (-h / 5)


def _yuvarla(x: float) -> int:
    if x < 10:
        return max(1, round(x))
    b = 10 ** (int(math.log10(x)) - 1)
    return int(round(x / b) * b)


def sorgu_url(bas: dt.date, son: dt.date) -> str:
    return f"{SERVIS}?date-min={bas.isoformat()}&date-max={son.isoformat()}&dist-max={MAKS_AU}&sort=date"


def indir(bugun: dt.date | None = None) -> tuple[dict, str]:
    bugun = bugun or dt.datetime.now(dt.UTC).date()
    url = sorgu_url(bugun - dt.timedelta(days=ONCE_GUN), bugun + dt.timedelta(days=SONRA_GUN))
    return json_al(url, zaman_asimi=90), url


def gecisler(ham: dict) -> list[Gecis]:
    alan = {a: i for i, a in enumerate(ham.get("fields", []))}
    sonuc = []
    for r in ham.get("data") or []:
        if r[alan["h"]] is None:
            continue
        an = dt.datetime.strptime(r[alan["cd"]], "%Y-%b-%d %H:%M").replace(tzinfo=dt.UTC)
        km = float(r[alan["dist"]]) * AU_KM
        sonuc.append(Gecis(r[alan["des"]], an, km / LD_KM, km, float(r[alan["v_rel"]]), float(r[alan["h"]])))
    return sorted(sonuc, key=lambda g: g.an)


def _tarih(an: dt.datetime) -> str:
    return f"{an.strftime('%B')} {an.day}"


def _ld(x: float) -> float:
    return round(x, 2) if x < 1 else round(x, 1)


def _km(x: float) -> int:
    return _yuvarla(x) if x < 1000 else int(round(x, -3))


def _ozellikler(g: Gecis, on: str = "") -> dict[str, Olgu]:
    kucuk, buyuk = g.cap_m
    return {
        f"{on}name": Olgu(g.ad, "the asteroid's official designation"),
        f"{on}date": Olgu(_tarih(g.an), "date of its closest approach to Earth (UTC)"),
        f"{on}distance_ld": Olgu(
            _ld(g.ld), "closest distance, in multiples of the Earth-Moon distance", "Moon distances"
        ),
        f"{on}distance_km": Olgu(_km(g.km), "closest distance from Earth's center", "km"),
        f"{on}speed_kms": Olgu(round(g.hiz, 1), "speed relative to Earth", "km/s"),
        f"{on}size_min_m": Olgu(kucuk, "smallest estimated width (from brightness)", "m"),
        f"{on}size_max_m": Olgu(buyuk, "largest estimated width (from brightness)", "m"),
    }


def _gorsel(gecisler_: list[Gecis], vurgu: int = 0) -> dict:
    return {
        "sablon": "yakin_gecis",
        "gecisler": [
            {
                "ad": g.ad,
                "an": g.an.isoformat(),
                "ld": round(g.ld, 3),
                "tarih": _tarih(g.an),
                "cap": list(g.cap_m),
                "hiz": round(g.hiz, 1),
            }
            for g in gecisler_
        ],
        "vurgu": vurgu,
    }


def paketler(ham: dict, url: str, cekildi: str, bugun: dt.date) -> list[OlguPaketi]:
    tum = gecisler(ham)
    if not tum:
        return []
    kaynak = Kaynak("NASA/JPL CNEOS", url, LISANS, cekildi)
    sonuc: list[OlguPaketi] = []
    yil, hafta, _ = bugun.isocalendar()

    # 1) Pencerenin en yakın geçişleri (haftada bir açı)
    yakin = sorted(tum, key=lambda g: g.ld)[:LISTE_EN_COK]
    if len(yakin) >= 3:
        en = yakin[0]
        olgular = {
            "flyby_count": Olgu(len(tum), "asteroids passing within about 20 Moon distances in this period"),
            "closer_than_moon": Olgu(sum(g.ld < 1 for g in tum), "of those, how many came closer than the Moon"),
            "period_start": Olgu(_tarih(tum[0].an), "first day of the period"),
            "period_end": Olgu(_tarih(tum[-1].an), "last day of the period"),
            **_ozellikler(en, "closest_"),
        }
        sonuc.append(
            OlguPaketi(
                kol="jpl",
                tur="yakin_gecis_liste",
                anahtar=f"jpl:yakin_gecis_liste:{yil}-H{hafta:02d}",
                konu="the asteroids that pass closest to Earth over ten days",
                olgular=olgular,
                gorsel=_gorsel(yakin),
                kaynak=kaynak,
                etiketler=["asteroid", "near earth object", "space"],
            )
        )

    # 2) Tek asteroit: Ay'ın birkaç katı içinden geçenler, en yakından başlayarak
    for g in sorted((g for g in tum if g.ld <= TEKIL_LD), key=lambda g: g.ld)[:TEKIL_EN_COK]:
        sonuc.append(
            OlguPaketi(
                kol="jpl",
                tur="yakin_gecis_tekil",
                anahtar=f"jpl:yakin_gecis_tekil:{g.ad}:{g.an.date().isoformat()}",
                konu=f"asteroid {g.ad} passing close to Earth",
                olgular=_ozellikler(g),
                gorsel=_gorsel([g]),
                kaynak=kaynak,
                etiketler=["asteroid", g.ad, "space"],
            )
        )
    return sonuc
