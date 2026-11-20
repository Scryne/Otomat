"""Müzik yatağı: bölüm başına kendi ruh halinde, tam uzunlukta üretilen parça (ACE-Step 1.5) + anlatıma göre kısılma.

Neden (11-20 izleyici geri bildirimi): tek Kevin MacLeod parçası 5 dakika döngüde çaldı, "çok kötü, aynı şey dönüyor,
bayıyor". Araştırma (docs/arastirma/14-trend-kanali.md, Faz 20 ses/müzik bölümü): hazır kütüphanelerin hepsi Content ID
riski taşıyor; yerel üretim (ACE-Step 1.5, MIT) 4060'ta 95 sn parçayı ~9 sn'de veriyor ve kimsenin kataloğunda değil.

Kurallar:
- Bölüm sınırında parça ve his değişir (Johnny Harris: "thinking" / "feeling" müziği dönüşümlü); 3 sn çapraz geçiş.
- Parça bölüm süresi kadar üretilir: döngü yok.
- Kısılma zarfı konuşma zamanından hesaplanır (sidechain pompalamaz): konuşma altında -20 dB, 0,45 sn'den uzun
  boşlukta -12 dB, bölüm kartında -9 dB. Rakamın söylendiği andan hemen önce kısa nefes (müzik çekilir).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 48000
ACE_DIZIN = Path(os.environ.get("OTOMAT_ACE_DIZIN", Path.home() / "ace-step"))
ACE_PY = ACE_DIZIN / ".venv" / "Scripts" / "python.exe"
ORTAK = "modern documentary film score, polished high production quality, instrumental, no vocals, no singing"
RUHLAR = {  # ruh hali → (istem, bpm)
    "merak": ("curious inquisitive underscore, pulsing muted synth arpeggio, soft felt piano, light ticking percussion, "
              "warm sub bass", 100),
    "gerilim": ("dark tense investigative underscore, low cello ostinato, ticking clock percussion, deep pulsing synth, "
                "building suspense", 92),
    "dram": ("emotional cinematic underscore, slow strings swelling, solo piano motif, deep low drones, bittersweet", 76),
    "umut": ("hopeful uplifting underscore, bright plucked guitar and piano, gentle strings rising, soft steady drums",
             108),
    "enerji": ("driving energetic underscore, punchy electronic drums, bold bass synth, rhythmic staccato strings, "
               "momentum", 120),
    "sakin": ("calm reflective ambient underscore, airy pads, sparse warm piano notes, slow evolving textures", 70),
    "karanlik": ("ominous brooding underscore, dark drones, distant metallic hits, sub bass pulses, unsettling", 84),
}  # fmt: skip
KONUSMA_DB, BOSLUK_DB, BOLUM_DB, NEFES_DB = -20.0, -12.0, -9.0, -26.0
GECIS = 3.0  # bölümler arası çapraz geçiş (sn)


def bolumler(sahneler: list[dict], muzik_plani: dict | None, toplam: float) -> list[dict]:
    """Plan sahnelerinden müzik bölümleri: kanca (ilk bolum kartına kadar), her bölüm, son iki sahne kapanış.
    Dönüş: [{bas, son, ruh}] (videonun saniyesi)."""
    mp = muzik_plani or {}
    ruh_b = [r for r in (mp.get("bolumler") or [])]
    sinirlar = [sh["bas"] for sh in sahneler if sh.get("tur") == "bolum"]
    out = []
    bas = 0.0
    out_ruh = [mp.get("kanca") or "merak"]
    for i, t in enumerate(sinirlar):
        out.append({"bas": bas, "son": t})
        bas = t
        out_ruh.append(ruh_b[i] if i < len(ruh_b) and ruh_b[i] else ("gerilim", "merak", "dram", "enerji")[i % 4])
    kapanis_bas = sahneler[-2]["bas"] if len(sahneler) >= 3 else toplam
    if kapanis_bas - bas > 20:
        out.append({"bas": bas, "son": kapanis_bas})
        out_ruh.append(mp.get("kapanis") or "umut")
        bas = kapanis_bas
    out.append({"bas": bas, "son": toplam})
    for b, r in zip(out, out_ruh, strict=False):
        b["ruh"] = r if r in RUHLAR else "merak"
    # 12 sn'den kısa bölüm öncekine katılır (parça değişimi anlamsız kalır)
    birlesik: list[dict] = []
    for b in out:
        if birlesik and b["son"] - b["bas"] < 12:
            birlesik[-1]["son"] = b["son"]
        else:
            birlesik.append(dict(b))
    # aynı ruh art arda gelirse farklı tohumla yine yeni parça üretilir (aynı parça iki kez çalmasın)
    return birlesik


def _hedef(dizin: Path, b: dict, i: int, tohum: int) -> Path:
    istem, bpm = RUHLAR[b["ruh"]]
    sure = round(b["son"] - b["bas"] + GECIS * 2 + 2)
    iz = hashlib.sha1(f"{istem}|{bpm}|{sure}|{tohum + i}".encode()).hexdigest()[:8]
    return dizin / f"m{i:02d}_{b['ruh']}_{iz}.wav"


def uret(bolum_listesi: list[dict], dizin: Path, tohum: int = 7) -> list[Path]:
    dizin.mkdir(parents=True, exist_ok=True)
    isler, yollar = [], []
    for i, b in enumerate(bolum_listesi):
        istem, bpm = RUHLAR[b["ruh"]]
        y = _hedef(dizin, b, i, tohum)
        yollar.append(y)
        sure = min(600, max(20, round(b["son"] - b["bas"] + GECIS * 2 + 2)))
        isler.append({"istem": f"{istem}, {ORTAK}", "bpm": bpm, "sure": sure, "tohum": tohum + i, "hedef": str(y)})
    if any(not y.exists() for y in yollar):
        gorev = dizin / "muzik_is.json"
        gorev.write_text(json.dumps({"isler": isler}), encoding="utf-8")
        subprocess.run([str(ACE_PY), "-I", str(Path(__file__).with_name("muzik_isci.py")), str(gorev)],
                       cwd=ACE_DIZIN, check=True)  # fmt: skip
    return yollar


def _oku(yol: Path, kanal: int = 2) -> np.ndarray:
    ham = subprocess.run(["ffmpeg", "-v", "error", "-i", str(yol), "-ac", str(kanal), "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout  # fmt: skip
    return np.frombuffer(ham, np.float32).reshape(-1, kanal).copy()


def _lufs_yaklasik(x: np.ndarray) -> float:
    """Kaba yüksek ses ölçüsü (RMS dBFS, sessiz kısımlar hariç): parçaları birbirine eşitlemek için yeter."""
    m = x.mean(axis=1)
    pencere = SR // 2
    n = len(m) // pencere
    if not n:
        return -30.0
    rms = np.sqrt((m[: n * pencere].reshape(n, pencere) ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    db = db[db > db.max() - 20]
    return float(np.mean(db))


def zarf(konusma: np.ndarray, toplam_n: int, sahneler: list[dict]) -> np.ndarray:
    """Müzik kazancı (doğrusal, örnek başına). Konuşma etkinliği anlatım RMS'inden (10 ms çerçeve)."""
    cerceve = SR // 100
    m = np.abs(konusma.mean(axis=1))
    n = min(len(m) // cerceve, toplam_n // cerceve + 1)
    rms = np.sqrt((m[: n * cerceve].reshape(n, cerceve) ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    aktif = db > (np.percentile(db, 99) - 38)
    # 0,45 sn'den kısa boşluklar konuşma sayılır (kelime arası nefeste müzik zıplamasın)
    hedef = np.full(toplam_n // cerceve + 1, BOSLUK_DB)
    hedef[:n][aktif] = KONUSMA_DB
    i = 0
    while i < n:
        if not aktif[i]:
            j = i
            while j < n and not aktif[j]:
                j += 1
            if j - i < 45 and i > 0 and j < n:
                hedef[i:j] = KONUSMA_DB
            i = j
        else:
            i += 1
    # bölüm kartı: müzik öne çıkar (anlatım kısa başlık satırı), konuşma altında yine kısılır
    for sh in sahneler:
        a, b = int(sh["bas"] * 100), int((sh["bas"] + sh["sure"]) * 100)
        if sh.get("tur") == "bolum":
            dilim = hedef[a:b]
            dilim[dilim > KONUSMA_DB] = BOLUM_DB
        if sh.get("tur") == "sayi":  # rakamdan hemen önce müzik çekilir (vurgu öncesi boşluk)
            for k in sh.get("kelimeler") or []:
                if re.search(r"\d", k["w"]):
                    t = int((sh["bas"] + k["s"]) * 100)
                    hedef[max(0, t - 45) : t + 5] = np.minimum(hedef[max(0, t - 45) : t + 5], NEFES_DB)
                    break
    # yumuşatma: inerken 0,12 sn, çıkarken 0,6 sn
    yumusak = np.empty_like(hedef)
    v = hedef[0]
    a_in, a_out = 1 - np.exp(-1 / 12), 1 - np.exp(-1 / 60)
    for i, h in enumerate(hedef):
        v += (h - v) * (a_in if h < v else a_out)
        yumusak[i] = v
    kazanc = 10 ** (yumusak / 20)
    return np.repeat(kazanc, cerceve)[:toplam_n]


def karistir(anlatim: Path, parcalar: list[Path], bolum_listesi: list[dict], sahneler: list[dict], toplam: float,
             hedef: Path) -> Path:  # fmt: skip
    """Anlatım + bölüm parçaları (çapraz geçişli, kısılmalı) → tek stereo 48 kHz WAV."""
    n = int(toplam * SR)
    ses = _oku(anlatim)
    ses *= 10 ** ((-16.0 - _lufs_yaklasik(ses)) / 20)  # anlatım -16, müzik -14 tabanından kısılır (≈18 dB altta)
    konusma = np.zeros((n, 2), np.float32)
    konusma[: min(n, len(ses))] = ses[:n]
    yatak = np.zeros((n, 2), np.float32)
    for i, (b, p) in enumerate(zip(bolum_listesi, parcalar, strict=True)):
        x = _oku(p)
        x *= 10 ** ((-14.0 - _lufs_yaklasik(x)) / 20)  # parçalar aynı seviyeye
        bas = 0 if i == 0 else int((b["bas"] - GECIS / 2) * SR)
        son = n if i == len(bolum_listesi) - 1 else int((b["son"] + GECIS / 2) * SR)
        uz = min(son - bas, len(x))
        parca = x[:uz].copy()
        g = int(GECIS * SR)
        if i > 0:  # giriş çapraz geçişi (eşit güç)
            k = min(g, uz)
            parca[:k] *= np.sin(np.linspace(0, np.pi / 2, k))[:, None]
        else:
            k = min(int(0.8 * SR), uz)
            parca[:k] *= np.linspace(0, 1, k)[:, None]
        if i < len(bolum_listesi) - 1:
            k = min(g, uz)
            parca[uz - k :] *= np.cos(np.linspace(0, np.pi / 2, k))[:, None]
        else:  # son: 4 sn yumuşak çıkış
            k = min(int(4 * SR), uz)
            parca[uz - k :] *= np.linspace(1, 0, k)[:, None]
        yatak[bas : bas + uz] += parca
    yatak *= zarf(konusma, n, sahneler)[:, None]
    karisim = konusma + yatak
    tepe = float(np.abs(karisim).max())
    if tepe > 0.97:
        karisim *= 0.97 / tepe
    hedef.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(hedef), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(karisim, -1, 1) * 32767).astype(np.int16).tobytes())
    return hedef
