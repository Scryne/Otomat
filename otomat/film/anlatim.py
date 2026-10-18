"""Anlatım sesi: Chatterbox (ifade) + Kokoro'nun sentetik sesinden klon (tını), parça başına Whisper denetimi.

Spike (10-17, aynı üç cümle): Kokoro bm_george perde sapması 3,96 yarım ton, Chatterbox klonu 5,33; ikisi de Whisper'da
hatasız. Referans ses Kokoro'dan üretildiği için (Apache-2.0) gerçek bir kişinin sesi klonlanmaz.
"""

import difflib
import hashlib
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


class AnlatimHatasi(RuntimeError):
    def __init__(self, mesaj: str, kayit: list[dict]):
        super().__init__(mesaj)
        self.kayit = kayit


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


BIRLER = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen " \
         "seventeen eighteen nineteen".split()  # fmt: skip
ONLAR = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
SIRA = {"first": 1, "second": 2, "third": 3, "fifth": 5, "eighth": 8, "ninth": 9, "twelfth": 12}
SAYI_SOZ = {**{w: i for i, w in enumerate(BIRLER)}, **{w: i * 10 for i, w in enumerate(ONLAR) if w != "_"}}


def _iki_hane(n: int) -> str:
    return BIRLER[n] if n < 20 else ONLAR[n // 10] + (f"-{BIRLER[n % 10]}" if n % 10 else "")


def yil_yaziya(m: re.Match) -> str:
    """1916 → "nineteen sixteen", 1906 → "nineteen oh six". Chatterbox pilotta "1916"yı "1906" okudu (iki Whisper
    modeli de öyle duydu)."""
    y = int(m.group(0))
    bas, son = divmod(y, 100)
    if son == 0:
        return f"{_iki_hane(bas)} hundred"
    return f"{_iki_hane(bas)} {'oh ' + BIRLER[son] if son < 10 else _iki_hane(son)}"


def soylenis(metin: str) -> str:
    """TTS'e giden metin: aksanlar sadeleşir (Bahía → Bahia), uzun tire virgüle döner, yıllar yazıya çevrilir."""
    metin = metin.replace(" — ", ", ").replace("—", ", ")  # ascii'ye inmeden önce: tire yoksa düşer
    metin = re.sub(r"(?<![\d.])(?<!\d,)1[1-9]\d\d(?!\d|,\d)", yil_yaziya, metin)  # 1,066 gibi sayıya dokunmaz
    return unicodedata.normalize("NFKD", metin).encode("ascii", "ignore").decode()


def _soz(k: str) -> int | None:
    if k in SAYI_SOZ:
        return SAYI_SOZ[k]
    if k in SIRA:
        return SIRA[k]
    if k.endswith("th") and k[:-2] in SAYI_SOZ:  # fourth, sixth, sixteenth
        return SAYI_SOZ[k[:-2]]
    if k.endswith("ieth") and k[:-4] + "y" in SAYI_SOZ:  # twentieth
        return SAYI_SOZ[k[:-4] + "y"]
    return None


def kelimeler(s: str) -> list[str]:
    """Karşılaştırma birimleri: sayı sözleri ve rakamlar aynı biçime iner ("one thousand and sixty-six", "1,066" ve
    "21st", "twenty-first" → "1066", "21"). Whisper rakam yazıyor, senaryo söz; inmeyince doğru parça 0,22 fark alıp
    üç kez yeniden üretiliyordu (pilot)."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().replace("-", " ")
    s = re.sub(r"(?<=\d),(?=\d{3})", "", s)
    s = re.sub(r"\b(\d+)(st|nd|rd|th)\b", r"\1", s)
    # Whisper "a dollar" → "$1", "three dollars" → "$3" yazıyor ($ düşer): kelime karşılaştırmadan çıkar (Klondike)
    s = re.sub(r"\ban? dollar\b", "1", s)
    s = re.sub(r"\bdollars?\b", "", s)
    # ondalık: "12.5" ve "twelve and a half" → "12p5" (nokta sayıyı ikiye bölüp yanlış alarm veriyordu, Lowell)
    s = re.sub(r"(\d+)\.(\d+)", r"\1p\2", s)
    s = re.sub(r"\band a half\b", "p5", s)
    cikti: list[str] = []
    toplam = simdiki = None
    onceki = ""
    for k in re.findall(r"[a-z0-9']+|[.,;:!?]", s) + [""]:
        if k and k in ".,;:!?":
            # noktalama sayıyı keser ("a proven one, fifty thousand" 51000 oluyordu);
            # "seven thousand, one hundred" sürer
            if not (k == "," and onceki in ("thousand", "million") and simdiki is not None):
                if simdiki is not None:
                    cikti.append(str(toplam + simdiki))
                    toplam = simdiki = None
            onceki = k
            continue
        son_kelime, onceki = onceki, k
        if k in ("thousand", "million") and simdiki is None and cikti and cikti[-1].isdigit():
            cikti[-1] = str(int(cikti[-1]) * (1000 if k == "thousand" else 1_000_000))  # Whisper "25 million"
            continue
        n = _soz(k)
        if n is not None or k in ("hundred", "thousand", "million"):
            if simdiki is None:  # "a hundred" = 100
                toplam, simdiki = 0, (0 if n is not None else 1)
            if k == "hundred":
                simdiki *= 100
            elif k in ("thousand", "million"):
                toplam += simdiki * (1000 if k == "thousand" else 1_000_000)
                simdiki = 0
            else:
                simdiki += n
            continue
        # "one thousand and sixty" sürer; "between eighteen and twenty-five" iki sayıdır (43 oluyordu, Ellis)
        if k == "and" and simdiki is not None and son_kelime in ("hundred", "thousand", "million"):
            continue
        if simdiki is not None:
            cikti.append(str(toplam + simdiki))
            toplam = simdiki = None
        if k:
            if re.fullmatch(r"p\d+", k) and cikti and cikti[-1].isdigit():
                cikti[-1] += k  # "twelve" + "p5"
                continue
            cikti.append(k)
    for i in range(len(cikti) - 2):  # "thirty to forty thousand" = 30000 to 40000 (Whisper aralığı açık yazıyor)
        a, ara, b = cikti[i : i + 3]
        if a.isdigit() and ara in ("to", "or") and b.isdigit():
            n, m = int(a), int(b)
            if n < 1000 <= m and m % 1000 == 0 and n * 1000 <= m:
                cikti[i] = str(n * 1000)
    return cikti


def sayilar(s: str) -> list[str]:
    return sorted(k for k in kelimeler(s) if re.fullmatch(r"\d+(p\d+)?", k))


def fark(metin: str, duyulan: str) -> float:
    """Kelime farkı; sayılar (yıl, süre, kişi sayısı) uyuşmuyorsa 1: bir yanlış yıl kelime oranında kaybolup geçiyordu
    (pilotta "1906", fark 0,048)."""
    a, b = kelimeler(metin), kelimeler(duyulan)
    if not a:
        return 0.0
    if sayilar(metin) != sayilar(duyulan):
        return 1.0
    return 1 - difflib.SequenceMatcher(None, a, b).ratio()


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
    secim: dict[tuple[int, int], tuple[float, Path]] = {}
    kayit: list[dict] = []
    whisper = WhisperModel("small.en", device="cpu", compute_type="int8")
    acik = parcalar
    for deneme in range(DENEME):
        isler = []
        for bi, pi, p in acik:
            metin = soylenis(p)
            iz = hashlib.sha1(metin.encode()).hexdigest()[:8]  # metin değişince eski ses kullanılmasın
            isler.append({"metin": metin, "hedef": str(dizin / f"p{bi:03d}_{pi}_{deneme}_{iz}.wav"), "tohum": deneme})
        _uret(isler, ref, dizin)
        kalan = []
        for (bi, pi, p), is_ in zip(acik, isler, strict=True):
            x = wav_oku(Path(is_["hedef"]))
            duyulan = " ".join(s.text for s in whisper.transcribe(_16k(x), language="en")[0])
            f = fark(p, duyulan)
            kayit.append({"blok": bi, "parca": pi, "deneme": deneme, "fark": round(f, 3), "duyulan": duyulan.strip()})
            if (bi, pi) not in secim or f < secim[(bi, pi)][0]:
                secim[(bi, pi)] = (f, Path(is_["hedef"]))
            if f > HATA_ESIGI:
                kalan.append((bi, pi, p))
        acik = kalan
        if not acik:
            break
    if yanlis := [(bi, pi) for (bi, pi), (f, _) in secim.items() if f >= 1.0]:
        raise AnlatimHatasi(f"{DENEME} denemede sayısı doğru okunmayan parça: {yanlis} (ses/denetim.json)", kayit)
    toplam, zamanlar, an = [], [], 0.0
    for bi, (bolum, _) in enumerate(bloklar):
        if bi:
            ara = ARA_BOLUM if bolum != bloklar[bi - 1][0] else ARA_BLOK
            toplam.append(np.zeros(int(ara * SR), np.float32))
            an += ara
        bas = an
        pis = sorted(pi for b, pi in secim if b == bi)
        for j, pi in enumerate(pis):
            x = sessizlik_kirp(wav_oku(secim[(bi, pi)][1]))
            toplam.append(x)
            an += len(x) / SR
            if j < len(pis) - 1:
                toplam.append(np.zeros(int(ARA_PARCA * SR), np.float32))
                an += ARA_PARCA
        zamanlar.append(Zaman(round(bas, 3), round(an, 3)))
    yol = dizin / "anlatim.wav"
    wav_yaz(yol, np.concatenate(toplam))
    return yol, zamanlar, kayit


def _16k(x: np.ndarray) -> np.ndarray:
    n = int(len(x) * 16000 / SR)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
