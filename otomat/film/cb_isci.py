"""Chatterbox işçisi: kendi sanal ortamında koşar (torch + chatterbox-tts; otomat'ı import etmez).

Girdi: JSON dosyası {"ref": wav, "exaggeration": f, "cfg": f, "isler": [{"metin", "hedef", "tohum"}]}. Her iş için
hedef WAV yazar; var olanı atlar. Chatterbox MIT; her çıktıya duyulmaz Perth filigranı ekler.
"""

import json
import sys
from pathlib import Path

import torch
import torchaudio
from chatterbox.tts import ChatterboxTTS


def main() -> None:
    is_ = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    model = ChatterboxTTS.from_pretrained(device="cuda" if torch.cuda.is_available() else "cpu")
    for s in is_["isler"]:
        hedef = Path(s["hedef"])
        if hedef.exists():
            continue
        torch.manual_seed(s.get("tohum", 0))
        dalga = model.generate(
            s["metin"], audio_prompt_path=is_["ref"], exaggeration=is_["exaggeration"], cfg_weight=is_["cfg"]
        )
        hedef.parent.mkdir(parents=True, exist_ok=True)
        # 16 bit PCM: ana taraf `wave` ile okur, float WAV'ı açamaz
        torchaudio.save(str(hedef), dalga, model.sr, encoding="PCM_S", bits_per_sample=16)
        print(f"ok {hedef.name}", flush=True)


if __name__ == "__main__":
    main()
