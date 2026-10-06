"""Uzay kanalı olgu cümleleri (K-4): yakın geçen asteroitler ve ötegezegenler. Sayı ve ad yalnız olgu paketinden.

Doğruluk çizgileri: çap her zaman "estimated" ve aralık; çarpma/tehlike dili yok; ötegezegen sıralamaları kapsamını
söyler ("planets seen crossing their star"), "en yakın ötegezegen" gibi genel üstünlük iddiası kurmaz.
Her tip 5 varyant; seçim olgu_cumleleri.cumleler'deki tohumla.
"""

from collections.abc import Callable

from otomat.gorsel.kimlik import sayi

Varyant = Callable[[dict, dict], list[str]]


def _d(o: dict, k: str, ondalik: int | None = None) -> str:
    v = o[k]
    return sayi(v, ondalik) if isinstance(v, int | float) and not isinstance(v, bool) else str(v)


def _ld(o: dict, k: str) -> str:
    v = o[k]
    return sayi(v, 2 if v < 1 else 1)


def _ay(o: dict, on: str = "") -> str:
    """Ay mesafesiyle karşılaştırma cümlesi parçası."""
    ld = o[f"{on}distance_ld"]
    if ld < 1:
        return f"closer than the Moon, at {_ld(o, on + 'distance_ld')} times the Moon's distance"
    return f"at {_ld(o, on + 'distance_ld')} times the distance to the Moon"


def _boy(o: dict, on: str = "") -> str:
    return f"{_d(o, on + 'size_min_m')} to {_d(o, on + 'size_max_m')} meters"


def _ay_sayisi(o: dict) -> str:
    n = o["closer_than_moon"]
    if n == 0:
        return "None of them came closer than the Moon."
    if n == 1:
        return "One of them came closer than the Moon."
    return f"{_d(o, 'closer_than_moon')} of them came closer than the Moon."


# --- jpl:yakin_gecis_liste --------------------------------------------------------------------
YAKIN_GECIS_LISTE: list[Varyant] = [
    lambda o, b: [
        f"Between {o['period_start']} and {o['period_end']}, {_d(o, 'flyby_count')} asteroids passed within about "
        "twenty Moon distances of Earth.",
        _ay_sayisi(o),
        f"The closest was {o['closest_name']}, on {o['closest_date']}, {_ay(o, 'closest_')}.",
        f"Its estimated size: {_boy(o, 'closest_')}.",
    ],
    lambda o, b: [
        f"{_d(o, 'flyby_count')} asteroids flew past Earth from {o['period_start']} to {o['period_end']}.",
        f"{o['closest_name']} came nearest, {_ay(o, 'closest_')}.",
        f"That is {_d(o, 'closest_distance_km')} kilometers from Earth's center.",
        f"It is estimated at {_boy(o, 'closest_')} across.",
    ],
    lambda o, b: [
        f"Here are the closest asteroid flybys from {o['period_start']} to {o['period_end']}.",
        "Each line marks one asteroid's closest distance; the white ring is the Moon's orbit.",
        f"Number one: {o['closest_name']}, on {o['closest_date']}, {_ay(o, 'closest_')}.",
        f"It moved at {_d(o, 'closest_speed_kms', 1)} kilometers per second.",
    ],
    lambda o, b: [
        f"In these days, {_d(o, 'flyby_count')} known asteroids passed near Earth.",
        _ay_sayisi(o),
        f"The nearest, {o['closest_name']}, is an estimated {_boy(o, 'closest_')} wide.",
        f"It passed on {o['closest_date']}, {_ay(o, 'closest_')}.",
    ],
    lambda o, b: [
        f"The white ring is the Moon's orbit. Watch {_d(o, 'flyby_count')} asteroids pass by.",
        f"The closest, {o['closest_name']}, came {_ay(o, 'closest_')}.",
        f"Speed: {_d(o, 'closest_speed_kms', 1)} kilometers per second. Estimated size: {_boy(o, 'closest_')}.",
    ],
]

# --- jpl:yakin_gecis_tekil --------------------------------------------------------------------
YAKIN_GECIS_TEKIL: list[Varyant] = [
    lambda o, b: [
        f"On {o['date']}, asteroid {o['name']} passed Earth {_ay(o)}.",
        f"That is {_d(o, 'distance_km')} kilometers from Earth's center.",
        f"It was moving at {_d(o, 'speed_kms', 1)} kilometers per second.",
        f"Its size is estimated at {_boy(o)}.",
    ],
    lambda o, b: [
        f"This is asteroid {o['name']}, estimated at {_boy(o)} across.",
        f"On {o['date']}, it passed {_ay(o)}.",
        f"Its speed relative to Earth: {_d(o, 'speed_kms', 1)} kilometers per second.",
    ],
    lambda o, b: [
        f"The white ring is the Moon's orbit. Asteroid {o['name']} passed {_ay(o)}.",
        f"Closest approach: {o['date']}, {_d(o, 'distance_km')} kilometers from Earth's center.",
        f"Its estimated size: {_boy(o)}.",
    ],
    lambda o, b: [
        f"How close is close? Asteroid {o['name']} passed {_ay(o)}.",
        f"It flew by on {o['date']} at {_d(o, 'speed_kms', 1)} kilometers per second.",
        f"Astronomers estimate it is {_boy(o)} wide.",
    ],
    lambda o, b: [
        f"{o['name']} is a small asteroid, estimated at {_boy(o)}.",
        f"On {o['date']}, it came within {_d(o, 'distance_km')} kilometers of Earth's center.",
        f"That is {_ay(o)}.",
        f"It was traveling at {_d(o, 'speed_kms', 1)} kilometers per second.",
    ],
]


# --- otegezegen:gezegen_tekil -----------------------------------------------------------------
def _yil(o: dict) -> list[str]:
    return [f"A year there lasts {_d(o, 'year_days', 1)} days."] if "year_days" in o else []


def _sicak(o: dict) -> list[str]:
    if "temperature_c" not in o:
        return []
    return [f"Its estimated temperature is about {_d(o, 'temperature_c')} degrees Celsius."]


def _gezegen(o: dict, govde: list[str]) -> list[str]:
    return govde + _yil(o) + _sicak(o)


GEZEGEN_TEKIL: list[Varyant] = [
    lambda o, b: _gezegen(
        o,
        [
            f"This is {o['planet']}, a planet {_d(o, 'distance_ly')} light-years away.",
            f"It is {_d(o, 'radius_earths', 1)} times as wide as Earth, {o['size_class']}.",
        ],
    ),
    lambda o, b: _gezegen(
        o,
        [
            f"{o['planet']} orbits the star {o['star']}, {_d(o, 'distance_ly')} light-years from us.",
            f"Measured as it crossed its star, it is {_d(o, 'radius_earths', 1)} times Earth's width.",
        ],
    ),
    lambda o, b: _gezegen(
        o,
        [
            f"Here is {o['planet']} next to Earth, Neptune and Jupiter, all to scale.",
            f"It is {_d(o, 'radius_earths', 1)} times as wide as Earth.",
            f"It lies {_d(o, 'distance_ly')} light-years away.",
        ],
    ),
    lambda o, b: _gezegen(
        o,
        [
            f"Found in {o['discovery_year']}, {o['planet']} is {o['size_class']}.",
            f"Its width is {_d(o, 'radius_earths', 1)} times Earth's,",
            f"and it is {_d(o, 'distance_ly')} light-years away.",
        ],
    ),
    lambda o, b: _gezegen(
        o,
        [
            f"{_d(o, 'distance_ly')} light-years away, a planet passes in front of its star, {o['star']}.",
            f"That planet, {o['planet']}, is {_d(o, 'radius_earths', 1)} times as wide as Earth.",
        ],
    ),
]


# --- otegezegen sıralamaları --------------------------------------------------------------------
def _sira(cumle_bas: str, deger: Callable[[dict, int], str]) -> list[Varyant]:
    return [
        lambda o, b: [
            f"{cumle_bas}, among {_d(o, 'planets_compared')} {o['comparison_scope']}.",
            f"Third: {o['rank3_planet']}, {deger(o, 3)}.",
            f"Second: {o['rank2_planet']}, {deger(o, 2)}.",
            f"And first: {o['rank1_planet']}, {deger(o, 1)}.",
        ],
        lambda o, b: [
            f"{cumle_bas}. Number one is {o['rank1_planet']}: {deger(o, 1)}.",
            f"Then {o['rank2_planet']}, {deger(o, 2)},",
            f"and {o['rank3_planet']}, {deger(o, 3)}.",
            f"This list covers {o['comparison_scope']}.",
        ],
        lambda o, b: [
            f"We compared {_d(o, 'planets_compared')} {o['comparison_scope']}.",
            f"{cumle_bas}, counting down.",
            f"At the top: {o['rank1_planet']}, {deger(o, 1)}.",
        ],
        lambda o, b: [
            f"{cumle_bas}.",
            f"{o['rank3_planet']} is third, {deger(o, 3)}.",
            f"{o['rank2_planet']} is second, {deger(o, 2)}.",
            f"{o['rank1_planet']} leads, {deger(o, 1)}.",
        ],
        lambda o, b: [
            f"Out of {_d(o, 'planets_compared')} {o['comparison_scope']}: {cumle_bas.lower()}.",
            f"First place goes to {o['rank1_planet']}, {deger(o, 1)}.",
            f"{o['rank2_planet']} and {o['rank3_planet']} follow.",
        ],
    ]


def _isik_yili(o: dict, i: int) -> str:
    return f"{_d(o, f'rank{i}_value', 1)} light-years away"


def _derece(o: dict, i: int) -> str:
    return f"about {_d(o, f'rank{i}_value')} degrees Celsius"


def _saat(o: dict, i: int) -> str:
    return f"a year of {_d(o, f'rank{i}_value', 1)} hours"


HAVUZ: dict[str, list[Varyant]] = {
    "yakin_gecis_liste": YAKIN_GECIS_LISTE,
    "yakin_gecis_tekil": YAKIN_GECIS_TEKIL,
    "gezegen_tekil": GEZEGEN_TEKIL,
    "en_yakin_8": _sira("These are the closest star systems with a planet seen crossing its star", _isik_yili),
    "en_sicak_8": _sira("These are the hottest planets seen crossing their star, by estimated temperature", _derece),
    "en_kisa_yil_8": _sira("These planets seen crossing their star have the shortest years", _saat),
}
