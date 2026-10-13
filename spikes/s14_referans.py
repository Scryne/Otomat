"""S14: ana karakterin ilk karesi sonraki sahnelere referans görsel (flux-2-klein `input_image_0`) olarak verilince
karakter tutarlılığı artıyor mu, sahneler ilk karenin kopyasına mı dönüşüyor?

Taban: günlük koşunun bir üretim klasörü (senaryo.json + sahne_*.jpg, referanssız). Betik aynı istem ve tohumlarla
karakterin geçtiği sahneleri referansla yeniden çizer (`<cikti>/sahne_*.jpg`) ve üst sıra taban, alt sıra referanslı
bir karşılaştırma sayfası yazar (`<cikti>/karsilastirma.jpg`). Kaynak kare kopyalanır, yeniden çizilmez.

Çalıştırma: uv run python spikes/s14_referans.py <uretim_klasoru> <cikti_klasoru>   (OTOMAT_KANAL kanalın kendisi)
Maliyet: referanslı sahne başına ~162 neuron.
"""

import json
import shutil
import sys
from pathlib import Path

from PIL import Image

from otomat.hikaye import cf, senaryo, uretim


def main():
    kaynak_dizin, cikti = Path(sys.argv[1]), Path(sys.argv[2])
    cikti.mkdir(parents=True, exist_ok=True)
    d = json.loads((kaynak_dizin / "senaryo.json").read_text(encoding="utf-8"))
    sc = senaryo.Senaryo(**d["senaryo"])
    istemler = d["istemler"]
    taban = sum(map(ord, d["anahtar"])) % 100_000
    ad = sc.oyuncular[0].partition(":")[0].strip()
    gecen = [i for i, g in enumerate(sc.gorseller) if uretim._sahnede(ad, g)]
    if len(gecen) < 2:
        sys.exit(f"ana karakter ({ad}) iki sahnede geçmiyor: {gecen}")
    kaynak, refli = gecen[0], gecen[1:]
    shutil.copy(kaynak_dizin / f"sahne_{kaynak}.jpg", cikti / f"sahne_{kaynak}.jpg")
    ref = (cikti / f"sahne_{kaynak}.jpg",)
    for i in refli:
        istem = f"{istemler[i]} {uretim.REFERANS_CUMLESI.format(ad=ad)}"
        cf.gorsel(istem, cikti / f"sahne_{i}.jpg", taban + 10 * i, referanslar=ref)
    print(f"ana karakter: {ad} · kaynak sahne {kaynak} · referanslı {refli} · neuron {round(cf.NEURON['toplam'])}")

    sutun = [kaynak, *refli]
    w, h = 300, 525
    sayfa = Image.new("RGB", (w * len(sutun), h * 2), "white")
    for j, i in enumerate(sutun):
        for satir, klasor in enumerate((kaynak_dizin, cikti)):
            with Image.open(klasor / f"sahne_{i}.jpg") as img:
                sayfa.paste(img.convert("RGB").resize((w, h)), (j * w, satir * h))
    sayfa.save(cikti / "karsilastirma.jpg", quality=85)
    print("karşılaştırma:", cikti / "karsilastirma.jpg")


if __name__ == "__main__":
    main()
