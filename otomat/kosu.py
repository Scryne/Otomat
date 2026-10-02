"""Komut satırı. `duman`: yüklemesiz, sabit veriyle tek kısa video (CI'da koşar)."""

import argparse
import json
import time
from pathlib import Path

from otomat.ayarlar import KOK
from otomat.gorsel import nokta_harita
from otomat.veri import usgs


def duman(cikti: Path, saniye: float = 2, kucuk: bool = True) -> Path:
    ham = json.loads((KOK / "tests" / "veri" / "usgs_ornek.json").read_text(encoding="utf-8"))
    olaylar = [[d.zaman, d.boylam, d.enlem, d.buyukluk] for d in usgs.depremler(ham)]
    g, y = (270, 480) if kucuk else (1080, 1920)
    return nokta_harita.ciz(
        olaylar,
        "Every M4.5+ earthquake (smoke test)",
        "USGS",
        cikti,
        genislik=g,
        yukseklik=y,
        fps=30,
        saniye=saniye,
    )


def main() -> None:
    p = argparse.ArgumentParser(prog="otomat")
    alt = p.add_subparsers(dest="komut", required=True)
    d = alt.add_parser("duman")
    d.add_argument("--cikti", type=Path, default=KOK / "calisma" / "duman.mp4")
    d.add_argument("--saniye", type=float, default=2)
    d.add_argument("--tam", action="store_true", help="1080x1920 boyutunda")
    a = p.parse_args()
    if a.komut == "duman":
        t = time.time()
        yol = duman(a.cikti, a.saniye, kucuk=not a.tam)
        print(f"duman: {yol} ({time.time() - t:.1f} sn)")


if __name__ == "__main__":
    main()
