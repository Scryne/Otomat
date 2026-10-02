"""Olgu cümleleri: koddan, şablon havuzundan (K-4). Sayı ve özel ad yalnız olgu paketinden gelir.

Her olgu tipi için en az 5 varyant var; seçim paket hash'i + tarihle tohumlanır (aynı paket aynı gün aynı metni üretir).
Varyantlar cümle sırasını ve kuruluşunu değiştirir, olgu kümesini değiştirmez.
"""

import random
from collections.abc import Callable

from otomat.gorsel.kimlik import sayi
from otomat.veri import OlguPaketi

Varyant = Callable[[dict, dict], list[str]]  # (değerler, birimler) -> cümleler


def _d(o: dict, k: str, ondalik: int | None = None) -> str:
    v = o[k]
    return sayi(v, ondalik) if isinstance(v, int | float) and not isinstance(v, bool) else str(v)


def _donem(gun: int) -> str:
    return "the past year" if gun == 365 else f"the last {gun} days"


def _birimli(o: dict, b: dict, k: str) -> str:
    from otomat.anlati.kapilar import deger_yazisi

    ondalik = o.get("__ondalik") if k.endswith(("_value", "_from", "_to")) else None
    return deger_yazisi(o[k], b.get(k, ""), ondalik)


# --- usgs:dunya_30g ---------------------------------------------------------------------------
DUNYA_30G: list[Varyant] = [
    lambda o, b: [
        f"In just {o['days']} days, Earth recorded {_d(o, 'total_quakes')} earthquakes of magnitude 4.5 or stronger.",
        f"{_d(o, 'quakes_above_6')} of them reached magnitude 6 or more.",
        f"The strongest, magnitude {_d(o, 'strongest_magnitude', 1)}, hit {o['strongest_region']}.",
        f"And no place shook more often than {o['top_region']}, with {_d(o, 'top_region_count')} quakes.",
    ],
    lambda o, b: [
        f"Every dot is an earthquake of magnitude 4.5 or more: {_d(o, 'total_quakes')} in {o['days']} days.",
        f"{o['top_region']} alone had {_d(o, 'top_region_count')} of them.",
        f"The biggest was a magnitude {_d(o, 'strongest_magnitude', 1)} near {o['strongest_region']}.",
        f"{_d(o, 'quakes_above_6')} quakes crossed magnitude 6.",
    ],
    lambda o, b: [
        f"Over the last {o['days']} days, the ground shook {_d(o, 'total_quakes')} times with magnitude 4.5 or more.",
        f"The single strongest shock, magnitude {_d(o, 'strongest_magnitude', 1)}, struck {o['strongest_region']}.",
        f"The most active place was {o['top_region']}: {_d(o, 'top_region_count')} quakes.",
        f"{_d(o, 'quakes_above_6')} of them were magnitude 6 or above.",
    ],
    lambda o, b: [
        f"{_d(o, 'total_quakes')} strong earthquakes in {o['days']} days. Here they all are.",
        f"{o['top_region']} led the list with {_d(o, 'top_region_count')}.",
        f"{_d(o, 'quakes_above_6')} reached magnitude 6 or higher,",
        f"and the strongest, a magnitude {_d(o, 'strongest_magnitude', 1)}, hit {o['strongest_region']}.",
    ],
    lambda o, b: [
        f"This is {o['days']} days of strong earthquakes on Earth: {_d(o, 'total_quakes')} of them.",
        f"The top spot for shaking was {o['top_region']}, with {_d(o, 'top_region_count')} quakes.",
        f"The largest measured magnitude {_d(o, 'strongest_magnitude', 1)}, in {o['strongest_region']}.",
        f"In total, {_d(o, 'quakes_above_6')} were magnitude 6 or more.",
    ],
]

# --- usgs:bolge_yillik ------------------------------------------------------------------------
BOLGE_YILLIK: list[Varyant] = [
    lambda o, b: [
        f"In {_donem(o['days'])}, {o['region']} recorded {_d(o, 'quake_count')} earthquakes of magnitude 4.5 or more.",
        f"That is {o['share_of_world_pct']}% of all such quakes on Earth.",
        f"The strongest, magnitude {_d(o, 'strongest_magnitude', 1)}, struck on {o['strongest_date']}.",
        f"The busiest month was {o['busiest_month']}, with {_d(o, 'busiest_month_count')} quakes.",
    ],
    lambda o, b: [
        f"Every dot is a strong earthquake in {o['region']}: {_d(o, 'quake_count')} in {_donem(o['days'])}.",
        f"{o['busiest_month']} alone brought {_d(o, 'busiest_month_count')} of them.",
        f"The biggest reached magnitude {_d(o, 'strongest_magnitude', 1)} on {o['strongest_date']}.",
        f"{o['region']} accounts for {o['share_of_world_pct']}% of the world's strong quakes.",
    ],
    lambda o, b: [
        f"{o['region']} shook {_d(o, 'quake_count')} times in {_donem(o['days'])}, each at magnitude 4.5 or more.",
        f"That's {o['share_of_world_pct']}% of every such earthquake worldwide.",
        f"Its worst month was {o['busiest_month']}: {_d(o, 'busiest_month_count')} quakes.",
        f"And the strongest, magnitude {_d(o, 'strongest_magnitude', 1)}, came on {o['strongest_date']}.",
    ],
    lambda o, b: [
        f"Here is {_donem(o['days'])} of strong earthquakes in {o['region']}.",
        f"{_d(o, 'quake_count')} quakes of magnitude 4.5 or more, {o['share_of_world_pct']}% of the global total.",
        f"On {o['strongest_date']}, the strongest one hit magnitude {_d(o, 'strongest_magnitude', 1)}.",
        f"The most active month was {o['busiest_month']}, with {_d(o, 'busiest_month_count')}.",
    ],
    lambda o, b: [
        f"How often does {o['region']} shake? {_d(o, 'quake_count')} times in {_donem(o['days'])}.",
        "Only quakes of magnitude 4.5 or more are shown.",
        f"The peak came in {o['busiest_month']}, with {_d(o, 'busiest_month_count')} quakes,",
        f"and the strongest, magnitude {_d(o, 'strongest_magnitude', 1)}, struck on {o['strongest_date']}.",
    ],
]

# --- usgs:en_guclu_10 -------------------------------------------------------------------------
EN_GUCLU_10: list[Varyant] = [
    lambda o, b: [
        f"These are the 10 strongest earthquakes of {_donem(o['days'])}.",
        f"In third place, {o['rank3_region']}, magnitude {_d(o, 'rank3_magnitude', 1)}.",
        f"Second, {o['rank2_region']}, magnitude {_d(o, 'rank2_magnitude', 1)}.",
        f"And the strongest of all: {o['rank1_region']}, magnitude {_d(o, 'rank1_magnitude', 1)}.",
    ],
    lambda o, b: [
        f"{_d(o, 'quakes_above_7')} earthquakes reached magnitude 7 or more in {_donem(o['days'])}.",
        "Here are the top 10, counting down.",
        f"Number 1 was in {o['rank1_region']}, at magnitude {_d(o, 'rank1_magnitude', 1)}.",
        f"{o['rank2_region']} and {o['rank3_region']} came second and third.",
    ],
    lambda o, b: [
        f"The 10 biggest earthquakes of {_donem(o['days'])}, from tenth to first.",
        f"Third: magnitude {_d(o, 'rank3_magnitude', 1)} in {o['rank3_region']}.",
        f"Second: magnitude {_d(o, 'rank2_magnitude', 1)} in {o['rank2_region']}.",
        f"First: magnitude {_d(o, 'rank1_magnitude', 1)} in {o['rank1_region']}.",
    ],
    lambda o, b: [
        f"Counting down the strongest earthquakes of {_donem(o['days'])}.",
        f"The top three: {o['rank3_region']}, {o['rank2_region']}, and {o['rank1_region']}.",
        f"The strongest reached magnitude {_d(o, 'rank1_magnitude', 1)}.",
        f"In all, {_d(o, 'quakes_above_7')} quakes hit magnitude 7 or higher.",
    ],
    lambda o, b: [
        f"Which earthquake was the strongest in {_donem(o['days'])}?",
        f"{o['rank3_region']} is third, at magnitude {_d(o, 'rank3_magnitude', 1)}.",
        f"{o['rank2_region']} is second, at {_d(o, 'rank2_magnitude', 1)}.",
        f"And number 1 is {o['rank1_region']}, at magnitude {_d(o, 'rank1_magnitude', 1)}.",
    ],
]


# --- siralama: en_yuksek_10 / en_dusuk_10 -----------------------------------------------------
def _yer(o: dict) -> str:
    return "in the world" if o["scope"] == "the world" else "in Europe"


def _siralama(yon: str) -> list[Varyant]:
    return [
        lambda o, b: [
            f"These are the countries {_yer(o)} with the {yon} {o['indicator']}.",
            f"Third, {o['rank3_country']}: {_birimli(o, b, 'rank3_value')}.",
            f"Second, {o['rank2_country']}: {_birimli(o, b, 'rank2_value')}.",
            f"And first, {o['rank1_country']}, at {_birimli(o, b, 'rank1_value')}.",
            f"The median across {_d(o, 'countries_compared')} countries is {_birimli(o, b, 'median_value')}.",
        ],
        lambda o, b: [
            f"{o['rank1_country']} has the {yon} {o['indicator']} {_yer(o)}: {_birimli(o, b, 'rank1_value')}.",
            f"{o['rank2_country']} follows with {_birimli(o, b, 'rank2_value')},",
            f"then {o['rank3_country']} with {_birimli(o, b, 'rank3_value')}.",
            f"For comparison, the median country sits at {_birimli(o, b, 'median_value')}.",
        ],
        lambda o, b: [
            f"Counting down the {yon} {o['indicator']} {_yer(o)}, data from {o['year']}.",
            f"Number 3 is {o['rank3_country']}, with {_birimli(o, b, 'rank3_value')}.",
            f"Number 2, {o['rank2_country']}, with {_birimli(o, b, 'rank2_value')}.",
            f"Number 1, {o['rank1_country']}: {_birimli(o, b, 'rank1_value')}.",
        ],
        lambda o, b: [
            f"We compared {_d(o, 'countries_compared')} countries {_yer(o)} by {o['indicator']}.",
            f"The median is {_birimli(o, b, 'median_value')}.",
            f"The {yon}: {o['rank1_country']} at {_birimli(o, b, 'rank1_value')},",
            f"then {o['rank2_country']} and {o['rank3_country']}.",
        ],
        lambda o, b: [
            f"Which country {_yer(o)} has the {yon} {o['indicator']}?",
            f"In {o['year']}, it was {o['rank1_country']}, at {_birimli(o, b, 'rank1_value')}.",
            f"{o['rank2_country']} was second with {_birimli(o, b, 'rank2_value')},",
            f"and {o['rank3_country']} third with {_birimli(o, b, 'rank3_value')}.",
        ],
    ]


def _artis() -> list[Varyant]:
    return [
        lambda o, b: [
            f"Where did {o['indicator']} rise the most since {o['from_year']}?",
            f"In {o['rank1_country']}, it went from {_birimli(o, b, 'rank1_from')} to {_birimli(o, b, 'rank1_to')}.",
            f"{o['rank2_country']} went from {_birimli(o, b, 'rank2_from')} to {_birimli(o, b, 'rank2_to')}.",
            f"And {o['rank3_country']}, from {_birimli(o, b, 'rank3_from')} to {_birimli(o, b, 'rank3_to')}.",
        ],
        lambda o, b: [
            f"These countries {_yer(o)} saw the biggest rise in {o['indicator']} from {o['from_year']} to "
            f"{o['to_year']}.",
            f"Number 1: {o['rank1_country']}, up from {_birimli(o, b, 'rank1_from')} to {_birimli(o, b, 'rank1_to')}.",
            f"Then {o['rank2_country']} and {o['rank3_country']}.",
        ],
        lambda o, b: [
            f"Between {o['from_year']} and {o['to_year']}, {o['indicator']} in {o['rank1_country']} climbed from "
            f"{_birimli(o, b, 'rank1_from')} to {_birimli(o, b, 'rank1_to')}.",
            f"No country {_yer(o)} rose faster.",
            f"{o['rank2_country']} was second, {o['rank3_country']} third.",
        ],
        lambda o, b: [
            f"The fastest risers in {o['indicator']} {_yer(o)} since {o['from_year']}.",
            f"Third, {o['rank3_country']}: {_birimli(o, b, 'rank3_from')} to {_birimli(o, b, 'rank3_to')}.",
            f"Second, {o['rank2_country']}: {_birimli(o, b, 'rank2_from')} to {_birimli(o, b, 'rank2_to')}.",
            f"First, {o['rank1_country']}: {_birimli(o, b, 'rank1_from')} to {_birimli(o, b, 'rank1_to')}.",
        ],
        lambda o, b: [
            f"In {o['from_year']}, {o['indicator']} in {o['rank1_country']} was {_birimli(o, b, 'rank1_from')}.",
            f"By {o['to_year']}, it was {_birimli(o, b, 'rank1_to')}, the biggest rise {_yer(o)}.",
            f"{o['rank2_country']} and {o['rank3_country']} follow.",
        ],
    ]


HAVUZ: dict[str, list[Varyant]] = {
    "dunya_30g": DUNYA_30G,
    "bolge_yillik": BOLGE_YILLIK,
    "en_guclu_10": EN_GUCLU_10,
    "en_yuksek_10": _siralama("highest"),
    "en_dusuk_10": _siralama("lowest"),
    "en_cok_artan_10": _artis(),
}


def cumleler(paket: OlguPaketi, tohum: str) -> tuple[list[str], int]:
    """Olgu cümleleri ve seçilen varyant numarası."""
    havuz = HAVUZ[paket.tur]
    i = random.Random(f"{paket.hash}:{tohum}").randrange(len(havuz))
    degerler = {k: v.deger for k, v in paket.olgular.items()}
    degerler["__ondalik"] = paket.gorsel.get("ondalik")
    birimler = {k: v.birim for k, v in paket.olgular.items()}
    return havuz[i](degerler, birimler), i
