"""Harita sahnesi: Wikipedia koordinatı → HyperFrames `bake-basemap` (Esri uydu, küreden yere yakınlaştırma) → MP4.

Koordinat yazar modelinden değil Wikipedia'nın `prop=coordinates` verisinden gelir (uydurma konum olmasın). Pişirme
canlı karo ister ve kare başına ~0,9 sn sürer (6 sn klip ~2,5 dk, 11-20 ölçümü): video başına en çok 2 harita.
Ekranda kredi: "Esri, Maxar, Earthstar Geographics" (HyperFrames film.md "Maps and real places").
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import urllib.parse
from pathlib import Path

from otomat.trend import radar
from otomat.trend.kurgu import HF_ORTAM, MOTOR_DIZIN

BETIK = MOTOR_DIZIN / "node_modules/hyperframes/dist/skills/hyperframes/scripts/bake-basemap.mjs"
CHROME = os.environ.get("OTOMAT_CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
YAKINLIK = {"city": 11.0, "region": 7.5, "country": 5.0}
KREDI = "Imagery: Esri, Maxar, Earthstar Geographics"


def koordinat(baslik: str) -> tuple[float, float] | None:
    q = urllib.parse.quote(baslik.replace(" ", "_"), safe="")
    url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&formatversion=2&prop=coordinates&redirects=1&titles={q}"
    try:
        sayfa = json.loads(radar._getir(url))["query"]["pages"][0]
    except Exception:  # noqa: BLE001
        return None
    k = (sayfa.get("coordinates") or [None])[0]
    return (float(k["lon"]), float(k["lat"])) if k else None


def pisir(lng: float, lat: float, yakinlik: str, sure: float, dizin: Path) -> Path:
    """Küreden hedefe uçuş: ilk %60'ta yakınlaşır, kalan sürede hedefte durur (pin ve etiket o zaman gelir)."""
    zend = YAKINLIK.get(yakinlik, 11.0)
    anahtar = hashlib.sha1(f"{lng:.4f},{lat:.4f},{zend},{sure:.2f}".encode()).hexdigest()[:10]
    hedef = dizin / f"harita-{anahtar}.mp4"
    if hedef.exists():
        return hedef
    dizin.mkdir(parents=True, exist_ok=True)
    kaynak_lng = lng + 40 if lng < 100 else lng - 40
    ortam = {**os.environ, **HF_ORTAM, "CHROME": CHROME, "NAME": hedef.stem, "STYLE": "satellite",
             "PROJECTION": "globe", "FROM": f"{kaynak_lng:.3f},{max(-60, min(60, lat + 5)):.3f}",
             "CENTER": f"{lng:.5f},{lat:.5f}", "ZSTART": "1.85", "ZEND": str(zend), "DUR": f"{sure:.2f}",
             "HOLD": "0.6", "FPS": "30", "OUT": str(dizin)}  # fmt: skip
    r = subprocess.run(["node", str(BETIK)], cwd=MOTOR_DIZIN, env=ortam, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800)  # fmt: skip
    if r.returncode or not hedef.exists():
        raise RuntimeError(f"harita pişmedi: {(r.stderr or r.stdout)[-800:]}")
    return hedef
