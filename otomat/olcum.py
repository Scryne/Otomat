"""Faz 1 ölçümü: çalışma ortamında LLM, TTS ve render sürelerini ölç, Markdown tablo bas.

GitHub Actions'ta `olcum.yml` ile koşar; çıktı iş özetine (GITHUB_STEP_SUMMARY) de yazılır.
"""

import json
import os
import time
import urllib.request
import wave

import numpy as np

from otomat.ayarlar import KOK, modeller
from otomat.kosu import duman

ANLATIM = (
    "In just thirty days, the Earth shook more than five hundred times. Every dot you see is an earthquake "
    "stronger than magnitude four point five. Almost all of them trace one giant ring around the Pacific. "
    "But one country felt more of them than any other."
)
KANCA_ISTEMI = (
    "Write one curiosity hook (max 12 words) for a vertical video about worldwide earthquakes last month. "
    "No numbers. Output only the hook."
)


def _llm(model: str, istem: str) -> str:
    govde = json.dumps({"model": model, "prompt": istem, "stream": False, "think": False}).encode()
    istek = urllib.request.Request("http://127.0.0.1:11434/api/generate", govde)
    return json.loads(urllib.request.urlopen(istek, timeout=900).read())["response"].strip()


def main() -> None:
    m = modeller()
    satirlar = []

    def olc(ad, f):
        t = time.time()
        sonuc = f()
        sure = time.time() - t
        satirlar.append((ad, f"{sure:.1f} sn", sonuc))
        print(f"{ad}: {sure:.1f} sn | {sonuc}", flush=True)

    model = os.environ.get("OTOMAT_LLM", m["llm"]["model"])
    olc(f"LLM ısınma ({model})", lambda: _llm(model, "Say OK.")[:40])
    for i in range(5):
        olc(f"LLM kanca {i + 1}", lambda: _llm(model, KANCA_ISTEMI)[:80])

    from kokoro_onnx import Kokoro

    from otomat.modeller import kokoro_dosyalari

    model_yolu, sesler_yolu = kokoro_dosyalari(KOK / "modeller")
    kokoro = Kokoro(str(model_yolu), str(sesler_yolu))
    ses_yolu = KOK / "calisma" / "olcum.wav"

    def tts():
        ornek, sr = kokoro.create(ANLATIM, voice=m["tts"]["ses"], speed=1.05, lang="en-us")
        ses_yolu.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(ses_yolu), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes((np.clip(ornek, -1, 1) * 32767).astype(np.int16).tobytes())
        return f"{len(ornek) / sr:.1f} sn ses"

    olc("Kokoro TTS", tts)
    olc("Render 1080×1920, 30 sn", lambda: duman(KOK / "calisma" / "olcum.mp4", 30, kucuk=False).name)

    tablo = ["| Adım | Süre | Çıktı |", "| --- | --- | --- |"]
    tablo += [f"| {a} | {s} | {str(c).replace('|', '/')} |" for a, s, c in satirlar]
    metin = "\n".join(tablo)
    print(metin)
    ozet = os.environ.get("GITHUB_STEP_SUMMARY")
    if ozet:
        with open(ozet, "a", encoding="utf-8") as f:
            f.write("## Otomat ölçümü\n\n" + metin + "\n")


if __name__ == "__main__":
    main()
