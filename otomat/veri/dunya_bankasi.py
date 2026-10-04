"""World Bank API v2 adaptörü (WDI, CC BY 4.0)."""

import datetime as dt
from collections import defaultdict

from otomat.veri import Kaynak, OlguPaketi
from otomat.veri.adlar import goster
from otomat.veri.http import json_al
from otomat.veri.siralama import referans_yili, siralama_paketleri

API = "https://api.worldbank.org/v2"
LISANS = "CC BY 4.0"
GERI_YIL = 14


def ulkeler_indir() -> list[dict]:
    return json_al(f"{API}/country?format=json&per_page=400")[1]


def ulkeler(ham: list[dict]) -> dict[str, str]:
    """Gerçek ülkeler (bölge toplamları hariç): ISO3 -> ad."""
    return {u["id"]: goster(u["name"]) for u in ham if u["region"]["id"] != "NA"}


def gosterge_url(kod: str, bitis: int) -> str:
    return f"{API}/country/all/indicator/{kod}?format=json&per_page=20000&date={bitis - GERI_YIL}:{bitis}"


def gosterge_indir(kod: str, bitis: int | None = None) -> tuple[list[dict], str]:
    bitis = bitis or dt.datetime.now(dt.UTC).year
    url = gosterge_url(kod, bitis)
    yanit = json_al(url, zaman_asimi=120)
    if not isinstance(yanit, list) or len(yanit) < 2 or yanit[1] is None:
        raise RuntimeError(f"World Bank yanıtı beklenmedik: {kod}: {str(yanit)[:200]}")
    return yanit[1], url


def yil_tablosu(kayitlar: list[dict], gecerli: dict[str, str]) -> dict[int, dict[str, float]]:
    tablo: dict[int, dict[str, float]] = defaultdict(dict)
    for k in kayitlar:
        iso = k.get("countryiso3code")
        if k.get("value") is None or iso not in gecerli:
            continue
        tablo[int(k["date"])][iso] = float(k["value"])
    return dict(tablo)


def paketler(gosterge: dict, kayitlar: list[dict], gecerli: dict[str, str], url: str, cekildi: str) -> list[OlguPaketi]:
    tablo = yil_tablosu(kayitlar, gecerli)
    yil = referans_yili(tablo)
    if yil is None:
        return []
    eski_yil = yil - 10 if (yil - 10) in tablo else None
    return siralama_paketleri(
        kol="dunya_bankasi",
        kod=gosterge["kod"],
        ad=gosterge["ad"],
        birim=gosterge["birim"],
        ondalik=gosterge["ondalik"],
        yil=yil,
        degerler=tablo[yil],
        isimler=gecerli,
        kaynak=Kaynak("World Bank", url, LISANS, cekildi),
        kapsam="the world",
        eski=tablo.get(eski_yil) if eski_yil else None,
        eski_yil=eski_yil,
    )
