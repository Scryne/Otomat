"""S15: panelli çıkan sahne, dünya cümlesi düşürülmüş ve "tek sürekli resim" cümlesi eklenmiş istemle (üretimin panel
yeniden çizimi: `uretim.panelsiz_istem` + `yeniden_ciz`) tek kare çiziliyor mu?

Taban: günlük koşunun bir üretim klasörü (senaryo.json'da `istemler`) ve panelli sahnenin numarası. Betik o sahneyi
üretimin yeniden çizim yoluyla birkaç tohumla çizer (`<cikti>/<ad>_<tohum>.jpg`), her kareyi panel denetiminden geçirir.

Çalıştırma: uv run python spikes/s15_panel.py <uretim_klasoru> <sahne_no> <cikti_klasoru> [tohum_sayisi]
Maliyet: kare başına ~156 neuron.
"""

import json
import sys
from pathlib import Path

from otomat.hikaye import cf, panel, senaryo, uretim


def main():
    kaynak, i, cikti = Path(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3])
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    cikti.mkdir(parents=True, exist_ok=True)
    d = json.loads((kaynak / "senaryo.json").read_text(encoding="utf-8"))
    sc = senaryo.Senaryo(**d["senaryo"])
    tek = [uretim.panelsiz_istem(s, sc.dunya) for s in d["istemler"]]
    taban = sum(map(ord, d["anahtar"])) % 100_000
    print("istem:", senaryo.yazisiz(tek[i]))
    for t in range(n):
        yol = cikti / f"{kaynak.name}_{i}_{t}.jpg"
        uretim.yeniden_ciz(tek, i, yol, taban + 10 * i + 3 + 100 * (t + 1), cikti)
        print(yol.name, "panelli" if panel.panelli(yol) else "tek kare")
    print("neuron", round(cf.NEURON["toplam"]))


if __name__ == "__main__":
    main()
