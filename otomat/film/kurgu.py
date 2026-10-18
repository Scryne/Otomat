"""Kurgu: zaman çizelgesi (anlatım bloklarından çekim süreleri), kare üretimi (PIL) ve ses karışımı (ffmpeg).

Çekim türleri: durağan görselde kamera hareketi (iceri, disari, sol, sag, yukari) ya da Wan klibi (i2v). Bölüm
geçişindeki anlatım boşluğu karartılmış bölüm kartı olur; sonda bitiş ekranı için ~10 sn kuyruk bırakılır.
"""

import math
import subprocess
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from otomat.ayarlar import KOK
from otomat.film.anlatim import Zaman

W, H, FPS = 1920, 1080, 24
I2V_FPS = 24
EN_YAVAS = 0.6  # Wan klibi çekimden kısaysa en çok bu hıza yavaşlatılır, sonra son kare tutulur
KUYRUK = 10.0  # bitiş ekranı (YouTube: son 5-20 sn)
BASLIK_KART = 1.4
YAZI_SURE = 3.6
FONT = KOK / "otomat" / "varliklar" / "fontlar"
KREM = (240, 230, 208)


@dataclass(frozen=True)
class Cekim:
    bas: float
    son: float
    tur: str  # hareket adı, "i2v" ya da "kart"
    kaynak: Path | None  # görsel ya da i2v kare dizini
    yazi: str = ""
    kart: str = ""


def cekimler(
    bolum_no: list[int], zamanlar: list[Zaman], sahneler: list[list[tuple[str, Path, str]]], bolum_adlari: list[str]
) -> list[Cekim]:
    """Blok başına (tür, kaynak, yazı) listesi → bitişik çekimler. Aynı bölümde bloklar arası boşluk önceki bloğun son
    çekimine, bölüm arası boşluk karta gider (ilk bölüm kartsız: soğuk açılış)."""
    sonuc: list[Cekim] = []
    son_an = zamanlar[-1].son + KUYRUK
    for i, (z, ss) in enumerate(zip(zamanlar, sahneler, strict=True)):
        bas = z.bas
        if i and bolum_no[i] != bolum_no[i - 1]:
            kart_bas = zamanlar[i - 1].son
            sonuc.append(Cekim(kart_bas, bas, "kart", None, kart=bolum_adlari[bolum_no[i]]))
        if i + 1 < len(zamanlar):
            son = zamanlar[i].son if bolum_no[i + 1] != bolum_no[i] else zamanlar[i + 1].bas
        else:
            son = son_an
        pay = (son - bas) / len(ss)
        for j, (tur, kaynak, yazi) in enumerate(ss):
            sonuc.append(Cekim(bas + j * pay, bas + (j + 1) * pay, tur, kaynak, yazi))
    return sonuc


def _yumusak(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * min(max(t, 0.0), 1.0))


def kamera(tur: str, t: float) -> tuple[float, float, float]:
    """(ölçek, merkez x, merkez y) kaynak boyutuna oranla; t ∈ [0, 1]."""
    u = _yumusak(t)
    if tur == "iceri":
        return 1.0 + 0.12 * u, 0.5, 0.5
    if tur == "disari":
        return 1.12 - 0.12 * u, 0.5, 0.5
    if tur in ("sol", "sag"):
        k = 1.10
        pay = (1 - 1 / k) / 2
        x = 0.5 + pay * (1 - 2 * u) if tur == "sol" else 0.5 - pay * (1 - 2 * u)
        return k, x, 0.5
    if tur == "yukari":
        k = 1.10
        pay = (1 - 1 / k) / 2
        return k, 0.5, 0.5 + pay * (1 - 2 * u)
    return 1.0 + 0.04 * u, 0.5, 0.5  # i2v ve tutulan kare: fark edilmeyen hafif itiş


def cerceve(img: Image.Image, olcek: float, cx: float, cy: float) -> Image.Image:
    """Kaynağı 16:9'a kaplayıp (ölçek, merkez) kamerasıyla W×H kare çıkar; alt piksel hareket için afin dönüşüm."""
    sw, sh = img.size
    taban = max(W / sw, H / sh)
    k = taban * olcek
    gw, gh = W / k, H / k  # kaynakta görünen alan
    x0 = min(max(cx * sw - gw / 2, 0), sw - gw)
    y0 = min(max(cy * sh - gh / 2, 0), sh - gh)
    return img.transform(
        (W, H), Image.Transform.AFFINE, (1 / k, 0, x0, 0, 1 / k, y0), resample=Image.Resampling.BICUBIC
    )


@cache
def _font(ad: str, boy: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT / ad), boy)


def damga(kare: Image.Image, yazi: str, saydam: float) -> None:
    """Sol üstte tarih/yer damgası: aralıklı büyük harf, krem, koyu kontur ve arkasında yumuşak koyu leke. Yalnız
    gölgeyle açık gökyüzünde okunmuyordu (pilot, ilk çekim)."""
    if saydam <= 0:
        return
    f = _font("SpaceGrotesk-Medium.ttf", 36)
    x0, y = 84, 70
    genislik = sum(f.getlength(h) + 5 for h in yazi.upper())
    leke = Image.new("L", kare.size, 0)
    ImageDraw.Draw(leke).rounded_rectangle((x0 - 30, y - 22, x0 + genislik + 30, y + 62), 30, fill=int(130 * saydam))
    kare.paste(Image.new("RGB", kare.size), (0, 0), leke.filter(ImageFilter.GaussianBlur(18)))
    katman = Image.new("RGBA", kare.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(katman)
    x = x0
    for harf in yazi.upper():
        d.text((x, y), harf, font=f, fill=(*KREM, int(255 * saydam)), stroke_width=2,
               stroke_fill=(0, 0, 0, int(200 * saydam)))  # fmt: skip
        x += f.getlength(harf) + 5
    kare.paste(katman, (0, 0), katman)


def kart(yazi: str, t: float, sure: float) -> Image.Image:
    """Bölüm kartı: siyah zemin, IM Fell başlık, yumuşak giriş-çıkış."""
    kare = Image.new("RGB", (W, H), (8, 8, 10))
    a = min(t / 0.35, (sure - t) / 0.35, 1.0)
    if a <= 0:
        return kare
    f = _font("IMFellEnglish-Regular.ttf", 92)
    d = ImageDraw.Draw(kare)
    renk = tuple(int(c * a + 8 * (1 - a)) for c in KREM)
    d.text((W / 2, H / 2), yazi, font=f, fill=renk, anchor="mm")
    return kare


@cache
def _vinyet() -> Image.Image:
    m = Image.new("L", (W // 8, H // 8), 0)
    d = ImageDraw.Draw(m)
    d.ellipse((-W // 16, -H // 16, W // 8 + W // 16, H // 8 + H // 16), fill=255)
    return m.filter(ImageFilter.GaussianBlur(14)).resize((W, H), Image.Resampling.BILINEAR)


def vinyet(kare: Image.Image) -> Image.Image:
    return Image.composite(kare, Image.new("RGB", (W, H), (0, 0, 0)), _vinyet().point(lambda v: 150 + v * 105 // 255))


@cache
def _gorsel(yol: Path) -> Image.Image:
    return Image.open(yol).convert("RGB")


def _i2v_kareleri(dizin: Path) -> list[Path]:
    return sorted(dizin.glob("*.png"))


def kare_uret(c: Cekim, an: float) -> Image.Image:
    t = an - c.bas
    sure = c.son - c.bas
    if c.tur == "kart":
        return kart(c.kart, t, sure)
    if c.tur == "i2v":
        kareler = _i2v_kareleri(c.kaynak)
        klip = len(kareler) / I2V_FPS
        hiz = max(min(klip / sure, 1.0), EN_YAVAS)
        i = min(int(t * hiz * I2V_FPS), len(kareler) - 1)
        olcek, cx, cy = kamera("i2v", t / sure)
        kare = cerceve(_gorsel(kareler[i]), olcek, cx, cy)
    else:
        olcek, cx, cy = kamera(c.tur, t / sure)
        kare = cerceve(_gorsel(c.kaynak), olcek, cx, cy)
    kare = vinyet(kare)
    if c.yazi:
        damga(kare, c.yazi, min(t / 0.4, (YAZI_SURE - t) / 0.4, 1.0))
    return kare


def sessiz_video(cekim_listesi: list[Cekim], cikti: Path, son: float) -> Path:
    """Kare kare PIL → ffmpeg (rawvideo boru). Bitişte 1 sn karartma."""
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    p = subprocess.Popen(
        [ff, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(cikti)],
        stdin=subprocess.PIPE,
    )  # fmt: skip
    n = int(son * FPS)
    ci = 0
    onceki_kaynak = None
    for k in range(n):
        an = k / FPS
        while ci < len(cekim_listesi) - 1 and an >= cekim_listesi[ci].son:
            ci += 1
        c = cekim_listesi[ci]
        if c.kaynak != onceki_kaynak:
            _gorsel.cache_clear()  # bellekte yalnız o anki çekimin kareleri
            onceki_kaynak = c.kaynak
        kare = kare_uret(c, an)
        if an > son - 1.0:
            kare = Image.blend(kare, Image.new("RGB", (W, H)), min((an - (son - 1.0)) / 1.0, 1.0))
        p.stdin.write(kare.tobytes())
    p.stdin.close()
    if p.wait():
        raise RuntimeError("ffmpeg kare kodlaması düştü")
    return cikti


def miks(
    sessiz: Path,
    anlatim: Path,
    muzikler: list[tuple[float, float, Path]],
    son: float,
    cikti: Path,
    muzik_lufs: float = -27.0,
) -> Path:
    """Anlatım -14 LUFS; müzik yatağı bölüm başına parça (döngü), geçişlerde 2 sn çapraz sönme, toplamda muzik_lufs."""
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    girdiler = ["-i", str(sessiz), "-i", str(anlatim)]
    suzgec = ["[1:a]loudnorm=I=-14:TP=-2:LRA=9,aresample=48000[v]"]
    etiketler = []
    for i, (bas, bit, yol) in enumerate(muzikler):
        girdiler += ["-stream_loop", "-1", "-i", str(yol)]
        uzun = bit - bas + 2.0
        suzgec.append(
            f"[{i + 2}:a]atrim=0:{uzun:.2f},asetpts=PTS-STARTPTS,aresample=48000,"
            f"afade=t=in:d=2,afade=t=out:st={max(uzun - 2.0, 0):.2f}:d=2,"
            f"adelay={int(max(bas - 1.0, 0) * 1000)}|{int(max(bas - 1.0, 0) * 1000)}[m{i}]"
        )
        etiketler.append(f"[m{i}]")
    suzgec.append(
        f"{''.join(etiketler)}amix=inputs={len(etiketler)}:normalize=0:duration=longest,"
        f"atrim=0:{son:.2f},loudnorm=I={muzik_lufs}:TP=-6:LRA=11[m]"
    )
    suzgec.append(
        f"[v][m]amix=inputs=2:duration=longest:normalize=0,atrim=0:{son:.2f},afade=t=out:st={son - 2.5:.2f}:d=2.5,"
        "alimiter=limit=0.84:level=false[a]"  # 0,89'da AAC sonrası tepe -0,5 dBFS çıktı (pilot); hedef ≤ -1
    )
    subprocess.run(
        [ff, "-y", "-v", "error", *girdiler, "-filter_complex", ";".join(suzgec), "-map", "0:v", "-map", "[a]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{son:.2f}", "-movflags", "+faststart", str(cikti)],
        check=True,
    )  # fmt: skip
    return cikti
