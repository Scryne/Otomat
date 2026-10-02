"""USGS GeoJSON'dan nokta harita olaylarına (Faz 2'de tam adaptöre dönüşecek)."""

import json
from pathlib import Path

from otomat.gorsel.nokta_harita import Olay


def olaylar(geojson: Path) -> list[Olay]:
    veri = json.loads(geojson.read_text(encoding="utf-8"))
    sonuc = []
    for f in veri["features"]:
        boylam, enlem, _ = f["geometry"]["coordinates"]
        sonuc.append(Olay(f["properties"]["time"] / 1000, boylam, enlem, f["properties"]["mag"]))
    return sonuc
