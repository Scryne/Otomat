"""Altyazı kelime vurgusu için gerçek kelime zamanları: anlatıcının sesi Whisper ile yazıya dökülür, bildiğimiz metne
hizalanır. Harf sayısıyla orantılı tahmin ortancada iyi ama sayılarda kayıyordu (Molasses: p90 0,58 sn, en kötü
1,07 sn; "2.3 million" yazıldığından uzun söyleniyor, 2026-10-08 ölçümü). Whisper yalnız zamanı verir; metin bizim.
Eşleşmeyen kelime komşu eşleşmeler arasına harf sayısıyla yerleşir. Whisper düşerse orantılı tahmine dönülür.
"""

import difflib
import re
import wave
from functools import cache
from pathlib import Path

import numpy as np

from otomat.ayarlar import KOK, modeller
from otomat.ses import Parca


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


@cache
def _model():
    from faster_whisper import WhisperModel

    return WhisperModel(modeller()["stt"]["model"], device="cpu", compute_type="int8",
                        download_root=str(KOK / "modeller" / "whisper"))  # fmt: skip


def whisper_kelimeleri(wav: Path) -> list[tuple[float, str]]:
    """(başlangıç sn, normalize kelime). Ses numpy ile verilir: av kütüphanesinin sürümüne takılmasın."""
    with wave.open(str(wav)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    y = np.interp(np.arange(0, len(x), sr / 16000), np.arange(len(x)), x).astype(np.float32)
    parcalar, _ = _model().transcribe(y, word_timestamps=True, language="en", beam_size=1)
    return [(w.start, _norm(w.word)) for p in parcalar for w in p.words]


def baslangiclar(parcalar: list[Parca], gercek: list[tuple[float, str]] | None) -> list[list[float]]:
    """Satır başına kelime başlangıçları: orantılı tahmin + (varsa) Whisper eşleşmeleri; satır sınırı, sıra korunur."""
    satirlar = [p.metin.split() for p in parcalar]
    tahmin: list[list[float]] = []
    for p, kel in zip(parcalar, satirlar, strict=True):
        toplam = sum(len(w) + 1 for w in kel) or 1
        an, bas = p.bas, []
        for w in kel:
            bas.append(an)
            an += (p.son - p.bas) * (len(w) + 1) / toplam
        tahmin.append(bas)
    if not gercek:
        return tahmin
    duz = [(i, j) for i, kel in enumerate(satirlar) for j in range(len(kel))]
    sm = difflib.SequenceMatcher(a=[_norm(satirlar[i][j]) for i, j in duz], b=[w for _, w in gercek], autojunk=False)
    sabit: dict[tuple[int, int], float] = {}
    for blok in sm.get_matching_blocks():
        for k in range(blok.size):
            i, j = duz[blok.a + k]
            t = gercek[blok.b + k][0]
            if parcalar[i].bas - 0.15 <= t <= parcalar[i].son:  # başka satıra kaymış eşleşmeye güvenme
                sabit[(i, j)] = max(t, parcalar[i].bas)
    sonuc = []
    for i, p in enumerate(parcalar):
        n = len(satirlar[i])
        bas = [sabit.get((i, j)) for j in range(n)]
        bas[0] = p.bas if bas[0] is None else bas[0]
        # eşleşmeyenler: önceki ve sonraki bilinen nokta arasına, orantılı tahminin oranıyla
        j = 0
        while j < n:
            if bas[j] is not None:
                j += 1
                continue
            k = j
            while k < n and bas[k] is None:
                k += 1
            sol_t, sag_t = bas[j - 1], (bas[k] if k < n else p.son)
            sol_e, sag_e = tahmin[i][j - 1], (tahmin[i][k] if k < n else p.son)
            for m in range(j, k):
                oran = (tahmin[i][m] - sol_e) / (sag_e - sol_e) if sag_e > sol_e else (m - j + 1) / (k - j + 1)
                bas[m] = sol_t + (sag_t - sol_t) * oran
            j = k
        for j in range(1, n):  # sıra bozulmasın
            bas[j] = max(bas[j], bas[j - 1] + 0.04)
        sonuc.append([min(b, p.son - 0.04) for b in bas])
    return sonuc
