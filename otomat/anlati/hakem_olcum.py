"""D-8 ölçümü: anlamsal hakemin etiketli 30 cümlede yakalama ve yanlış alarm oranı."""

import argparse
import json
import os
import time
from collections import Counter

from otomat.anlati import kapilar
from otomat.ayarlar import KOK
from otomat.gorsel.ornekler import paket_yukle


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--surum", default=kapilar.HAKEM_SURUM)
    p.add_argument("--paketler", default=str(KOK / "calisma" / "paketler.json"))
    a = p.parse_args()
    with open(a.paketler, encoding="utf-8") as f:
        paketler = {d["anahtar"]: paket_yukle(d) for d in json.load(f)}
    ornekler = json.loads((KOK / "tests" / "veri" / "hakem_30.json").read_text(encoding="utf-8"))
    sonuc: Counter = Counter()
    hatali = []
    t = time.time()
    for o in ornekler:
        pk = next(v for k, v in paketler.items() if k.startswith(o["anahtar"]))
        destek, neden = kapilar.hakem(o["cumle"], pk, a.surum)
        sonuc[("D" if o["destek"] else "Y") + ("+" if destek else "-")] += 1
        if destek != o["destek"]:
            hatali.append((o["tur"], o["cumle"], neden[:120]))
    yanlis = sonuc["Y-"] + sonuc["Y+"]
    dogru = sonuc["D-"] + sonuc["D+"]
    print(f"model={os.environ.get('OTOMAT_LLM', 'config')} sürüm={a.surum} süre={time.time() - t:.0f}s")
    print(f"yanlış cümle yakalama: {sonuc['Y-']}/{yanlis} ({sonuc['Y-'] / max(yanlis, 1):.0%})")
    print(f"doğru cümleye yanlış alarm: {sonuc['D-']}/{dogru} ({sonuc['D-'] / max(dogru, 1):.0%})")
    for h in hatali:
        print("  HATA", h)


if __name__ == "__main__":
    main()
