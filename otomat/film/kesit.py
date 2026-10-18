"""Filmden dikey Shorts kesiti (K-34): senaryodaki `kesitler` aralığı bitmiş `video.mp4`'ten kesilir, 1080×1920'ye
yerleştirilir (bulanık zemin + ortada 4:3 görüntü), üstte başlık, altında kelime zamanlı altyazı.

Altyazının metni senaryodan, zamanı Whisper'dan gelir: Whisper "Dyea"yı "Dyer", "Mountie"yi "bounty" yazıyordu (Klondike
uçtan uca denetimi); eşleşmeyen kelimenin zamanı komşularından aradeğerlenir. Yerleşim Shorts arayüzünün güvenli
alanında: alttaki ~%25 (başlık, kanal adı) ve sağdaki düğme sütunu boş kalır.

    uv run python -m otomat.film.kesit filmler/<slug>/senaryo.json
"""

import difflib
import json
import re
import subprocess
import sys
from functools import cache
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from otomat.film import kurgu, senaryo, uretim

W, H, FPS = 1080, 1920, 24
EN_UZUN = 59.0  # Shorts 3 dakikaya kadar kabul ediyor ama kesit kısa ve tek fikir olmalı
ON_PAY, ARKA_PAY = 0.25, 0.6
ON_Y, ON_W, ON_H = 450, 1080, 810  # ortadaki görüntü (4:3)
BASLIK_Y = (170, 420)
ALTYAZI_Y = 1345
KAPANIS = 2.0  # son saniyeler: altyazı yerine kanal çağrısı
KAPANIS_YAZI = "FULL FILM ON THE CHANNEL"


class KesitHatasi(RuntimeError):
    pass


def aralik(blok_zaman: list[list[float]], k: senaryo.Kesit, sure: float) -> tuple[float, float]:
    bas = max(blok_zaman[k.ilk][0] - ON_PAY, 0.0)
    son = min(blok_zaman[k.son][1] + ARKA_PAY, sure)
    if son - bas > EN_UZUN:
        raise KesitHatasi(f"'{k.baslik}': {son - bas:.1f} sn > {EN_UZUN} (bloklar {k.ilk}-{k.son})")
    return bas, son


def _norm(k: str) -> str:
    return re.sub(r"[^a-z0-9]", "", k.lower())


def hizala(metin: str, duyulan: list[tuple[str, float, float]]) -> list[tuple[str, float, float]]:
    """Senaryonun kelimelerine Whisper kelime zamanlarını giydirir; eşleşmeyene komşulardan aradeğer."""
    kelimeler = metin.split()
    a, b = [_norm(k) for k in kelimeler], [_norm(k) for k, _, _ in duyulan]
    zaman: list[tuple[float, float] | None] = [None] * len(kelimeler)
    for blok in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for i in range(blok.size):
            _, s, e = duyulan[blok.b + i]
            zaman[blok.a + i] = (s, e)
    toplam = duyulan[-1][2] if duyulan else 0.0
    i = 0
    while i < len(zaman):
        if zaman[i] is not None:
            i += 1
            continue
        j = i
        while j < len(zaman) and zaman[j] is None:
            j += 1
        sol = zaman[i - 1][1] if i else 0.0
        sag = zaman[j][0] if j < len(zaman) else max(toplam, sol + 0.3 * (j - i))
        adim = (sag - sol) / (j - i)
        for n in range(i, j):
            zaman[n] = (sol + adim * (n - i), sol + adim * (n - i + 1))
        i = j
    return [(k, s, e) for k, (s, e) in zip(kelimeler, zaman, strict=True)]


def gruplar(kelimeler: list[tuple[str, float, float]], en_cok: int = 3) -> list[tuple[str, float, float]]:
    """Ekranda 1-3 kelimelik parçalar; cümle sonu parçayı kapatır."""
    sonuc, simdiki = [], []
    for k in kelimeler:
        simdiki.append(k)
        if len(simdiki) == en_cok or k[0][-1] in ".!?,;:":
            sonuc.append((" ".join(x[0] for x in simdiki), simdiki[0][1], simdiki[-1][2]))
            simdiki = []
    if simdiki:
        sonuc.append((" ".join(x[0] for x in simdiki), simdiki[0][1], simdiki[-1][2]))
    # boşlukta önceki yazı ekranda kalsın (titreme olmasın)
    return [(m, s, sonuc[i + 1][1] if i + 1 < len(sonuc) else e) for i, (m, s, e) in enumerate(sonuc)]


@cache
def _font(ad: str, boy: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(kurgu.FONT / ad), boy)


def _sar(metin: str, f: ImageFont.FreeTypeFont, genislik: int) -> list[str]:
    satirlar, simdiki = [], ""
    for k in metin.split():
        aday = f"{simdiki} {k}".strip()
        if f.getlength(aday) <= genislik:
            simdiki = aday
        else:
            satirlar.append(simdiki)
            simdiki = k
    return satirlar + [simdiki] if simdiki else satirlar


def baslik_katmani(baslik: str) -> Image.Image:
    katman = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(katman)
    boy = 84
    while True:
        f = _font("LuckiestGuy-Regular.ttf", boy)
        satirlar = _sar(baslik.upper(), f, 940)
        if len(satirlar) <= 3 or boy <= 56:
            break
        boy -= 6
    satir_h = boy * 1.12
    y = (BASLIK_Y[0] + BASLIK_Y[1]) / 2 - satir_h * len(satirlar) / 2 + satir_h / 2
    for s in satirlar:
        d.text((W / 2, y), s, font=f, fill="white", anchor="mm", stroke_width=7, stroke_fill="black")
        y += satir_h
    return katman


def kare(goruntu: Image.Image, ust: Image.Image, yazi: str, saydam: float = 1.0) -> Image.Image:
    kucuk = goruntu.resize((341, 192), Image.Resampling.BILINEAR).crop((116, 0, 224, 192))
    zemin = kucuk.filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.Resampling.BILINEAR)
    zemin = Image.blend(Image.new("RGB", (W, H)), zemin, 0.45)
    on = goruntu.crop((240, 0, 1680, 1080)).resize((ON_W, ON_H), Image.Resampling.LANCZOS)
    zemin.paste(on, (0, ON_Y))
    zemin.paste(ust, (0, 0), ust)
    if yazi:
        d = ImageDraw.Draw(zemin)
        f = _font("LuckiestGuy-Regular.ttf", 76)
        for i, s in enumerate(_sar(yazi.upper(), f, 900)[:2]):
            renk = tuple(int(c * saydam) for c in (255, 214, 102))
            d.text((W / 2, ALTYAZI_Y + i * 84), s, font=f, fill=renk, anchor="mm", stroke_width=7, stroke_fill="black")
    return zemin


def _ses16k(video: Path, bas: float, sure: float) -> np.ndarray:
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    ham = subprocess.run(
        [ff, "-v", "error", "-ss", f"{bas:.3f}", "-t", f"{sure:.3f}", "-i", str(video), "-ac", "1", "-ar", "16000",
         "-f", "f32le", "-"], capture_output=True, check=True,
    ).stdout  # fmt: skip
    return np.frombuffer(ham, np.float32)


def uret(film: senaryo.Film, sira: int, whisper=None) -> Path:
    d = uretim.dizin(film)
    hedef = d / "kesit" / f"{sira:02d}.mp4"
    if hedef.exists():
        return hedef
    k = film.kesitler[sira]
    bilgi = json.loads((d / "kurgu.json").read_text(encoding="utf-8"))
    if "blok_zaman" not in bilgi:
        raise KesitHatasi(f"{film.slug}: kurgu.json'da blok_zaman yok (uretim ... zaman)")
    video = d / "video.mp4"
    bas, son = aralik(bilgi["blok_zaman"], k, bilgi["sure"])
    sure = son - bas
    if whisper is None:
        from faster_whisper import WhisperModel

        whisper = WhisperModel("small.en", device="cpu", compute_type="int8")
    parcalar, _ = whisper.transcribe(_ses16k(video, bas, sure), language="en", word_timestamps=True)
    duyulan = [(w.word.strip(), w.start, w.end) for p in parcalar for w in (p.words or [])]
    metin = " ".join(b.anlatim for _, b in film.bloklar()[k.ilk : k.son + 1])
    yazilar = gruplar(hizala(metin, duyulan))
    ust = baslik_katmani(k.baslik)

    hedef.parent.mkdir(parents=True, exist_ok=True)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    oku = subprocess.Popen(
        [ff, "-v", "error", "-ss", f"{bas:.3f}", "-t", f"{sure:.3f}", "-i", str(video), "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE,
    )  # fmt: skip
    yaz = subprocess.Popen(
        [ff, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-ss", f"{bas:.3f}", "-t", f"{sure:.3f}", "-i", str(video), "-map", "0:v", "-map", "1:a",
         "-af", f"afade=t=in:d=0.3,afade=t=out:st={max(sure - 0.6, 0):.2f}:d=0.6",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
         "-shortest", "-movflags", "+faststart", str(hedef)], stdin=subprocess.PIPE,
    )  # fmt: skip
    boyut = kurgu.W * kurgu.H * 3
    n = 0
    while ham := oku.stdout.read(boyut):
        if len(ham) < boyut:
            break
        an = n / FPS
        g = Image.frombytes("RGB", (kurgu.W, kurgu.H), ham)
        if an >= sure - KAPANIS:
            yazi, saydam = KAPANIS_YAZI, min((an - (sure - KAPANIS)) / 0.3, 1.0)
        else:
            yazi = next((m for m, s, e in yazilar if s <= an < e), "")
            saydam = 1.0
        yaz.stdin.write(kare(g, ust, yazi, saydam).tobytes())
        n += 1
    yaz.stdin.close()
    if oku.wait() or yaz.wait():
        hedef.unlink(missing_ok=True)
        raise KesitHatasi(f"ffmpeg kesit kodlaması düştü: {hedef}")
    return hedef


def main() -> None:
    film = senaryo.oku(Path(sys.argv[1]))
    if not film.kesitler:
        raise SystemExit(f"{film.slug}: senaryoda kesit yok")
    from faster_whisper import WhisperModel

    w = WhisperModel("small.en", device="cpu", compute_type="int8")
    for i, k in enumerate(film.kesitler):
        print(i, k.baslik, uret(film, i, w), flush=True)


if __name__ == "__main__":
    main()
