"""Etkin kanalın veri kaynaklarını çalıştırıp olgu paketlerini toplar. Bir kaynak düşerse diğerleri sürer.

Kaynaklar `KAYNAKLAR`'da adla kayıtlıdır; kanal profili hangilerini kullanacağını ve ayar dosyasını söyler
(kanallar/<id>/kanal.toml: `kaynaklar`, `veri`). `--kaydet DIZIN` ham yanıtları da yazar (sözleşme testleri için).
"""

import argparse
import datetime as dt
import json
import tomllib
from collections.abc import Callable
from pathlib import Path

from otomat import kanal
from otomat.veri import OlguPaketi, dunya_bankasi, eurostat, jpl, otegezegen, usgs

# (ayarlar, şimdi, çekildi, ham yazıcı) → (paketler, hatalar)
Kaynak = Callable[[dict, dt.datetime, str, Callable[[str, object], None]], tuple[list[OlguPaketi], list[str]]]


def ayarlar() -> dict:
    with open(kanal.aktif().veri, "rb") as f:
        return tomllib.load(f)


def _usgs(a: dict, simdi: dt.datetime, cekildi: str, yaz) -> tuple[list[OlguPaketi], list[str]]:
    ham, url = usgs.indir(a["usgs"]["gun"], a["usgs"]["min_buyukluk"])
    yaz("usgs", ham)
    return usgs.paketler(ham, url, cekildi, a["usgs"]["gun"]), []


def _dunya_bankasi(a: dict, simdi: dt.datetime, cekildi: str, yaz) -> tuple[list[OlguPaketi], list[str]]:
    paketler: list[OlguPaketi] = []
    hatalar: list[str] = []
    ham_ulkeler = dunya_bankasi.ulkeler_indir()
    yaz("wb_ulkeler", ham_ulkeler)
    gecerli = dunya_bankasi.ulkeler(ham_ulkeler)
    for g in a["dunya_bankasi"]:
        try:
            kayitlar, url = dunya_bankasi.gosterge_indir(g["kod"], simdi.year)
            yaz(f"wb_{g['kod']}", kayitlar)
            paketler += dunya_bankasi.paketler(g, kayitlar, gecerli, url, cekildi)
        except Exception as e:  # noqa: BLE001 — bir gösterge düşerse diğerleri sürsün
            hatalar.append(f"{g['kod']}: {e}")
    return paketler, hatalar


def _eurostat(a: dict, simdi: dt.datetime, cekildi: str, yaz) -> tuple[list[OlguPaketi], list[str]]:
    paketler: list[OlguPaketi] = []
    hatalar: list[str] = []
    for v in a["eurostat"]:
        try:
            js, url = eurostat.indir(v["kod"], v["filtre"], simdi.year - 12)
            yaz(f"es_{v['kod']}", js)
            paketler += eurostat.paketler(v, js, url, cekildi)
        except Exception as e:  # noqa: BLE001
            hatalar.append(f"{v['kod']}: {e}")
    return paketler, hatalar


def _jpl(a: dict, simdi: dt.datetime, cekildi: str, yaz) -> tuple[list[OlguPaketi], list[str]]:
    ham, url = jpl.indir(simdi.date())
    yaz("jpl_cad", ham)
    return jpl.paketler(ham, url, cekildi, simdi.date()), []


def _otegezegen(a: dict, simdi: dt.datetime, cekildi: str, yaz) -> tuple[list[OlguPaketi], list[str]]:
    satirlar, url = otegezegen.indir()
    yaz("otegezegen", satirlar)
    return otegezegen.paketler(satirlar, url, cekildi, simdi.date()), []


KAYNAKLAR: dict[str, Kaynak] = {
    "usgs": _usgs,
    "dunya_bankasi": _dunya_bankasi,
    "eurostat": _eurostat,
    "jpl": _jpl,
    "otegezegen": _otegezegen,
}


def topla(kayit: Path | None = None) -> tuple[list[OlguPaketi], list[str]]:
    a = ayarlar()
    simdi = dt.datetime.now(dt.UTC)
    cekildi = simdi.isoformat(timespec="seconds")
    paketler: list[OlguPaketi] = []
    hatalar: list[str] = []

    def yaz(ad: str, veri) -> None:
        if kayit:
            kayit.mkdir(parents=True, exist_ok=True)
            (kayit / f"{ad}.json").write_text(json.dumps(veri), encoding="utf-8")

    for ad in kanal.aktif().kaynaklar:
        try:
            p, h = KAYNAKLAR[ad](a, simdi, cekildi, yaz)
            paketler += p
            hatalar += [f"{ad} {x}" for x in h]
        except Exception as e:  # noqa: BLE001 — kaynak düşerse diğerleri sürsün
            hatalar.append(f"{ad}: {e}")
    return paketler, hatalar


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--kaydet", type=Path, help="ham yanıtları bu dizine yaz")
    p.add_argument("--cikti", type=Path, help="paketleri JSON olarak yaz")
    a = p.parse_args()
    paketler, hatalar = topla(a.kaydet)
    sayac: dict[str, int] = {}
    for pk in paketler:
        sayac[f"{pk.kol}/{pk.tur}"] = sayac.get(f"{pk.kol}/{pk.tur}", 0) + 1
    for k, n in sorted(sayac.items()):
        print(f"{k}: {n}")
    print(f"toplam {len(paketler)} paket, {len(set(p.hash for p in paketler))} benzersiz hash")
    for h in hatalar:
        print("HATA", h)
    if a.cikti:
        a.cikti.write_text(json.dumps([p.sozluk() for p in paketler], ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
