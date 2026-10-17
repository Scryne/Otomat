"""Anlatım sesi: Chatterbox (ifade) + Kokoro'nun sentetik sesinden klon (tını), parça başına Whisper denetimi.

Spike (10-17, aynı üç cümle): Kokoro bm_george perde sapması 3,96 yarım ton, Chatterbox klonu 5,33; ikisi de Whisper'da
hatasız. Referans ses Kokoro'dan üretildiği için (Apache-2.0) gerçek bir kişinin sesi klonlanmaz.
"""

import difflib
import json
import os
import re
import subprocess
import unicodedata
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from otomat.ayarlar import KOK

SR = 24000
ARA_PARCA = 0.30  # aynı blokta parçalar arası
ARA_BLOK = 0.65
ARA_BOLUM = 1.40
PARCA_KELIME = 32  # Chatterbox uzun girdide kelime atlıyor/uyduruyor; cümleler bu sınıra kadar gruplanır
HATA_ESIGI = 0.12  # Whisper'ın duyduğu ile metin arasındaki fark; üstündeyse parça yeniden üretilir
DENEME = 3
CHATTERBOX_PY = Path(os.environ.get("OTOMAT_CHATTERBOX_PY", Path.home() / "tts-chatterbox/.venv/Scripts/python.exe"))
REFERANS_METNI = (
    "This is a story about a girl who should not have survived. She was born far from the sea, on the open grasslands, "
    "and yet the ocean would shape her whole life. Three great ships. One extraordinary woman."
)


@dataclass(frozen=True)
class Zaman:
    bas: float
    son: float


def parcala(metin: str, sinir: int = PARCA_KELIME) -> list[str]:
    """Cümle sınırında ≤ `sinir` kelimelik parçalar; tek başına uzun cümle bölünmez."""
    cumleler = [c.strip() for c in re.split(r"(?<=[.!?])\s+", metin) if c.strip()]
    parcalar, simdiki = [], []
    for c in cumleler:
        if simdiki and len(" ".join(simdiki + [c]).split()) > sinir:
            parcalar.append(" ".join(simdiki))
            simdiki = []
        simdiki.append(c)
    if simdiki:
        parcalar.append(" ".join(simdiki))
    return parcalar


def soylenis(metin: str) -> str:
    """TTS'e giden metin: aksanlar sadeleşir (Bahía → Bahia), uzun tire virgüle döner."""
    metin = metin.replace(" — ", ", ").replace("—", ", ")  # ascii'ye inmeden önce: tire yoksa düşer
    return unicodedata.normalize("NFKD", metin).encode("ascii", "ignore").decode()


def kelimeler(s: str) -> list[str]:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().replace("-", " ")
    return re.findall(r"[a-z0-9']+", s)


def fark(metin: str, duyulan: str) -> float:
    a, b = kelimeler(metin), kelimeler(duyulan)
    return 1 - difflib.SequenceMatcher(None, a, b).ratio() if a else 0.0


def wav_oku(yol: Path) -> np.ndarray:
    with wave.open(str(yol)) as w:
        ham = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32767
        sr = w.getframerate()
    if sr != SR:
        x = np.linspace(0, len(ham) - 1, int(len(ham) * SR / sr))
        ham = np.interp(x, np.arange(len(ham)), ham).astype(np.float32)
    return ham


def wav_yaz(yol: Path, x: np.ndarray) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(yol), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def sessizlik_kirp(x: np.ndarray, esik: float = 0.01) -> np.ndarray:
    """Baştaki/sondaki sessizliği at (Chatterbox parça sonuna değişken uzunlukta boşluk bırakıyor)."""
    i = np.flatnonzero(np.abs(x) > esik)
    if not len(i):
        return x
    pay = int(0.04 * SR)
    return x[max(i[0] - pay, 0) : i[-1] + pay]


def referans(ses: str, dizin: Path) -> Path:
    yol = dizin / f"referans_{ses}.wav"
    if not yol.exists():
        from kokoro_onnx import Kokoro

        from otomat.modeller import kokoro_dosyalari

        model, sesler = kokoro_dosyalari(KOK / "modeller")
        x, sr = Kokoro(str(model), str(sesler)).create(
            REFERANS_METNI, voice=ses, speed=1.0, lang="en-gb" if ses.startswith("b") else "en-us"
        )
        wav_yaz(
            yol, x if sr == SR else np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / sr)), np.arange(len(x)), x)
        )
    return yol


def _uret(isler: list[dict], ref: Path, dizin: Path) -> None:
    bekleyen = [i for i in isler if not Path(i["hedef"]).exists()]
    if not bekleyen:
        return
    gorev = dizin / "chatterbox_is.json"
    gorev.write_text(
        json.dumps({"ref": str(ref), "exaggeration": 0.5, "cfg": 0.5, "isler": bekleyen}), encoding="utf-8"
    )
    subprocess.run([str(CHATTERBOX_PY), str(Path(__file__).with_name("cb_isci.py")), str(gorev)], check=True)


def seslendir(bloklar: list[tuple[int, str]], ses: str, dizin: Path) -> tuple[Path, list[Zaman], list[dict]]:
    """bloklar: (bölüm no, anlatım). Tek WAV + blok başına zaman aralığı + parça denetim kaydı döner."""
    from faster_whisper import WhisperModel

    dizin.mkdir(parents=True, exist_ok=True)
    ref = referans(ses, dizin)
    parcalar = [(bi, pi, p) for bi, (_, metin) in enumerate(bloklar) for pi, p in enumerate(parcala(metin))]
    secim: dict[tuple[int, int], Path] = {}
    kayit: list[dict] = []
    whisper = WhisperModel("small.en", device="cpu", compute_type="int8")
    acik = parcalar
    for deneme in range(DENEME):
        isler = [{"metin": soylenis(p), "hedef": str(dizin / f"p{bi:03d}_{pi}_{deneme}.wav"), "tohum": deneme}
                 for bi, pi, p in acik]  # fmt: skip
        _uret(isler, ref, dizin)
        kalan = []
        for (bi, pi, p), is_ in zip(acik, isler, strict=True):
            x = wav_oku(Path(is_["hedef"]))
            duyulan = " ".join(s.text for s in whisper.transcribe(_16k(x), language="en")[0])
            f = fark(p, duyulan)
            kayit.append({"blok": bi, "parca": pi, "deneme": deneme, "fark": round(f, 3), "duyulan": duyulan.strip()})
            onceki = secim.get((bi, pi))
            if onceki is None or f < _fark_kaydi(kayit, bi, pi, onceki):
                secim[(bi, pi)] = Path(is_["hedef"])
            if f > HATA_ESIGI:
                kalan.append((bi, pi, p))
        acik = kalan
        if not acik:
            break
    toplam, zamanlar, an = [], [], 0.0
    for bi, (bolum, _) in enumerate(bloklar):
        if bi:
            ara = ARA_BOLUM if bolum != bloklar[bi - 1][0] else ARA_BLOK
            toplam.append(np.zeros(int(ara * SR), np.float32))
            an += ara
        bas = an
        pis = sorted(pi for b, pi in secim if b == bi)
        for j, pi in enumerate(pis):
            x = sessizlik_kirp(wav_oku(secim[(bi, pi)]))
            toplam.append(x)
            an += len(x) / SR
            if j < len(pis) - 1:
                toplam.append(np.zeros(int(ARA_PARCA * SR), np.float32))
                an += ARA_PARCA
        zamanlar.append(Zaman(round(bas, 3), round(an, 3)))
    yol = dizin / "anlatim.wav"
    wav_yaz(yol, np.concatenate(toplam))
    return yol, zamanlar, kayit


def _fark_kaydi(kayit: list[dict], bi: int, pi: int, yol: Path) -> float:
    deneme = int(yol.stem.rsplit("_", 1)[1])
    return next(k["fark"] for k in kayit if (k["blok"], k["parca"], k["deneme"]) == (bi, pi, deneme))


def _16k(x: np.ndarray) -> np.ndarray:
    n = int(len(x) * 16000 / SR)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
