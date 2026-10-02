"""Proje kökü ve config dosyaları."""

import tomllib
from functools import cache
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
VARLIKLAR = Path(__file__).resolve().parent / "varliklar"


@cache
def modeller() -> dict:
    with open(KOK / "config" / "modeller.toml", "rb") as f:
        return tomllib.load(f)
