"""Senaryo → anlatım sesi + sahne başına kelime zamanları (kurgunun saati).

Ses film hattının `seslendir`iyle üretilir (Chatterbox, Kokoro'dan sentetik referans ses, parça başına Whisper
kapısı). Ardından bitmiş WAV faster-whisper ile kelime zamanlı çözülür ve senaryonun kendi kelimelerine hizalanır:
ipuçları ("bu parça anlatıcı X dediğinde gelsin") senaryo kelimesiyle yazıldığı için zaman da senaryo kelimesine
bağlanır. Rakamlar sözlü okunur ("750,000"), Whisper rakam yazar: iki taraf `kelimeler()` ile aynı birime iner.
"""

from __future__ import annotations

import difflib
import re
from pathlib import Path

from otomat.film.anlatim import SR, kelimeler, seslendir, wav_oku

ARALAR = (0.22, 0.38, 0.85)  # parça, sahne, bölüm arası sessizlik (film: 0.30 / 0.65 / 1.40)
ONCE = 0.12  # görüntü sesten biraz önce keser (J-kesme hissi)
SON_PAY = 2.6  # kapanış sahnesi anlatımdan sonra tutar


def _birimler(kelime: str) -> list[str]:
    return kelimeler(kelime) or [re.sub(r"\W", "", kelime.lower())]


def hizala(metin: str, whisper_kelimeleri: list[tuple[str, float, float]]) -> list[dict]:
    """Senaryo kelimeleri (boşlukla ayrık) için {w, s, e}; Whisper kelimeleriyle birim düzeyinde hizalanır,
    eşleşmeyenler komşularından doğrusal doldurulur."""
    senaryo = metin.split()
    s_birim, s_sahip = [], []
    for i, k in enumerate(senaryo):
        for b in _birimler(k):
            s_birim.append(b)
            s_sahip.append(i)
    w_birim, w_zaman = [], []
    for k, s, e in whisper_kelimeleri:
        for b in _birimler(k):
            w_birim.append(b)
            w_zaman.append((s, e))
    zaman: list[list[float] | None] = [None] * len(senaryo)
    sm = difflib.SequenceMatcher(None, s_birim, w_birim, autojunk=False)
    for blok in sm.get_matching_blocks():
        for j in range(blok.size):
            sahip = s_sahip[blok.a + j]
            s, e = w_zaman[blok.b + j]
            if zaman[sahip] is None:
                zaman[sahip] = [s, e]
            else:
                zaman[sahip][0] = min(zaman[sahip][0], s)
                zaman[sahip][1] = max(zaman[sahip][1], e)
    # boşlukları doldur
    bilinen = [i for i, z in enumerate(zaman) if z is not None]
    if not bilinen:
        bas = whisper_kelimeleri[0][1] if whisper_kelimeleri else 0.0
        son = whisper_kelimeleri[-1][2] if whisper_kelimeleri else bas + 0.4 * len(senaryo)
        adim = (son - bas) / max(1, len(senaryo))
        return [
            {"w": k, "s": round(bas + i * adim, 3), "e": round(bas + (i + 1) * adim, 3)} for i, k in enumerate(senaryo)
        ]
    for i in range(len(senaryo)):
        if zaman[i] is not None:
            continue
        onceki = max((j for j in bilinen if j < i), default=None)
        sonraki = min((j for j in bilinen if j > i), default=None)
        if onceki is None:
            t = zaman[sonraki][0] - 0.3 * (sonraki - i)
            zaman[i] = [t, t + 0.25]
        elif sonraki is None:
            t = zaman[onceki][1] + 0.3 * (i - onceki - 1)
            zaman[i] = [t, t + 0.25]
        else:
            a, b = zaman[onceki][1], zaman[sonraki][0]
            oran = (i - onceki) / (sonraki - onceki)
            t = a + (b - a) * oran
            zaman[i] = [t, t + max(0.05, (b - a) / (sonraki - onceki))]
    return [{"w": k, "s": round(max(0.0, z[0]), 3), "e": round(z[1], 3)} for k, z in zip(senaryo, zaman, strict=True)]


def whisper_kelimeleri(wav: Path, model: str = "small.en") -> list[tuple[str, float, float]]:
    from faster_whisper import WhisperModel

    w = WhisperModel(model, device="cpu", compute_type="int8")
    from otomat.film.anlatim import _16k  # dosya yolu verince av sürüm uyumsuzluğu (metadata_errors)

    parcalar, _ = w.transcribe(_16k(wav_oku(wav)), language="en", word_timestamps=True, vad_filter=False)
    return [(k.word.strip(), k.start, k.end) for p in parcalar for k in (p.words or [])]


def seslendir_ve_zamanla(sahneler: list[dict], dizin: Path, ses: str = "am_michael") -> dict:
    """Her sahnenin `anlatim`ı bir blok; `bolum` sahnesi bölüm sınırıdır (uzun duraklama).
    Dönüş: {"wav", "sure", "sahneler": [{bas, sure, kelimeler}], "denetim"} — sahne zamanı videonun saatidir."""
    bolum, bloklar = 0, []
    for sh in sahneler:
        if sh["tur"] == "bolum":
            bolum += 1
        bloklar.append((bolum, sh["anlatim"]))
    wav, araliklar, denetim = seslendir(bloklar, ses, dizin, aralar=ARALAR)
    toplam_ses = len(wav_oku(wav)) / SR
    wk = whisper_kelimeleri(wav)
    out = []
    for i, (sh, z) in enumerate(zip(sahneler, araliklar, strict=True)):
        bas = 0.0 if i == 0 else max(0.0, z.bas - ONCE)
        son = (araliklar[i + 1].bas - ONCE) if i + 1 < len(araliklar) else toplam_ses + SON_PAY
        icindeki = [(k, s, e) for k, s, e in wk if z.bas - 0.25 <= s <= z.son + 0.25]
        kel = hizala(sh["anlatim"], icindeki)
        for k in kel:  # sahneye göre göreli
            k["s"] = round(max(0.0, k["s"] - bas), 3)
            k["e"] = round(max(k["s"] + 0.05, k["e"] - bas), 3)
        out.append({"bas": round(bas, 3), "sure": round(son - bas, 3), "kelimeler": kel,
                    "ses_bas": z.bas, "ses_son": z.son})  # fmt: skip
    return {"wav": str(wav), "sure": round(toplam_ses + SON_PAY, 3), "sahneler": out, "denetim": denetim}
