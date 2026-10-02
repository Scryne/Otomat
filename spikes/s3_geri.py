"""S3: üretilen sesi Whisper ile geri yazıya dök — anlaşılırlık vekili."""
import wave, numpy as np
from pathlib import Path
from faster_whisper import WhisperModel
m = WhisperModel("small", device="cpu", compute_type="int8")
for lang in ["en-us", "es", "pt-br"]:
    w = wave.open(str(Path(__file__).parent / "out" / f"s3_{lang}.wav"))
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    sr = w.getframerate()
    a = np.interp(np.arange(0, len(a), sr / 16000), np.arange(len(a)), a).astype(np.float32)
    segs, _ = m.transcribe(a, language=lang[:2])
    print(lang, "|", " ".join(s.text.strip() for s in segs))
