"""Ming-3.0-tts işçisi: kendi sanal ortamında koşar (torch + Ming deposu; otomat'ı import etmez).

Girdi: JSON {"ses", "isler": [{"metin", "hedef", "tohum"}]}. Her iş için hedef WAV (24 kHz, 16 bit PCM) yazar; var
olanı atlar. Model inclusionAI/Ming-3.0-tts-0.5b (MIT); hazır ses (`ip`, ör. UK_George) ile okur, metni noktalama
sınırlarında kendisi böler. Neden: Artificial Analysis kör tercih sıralamasında (11-26) açık ağırlıklılar arasında
4. (1181 ELO); Qwen3 TTS 931. 4060'ta ~3 GB VRAM, ~1,6× gerçek zaman.
Model 44,1 kHz üretir; hat 24 kHz bekler. Örnek oranı burada süzgeçli yeniden örneklemeyle iner (doğrusal
aradeğerleme yüksek frekansı katlar, metalik ses yapar).
Kurulum: ~/tts-ming (github.com/inclusionAI/Ming-3.0-tts, uv venv py3.12, torch 2.11 cu128, transformers 4.46.3).
"""

import json
import os
import sys
from pathlib import Path

DEPO = Path(os.environ.get("OTOMAT_MING_DEPO", Path.home() / "tts-ming"))
MODEL = "inclusionAI/Ming-3.0-tts-0.5b"
HEDEF_SR = 24000


def main() -> None:
    is_ = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    bekleyen = [s for s in is_["isler"] if not Path(s["hedef"]).exists()]
    if not bekleyen:
        return
    sys.path.insert(0, str(DEPO))
    os.chdir(DEPO)  # depo göreli yollarla (frontend/, data/) çalışıyor
    import soundfile as sf
    import torch
    import torchaudio.functional as AF
    from ming_tts import MingTTS

    model = MingTTS(MODEL, text_normalization=False)  # sayılar hatta `soylenis` ile yazıya döner
    for s in bekleyen:
        torch.manual_seed(int(s.get("tohum", 0)))
        dalga = model.synthesize(task="IP", text=s["metin"], language_id="English", controls={"ip": is_["ses"]},
                                 use_zero_spk_emb=True)  # fmt: skip
        x = AF.resample(dalga.float().cpu(), model.sample_rate, HEDEF_SR).squeeze(0).numpy()
        hedef = Path(s["hedef"])
        hedef.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(hedef), x.clip(-1, 1), HEDEF_SR, subtype="PCM_16")
        print(f"ok {hedef.name}", flush=True)


if __name__ == "__main__":
    main()
