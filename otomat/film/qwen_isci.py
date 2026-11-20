"""Qwen3-TTS işçisi: kendi sanal ortamında koşar (torch + faster-qwen3-tts; otomat'ı import etmez).

Girdi: JSON {"model", "konusmaci", "isler": [{"metin", "ton", "hedef", "tohum"}]}. Her iş için hedef WAV (24 kHz,
16 bit PCM) yazar; var olanı atlar. Qwen3-TTS-12Hz-1.7B-CustomVoice Apache-2.0; hazır konuşmacı + doğal dil talimatı
(`instruct`) cümle başına ton verir, ses kimliği sabit kalır (VoiceDesign'da kimlik kayıyordu, 11-20 ölçümü).
Kurulum: ~/tts-qwen3 (uv venv, torch cu128, faster-qwen3-tts 0.5.4, transformers 5.15.1 — 5.23 tokenizer'ı bozuyor).
"""

import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from faster_qwen3_tts import FasterQwen3TTS


def main() -> None:
    is_ = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    bekleyen = [s for s in is_["isler"] if not Path(s["hedef"]).exists()]
    if not bekleyen:
        return
    model = FasterQwen3TTS.from_pretrained(is_["model"])
    for s in bekleyen:
        torch.manual_seed(int(s.get("tohum", 0)))
        dalga, sr = model.generate_custom_voice(text=s["metin"], speaker=is_["konusmaci"], language="English",
                                                instruct=s.get("ton") or None)  # fmt: skip
        hedef = Path(s["hedef"])
        hedef.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(hedef), np.asarray(dalga[0], dtype=np.float32), sr, subtype="PCM_16")
        print(f"ok {hedef.name}", flush=True)


if __name__ == "__main__":
    main()
