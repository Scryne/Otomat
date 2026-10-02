"""Yedek kanca ve başlık: LLM kapıları geçemezse koddan, olgudan kurulur. Video her durumda üretilebilsin."""

import random

from otomat.veri import OlguPaketi

KANCALAR = {
    "soru": ["Can you guess where this happens most?", "Which place do you think tops this list?"],
    "senin_ulken": ["Is your country on this map?", "Find your country before the end."],
    "duygusal": ["The pattern here is hard to ignore.", "Watch how uneven this really is."],
    "olcek": ["Watch the numbers climb.", "The gap at the top is huge."],
}


def _bas(metin: str) -> str:
    from otomat.anlati.kapilar import baslik_duzeni

    return baslik_duzeni(metin)


def baslik(paket: OlguPaketi) -> str:
    o = {k: v.deger for k, v in paket.olgular.items()}
    if paket.tur == "dunya_30g":
        return "Every Strong Earthquake on Earth in 30 Days"
    if paket.tur == "bolge_yillik":
        return f"Every Strong Earthquake in {o['region']} This Year"
    if paket.tur == "en_guclu_10":
        return "The 10 Strongest Earthquakes of the Year"
    yer = "in the World" if o.get("scope") == "the world" else "in Europe"
    if paket.tur == "en_yuksek_10":
        return f"Highest {_bas(o['indicator'])} {yer}"[:70]
    if paket.tur == "en_dusuk_10":
        return f"Lowest {_bas(o['indicator'])} {yer}"[:70]
    if paket.tur == "en_cok_artan_10":
        return f"Where {_bas(o['indicator'])} Rose the Most"[:70]
    return _bas(paket.konu)[:70]


def kanca(kalip: str, tohum: str) -> str:
    secenek = KANCALAR[kalip]
    return secenek[random.Random(tohum).randrange(len(secenek))]
