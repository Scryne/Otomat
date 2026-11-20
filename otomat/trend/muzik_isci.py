"""ACE-Step 1.5 işçisi: kendi sanal ortamında ve kendi dizininde koşar (~/ace-step; otomat'ı import etmez).

Girdi: JSON {"isler": [{"istem", "bpm", "sure", "tohum", "hedef"}]}. Her iş için 48 kHz WAV yazar; var olanı atlar.
ACE-Step 1.5 MIT; turbo DiT, dil modeli kapalı (8 GB'ta gerek yok), int8 ağırlık. Ölçüm (RTX 4060 Laptop, 11-20):
95 sn enstrümantal ~9 sn'de üretiliyor.
"""

import json
import shutil
import sys
from pathlib import Path

from acestep.handler import AceStepHandler
from acestep.inference import GenerationConfig, GenerationParams, generate_music


def main() -> None:
    is_ = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    bekleyen = [s for s in is_["isler"] if not Path(s["hedef"]).exists()]
    if not bekleyen:
        return
    dit = AceStepHandler()
    mesaj, ok = dit.initialize_service(project_root=str(Path.cwd()), config_path="acestep-v15-turbo", device="cuda",
                                       offload_to_cpu=True, quantization="int8_weight_only")  # fmt: skip
    if not ok:
        raise SystemExit(f"ACE-Step başlamadı: {mesaj[:400]}")
    for s in bekleyen:
        hedef = Path(s["hedef"])
        gecici = hedef.parent / (hedef.stem + "_tmp")
        p = GenerationParams(caption=s["istem"], lyrics="[Instrumental]", instrumental=True, bpm=int(s["bpm"]),
                             duration=float(s["sure"]), thinking=False, use_cot_metas=False, use_cot_caption=False,
                             use_cot_language=False, inference_steps=8, seed=int(s["tohum"]))  # fmt: skip
        c = GenerationConfig(batch_size=1, use_random_seed=False, seeds=[int(s["tohum"])], audio_format="wav")
        r = generate_music(dit, None, p, c, save_dir=str(gecici))
        if not r.success or not r.audios:
            raise SystemExit(f"müzik üretilemedi: {getattr(r, 'error', '')}")
        shutil.move(r.audios[0]["path"], hedef)
        shutil.rmtree(gecici, ignore_errors=True)
        print(f"ok {hedef.name}", flush=True)


if __name__ == "__main__":
    main()
