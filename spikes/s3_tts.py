"""S3 spike: Kokoro (ONNX, CPU) ile çok dilli anlatım, hız ve kaliteyi ölç."""
import time, wave
from pathlib import Path
import numpy as np
from kokoro_onnx import Kokoro

M = Path(__file__).parent / "out" / "models"
k = Kokoro(str(M / "kokoro-v1.0.onnx"), str(M / "voices-v1.0.bin"))
metin = {
    ("en-us", "am_michael"): "In just thirty days, the Earth shook five hundred and twenty-six times. Every dot you see is an earthquake stronger than magnitude four point five. And almost all of them trace one giant ring around the Pacific.",
    ("es", "em_alex"): "En solo treinta días, la Tierra tembló quinientas veintiséis veces. Cada punto es un terremoto de magnitud superior a cuatro coma cinco.",
    ("pt-br", "pm_alex"): "Em apenas trinta dias, a Terra tremeu quinhentas e vinte e seis vezes. Cada ponto é um terremoto acima de magnitude quatro vírgula cinco.",
}
for (lang, voice), txt in metin.items():
    t = time.time()
    samples, sr = k.create(txt, voice=voice, speed=1.05, lang=lang)
    pcm = (np.clip(samples, -1, 1) * 32767).astype(np.int16)
    out = Path(__file__).parent / "out" / f"s3_{lang}.wav"
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())
    print(f"{lang} {voice}: {len(samples)/sr:.1f} sn ses, {time.time()-t:.1f} sn üretim")
