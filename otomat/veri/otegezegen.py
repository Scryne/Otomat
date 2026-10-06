"""NASA Exoplanet Archive adaptörü (TAP, `pscomppars`): ötegezegen boyutu ve sıralamaları (uzay kanalı).

Yalnız **transit** yöntemiyle bulunmuş, tartışmalı olmayan ve yarıçapı ölçülmüş (hata payı yayımlanmış) gezegenler:
boyut iddiası ölçüme dayansın, kütleden türetilmiş yarıçap girmesin. Arşiv atıf metni zorunludur (aciklama'da).

`indir` ham satırları getirir; `paketler` saf fonksiyondur (kayıtlı yanıtla test edilir).
"""

import datetime as dt
import urllib.parse

from otomat.veri import Kaynak, Olgu, OlguPaketi
from otomat.veri.http import json_al

TAP = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
SAYFA = "https://exoplanetarchive.ipac.caltech.edu/"
LISANS = "NASA Exoplanet Archive"
ATIF = (
    "This research has made use of the NASA Exoplanet Archive, which is operated by the California Institute of "
    "Technology, under contract with NASA under the Exoplanet Exploration Program."
)
ALANLAR = "pl_name,hostname,sy_dist,pl_rade,pl_orbper,pl_eqt,disc_year,disc_pubdate,disc_facility"
PC_ISIK_YILI = 3.26156
JUPITER_RE = 11.21  # Jüpiter yarıçapı, Dünya yarıçapı cinsinden
NEPTUN_RE = 3.88
LISTE = 8
YENI_AY = 6  # "yeni keşif" penceresi (yayın tarihine göre ay)


def sorgu() -> str:
    return (
        f"select {ALANLAR} from pscomppars where discoverymethod = 'Transit' and pl_controv_flag = 0 "
        "and pl_rade is not null and pl_radeerr1 is not null and sy_dist is not null"
    )


def indir() -> tuple[list[dict], str]:
    url = f"{TAP}?" + urllib.parse.urlencode({"query": sorgu(), "format": "json"})
    return json_al(url, zaman_asimi=120), url


def _isik_yili(pc: float) -> int:
    ly = pc * PC_ISIK_YILI
    return int(round(ly, -1)) if ly >= 100 else int(round(ly))


def _sicaklik_c(k: float | None) -> int | None:
    return None if k is None else int(round(k - 273.15, -1))


def _yaricap(re_: float) -> float:
    return round(re_, 1) if re_ < 10 else round(re_)


def _gun(p: float) -> float:
    return round(p, 1) if p < 10 else round(p)


def _ozellikler(g: dict) -> dict[str, Olgu]:
    o = {
        "planet": Olgu(g["pl_name"], "the planet's name"),
        "star": Olgu(g["hostname"], "the star it orbits"),
        "distance_ly": Olgu(_isik_yili(g["sy_dist"]), "distance from Earth", "light-years"),
        "radius_earths": Olgu(_yaricap(g["pl_rade"]), "measured radius, in Earth radii", "times Earth's width"),
        "discovery_year": Olgu(g["disc_year"], "year the discovery was published"),
    }
    if g.get("pl_orbper"):
        o["year_days"] = Olgu(_gun(g["pl_orbper"]), "time to orbit its star once (its year)", "days")
    if (c := _sicaklik_c(g.get("pl_eqt"))) is not None:
        o["temperature_c"] = Olgu(c, "estimated equilibrium temperature, rounded", "°C")
    return o


def _boyut_sinifi(re_: float) -> str:
    if re_ < 1.25:
        return "about the size of Earth"
    if re_ < 2:
        return "a bit larger than Earth"
    if re_ < 6:
        return "Neptune-sized"
    return "Jupiter-sized or larger"


def paketler(satirlar: list[dict], url: str, cekildi: str, bugun: dt.date) -> list[OlguPaketi]:
    gez = [g for g in satirlar if g.get("pl_rade") and g.get("sy_dist")]
    if not gez:
        return []
    kaynak = Kaynak("NASA Exoplanet Archive", url, LISANS, cekildi)
    sonuc: list[OlguPaketi] = []

    def tekil(g: dict, aci: str, konu: str) -> OlguPaketi:
        o = _ozellikler(g)
        o["size_class"] = Olgu(_boyut_sinifi(g["pl_rade"]), "size class, from the measured radius")
        return OlguPaketi(
            kol="otegezegen",
            tur="gezegen_tekil",
            anahtar=f"otegezegen:gezegen_tekil:{g['pl_name']}",
            konu=konu,
            olgular=o,
            gorsel={
                "sablon": "olcek",
                "kip": "gezegen",
                "ad": g["pl_name"],
                "yaricap": g["pl_rade"],
                "aci": aci,
            },
            kaynak=kaynak,
            etiketler=["exoplanet", g["hostname"], "space"],
        )

    # 1) Tekil gezegenler: en yakınlar, yeni keşifler, Dünya boyutundakiler
    yakin = sorted(gez, key=lambda g: g["sy_dist"])[:20]
    for g in yakin:
        sonuc.append(tekil(g, "yakin", f"the exoplanet {g['pl_name']}, one of the closest known transiting planets"))
    sinir = (bugun.replace(day=1) - dt.timedelta(days=31 * YENI_AY)).strftime("%Y-%m")
    for g in sorted((g for g in gez if (g.get("disc_pubdate") or "") >= sinir), key=lambda g: g["sy_dist"])[:20]:
        sonuc.append(tekil(g, "yeni", f"the recently announced exoplanet {g['pl_name']}"))
    dunya_gibi = [g for g in gez if 0.8 <= g["pl_rade"] <= 1.25 and g.get("pl_eqt") and g["pl_eqt"] < 400]
    for g in sorted(dunya_gibi, key=lambda g: g["sy_dist"])[:15]:
        sonuc.append(tekil(g, "dunya_boyu", f"the Earth-sized exoplanet {g['pl_name']}"))

    # 2) Sıralamalar. "En büyük" bilerek yok: listenin tepesi (~2,5 Jüpiter) şişkin ya da sıyırma geçişli ölçümler.
    def liste(tur: str, anahtar_alan: str, ters: bool, konu: str, birim: str, deger, sistem_basi: bool = False):
        aday = [g for g in gez if g.get(anahtar_alan) is not None]
        sirali = sorted(aday, key=lambda g: g[anahtar_alan], reverse=ters)
        if sistem_basi:  # aynı yıldızın gezegenleri listeyi doldurmasın
            yildizlar: set[str] = set()
            sirali = [g for g in sirali if not (g["hostname"] in yildizlar or yildizlar.add(g["hostname"]))]
        ilk = sirali[:LISTE]
        degerler = [deger(g) for g in ilk]
        if len(ilk) < LISTE or len(set(degerler[:4])) < 4:  # ilk 4 gösterimde ayrışmıyorsa sahte sıra olur
            return
        olgular = {
            "planets_compared": Olgu(len(aday), "planets in this comparison"),
            "comparison_scope": Olgu(
                "planets seen crossing their star, with a measured size", "which planets this ranking covers"
            ),
        }
        for i, g in enumerate(ilk[:3], 1):
            olgular[f"rank{i}_planet"] = Olgu(g["pl_name"], f"the number {i} planet in this ranking")
            olgular[f"rank{i}_value"] = Olgu(degerler[i - 1], f"the number {i} planet's value", birim)
            if sistem_basi:
                olgular[f"rank{i}_star"] = Olgu(g["hostname"], f"the star of the number {i} planet")
        sonuc.append(
            OlguPaketi(
                kol="otegezegen",
                tur=tur,
                anahtar=f"otegezegen:{tur}:{bugun.year}",
                konu=konu,
                olgular=olgular,
                gorsel={
                    "sablon": "olcek",
                    "kip": "gezegen_liste",
                    "ogeler": [
                        {"ad": g["pl_name"], "yaricap": g["pl_rade"], "deger": d, "birim": birim}
                        for g, d in zip(ilk, degerler, strict=True)
                    ],
                },
                kaynak=kaynak,
                etiketler=["exoplanet", "ranking", "space"],
            )
        )

    liste(
        "en_yakin_8",
        "sy_dist",
        False,
        "the closest star systems with a planet seen crossing its star",
        "light-years",
        lambda g: round(g["sy_dist"] * PC_ISIK_YILI, 1),
        sistem_basi=True,
    )
    liste(
        "en_sicak_8",
        "pl_eqt",
        True,
        "the hottest planets seen crossing their star (estimated temperature)",
        "°C",
        lambda g: _sicaklik_c(g["pl_eqt"]),
    )
    liste(
        "en_kisa_yil_8",
        "pl_orbper",
        False,
        "the planets with the shortest years, among planets seen crossing their star",
        "hours",
        lambda g: round(g["pl_orbper"] * 24, 1),
    )
    # aynı gezegen birden çok açıdan gelebilir (yakın + Dünya boyu): ilk açı kalır, seçimde ağırlığı şişmesin
    gorulen: set[str] = set()
    return [p for p in sonuc if not (p.anahtar in gorulen or gorulen.add(p.anahtar))]
