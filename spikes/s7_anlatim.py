"""Faz 4 denemesi: altı paket × dört kanca kalıbı, kapılardan geçiş oranı."""

import json
import sys
import time

from otomat.anlati.anlatim import KALIPLAR, olustur
from otomat.anlati.llm import LLMHatasi
from otomat.gorsel.ornekler import paket_yukle

SECIM = [
    "usgs:dunya_30g",
    "usgs:bolge_yillik:Japan",
    "usgs:en_guclu_10",
    "dunya_bankasi:en_yuksek_10:MS.MIL",
    "eurostat:en_dusuk_10:sdg_04_20",
    "dunya_bankasi:en_cok_artan_10:SP.DYN.LE00",
]

with open("calisma/paketler.json", encoding="utf-8") as f:
    paketler = [paket_yukle(d) for d in json.load(f)]
kaliplar = list(KALIPLAR)
gecen = 0
for i, onek in enumerate(SECIM):
    pk = next(x for x in paketler if x.anahtar.startswith(onek))
    kalip = kaliplar[i % 4] if len(sys.argv) < 2 else sys.argv[1]
    t = time.time()
    try:
        a = olustur(pk, kalip, "2026-10-02")
        gecen += 1
        gecen -= "yedek" in a.kaynak.values()
        print(f"[{onek} | {kalip} | {len(a.denemeler)} deneme | {a.kaynak} | {time.time() - t:.0f}s]")
        print(f"  HOOK: {a.kanca}\n  TITLE: {a.baslik}\n  BODY: {' '.join(a.cumleler)}")
        for d in a.denemeler[:-1]:
            print("   reddedilen:", d.get("hook"), "|", d.get("title"), "|", d.get("hatalar"))
    except LLMHatasi as e:
        print(f"[{onek} | {kalip}] KAPI GEÇİLEMEDİ: {e}")
print(f"geçen {gecen}/{len(SECIM)}")
