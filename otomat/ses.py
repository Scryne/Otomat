"""Seslendirme (Kokoro, yerel) ve altyazı zamanlaması.

Her cümle ayrı seslendirilir, aralarına kısa sessizlik konur. Böylece her cümlenin başlangıç ve bitiş anı kesin bilinir;
altyazı için Whisper gerekmez (ekran metni seslendirme metninden farklı olsa bile: '1.6' / '1 point 6').
"""

import wave
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import numpy as np

from otomat.ayarlar import KOK, modeller

ARA = 0.28  # cümleler arası sessizlik (sn)
HIZ = 1.05


@dataclass(frozen=True)
class Parca:
    bas: float
    son: float
    metin: str  # ekranda gösterilecek


@cache
def _kokoro():
    from kokoro_onnx import Kokoro

    from otomat.modeller import kokoro_dosyalari

    model, sesler = kokoro_dosyalari(KOK / "modeller")
    return Kokoro(str(model), str(sesler))


def seslendir(ses_cumleleri: list[str], ekran_cumleleri: list[str], cikti: Path) -> tuple[float, list[Parca]]:
    """WAV yazar; (toplam süre, cümle başına zaman aralığı) döner."""
    if len(ses_cumleleri) != len(ekran_cumleleri):
        raise ValueError("ses ve ekran cümle sayısı farklı")
    k = _kokoro()
    t = modeller()["tts"]
    parcalar, sesler, an, sr = [], [], 0.0, 24000
    for ses_metni, ekran_metni in zip(ses_cumleleri, ekran_cumleleri, strict=True):
        ornek, sr = k.create(ses_metni, voice=t["ses"], speed=HIZ, lang="en-us")
        sure = len(ornek) / sr
        parcalar.append(Parca(an, an + sure, ekran_metni))
        sesler += [ornek, np.zeros(int(ARA * sr), dtype=np.float32)]
        an += sure + ARA
    tum = np.concatenate(sesler)
    cikti.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(cikti), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(tum, -1, 1) * 32767).astype(np.int16).tobytes())
    return len(tum) / sr, parcalar


def altyazi_parcalari(parcalar: list[Parca], kelime: int = 4) -> list[Parca]:
    """Cümleleri ≤ `kelime` kelimelik gruplara böl; süreyi karakter uzunluğuyla orantılı dağıt."""
    sonuc = []
    for p in parcalar:
        kelimeler = p.metin.split()
        gruplar = [" ".join(kelimeler[i : i + kelime]) for i in range(0, len(kelimeler), kelime)]
        toplam = sum(len(g) for g in gruplar) or 1
        an = p.bas
        for g in gruplar:
            sure = (p.son - p.bas) * len(g) / toplam
            sonuc.append(Parca(an, an + sure, g))
            an += sure
    return sonuc
