"""S16: "kart" formatı. Nişte tutarlı izlenen küçük kanallar (Dark History, History Flash, Past Vault: son 50 videonun
medyanı 23-31 bin; 10-14 rakip taraması) hikâyeyi anlatıcısız, tek paragraf ekran yazısıyla veriyor: üstte kısa kanca,
altında 40-55 kelimelik paragraf (anahtar sözler renkli), altında konunun gerçek görseli, 6-8 sn, müzik. Paragraf bir
okumada bitmez, izleyici videoyu döndürür. Bu betik formatın görünüşünü elle yazılmış metinle sınar (üretime bağlı değil).

Çalıştırma: uv run python spikes/s16_kart.py <ornekler.json> <cikti_klasoru>
ornekler.json: [{"ad", "kanca", "metin" ([[vurgu]] işaretli), "gorsel", "atif"}]
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

KOK = Path(__file__).resolve().parents[1]
FONT = KOK / "otomat" / "varliklar" / "fontlar"
G, Y, FPS, SURE = 1080, 1920, 30, 7.0
ZEMIN = (12, 12, 14)
VURGU = ["#FFD84D", "#FF8A3D", "#7FE07A"]
KENAR = 64
METIN_UST = 250
GORSEL_ALT = 1500  # altındaki ~420 px Shorts arayüzünün (başlık, kanal, düğmeler) altında kalır


def font(ad: str, boy: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT / ad), boy)


def parcala(metin: str) -> list[tuple[str, int]]:
    """[[vurgu]] işaretli metin → (kelime, renk sırası; -1 düz). Vurgu sırayla renk alır."""
    kelimeler, vurgu_no = [], 0
    for parca in re.split(r"(\[\[.+?\]\])", metin):
        if parca.startswith("[["):
            for w in parca[2:-2].split():
                kelimeler.append((w, vurgu_no % len(VURGU)))
            vurgu_no += 1
        else:
            kelimeler += [(w, -1) for w in parca.split()]
    return kelimeler


def satirla(kelimeler, f: ImageFont.FreeTypeFont, genislik: int) -> list[list[tuple[str, int]]]:
    satirlar, satir = [], []
    for k in kelimeler:
        deneme = " ".join(w for w, _ in [*satir, k])
        if satir and f.getlength(deneme) > genislik:
            satirlar.append(satir)
            satir = []
        satir.append(k)
    return [*satirlar, satir] if satir else satirlar


def ust_katman(kanca: str, metin: str, kanal: str) -> tuple[Image.Image, int]:
    """Sabit katman (kanal adı, kanca, paragraf) ve paragrafın bittiği y."""
    kat = Image.new("RGBA", (G, Y), (0, 0, 0, 0))
    d = ImageDraw.Draw(kat)
    fk = font("Barlow-Medium.ttf", 34)
    d.text((G / 2, METIN_UST - 70), kanal.upper(), font=fk, fill=(170, 170, 170), anchor="mm")
    y = METIN_UST
    for boy in (92, 84, 76):
        fh = font("BarlowCondensed-Bold.ttf", boy)
        if fh.getlength(kanca.upper()) <= G - 2 * KENAR:
            break
    d.text((G / 2, y), kanca.upper(), font=fh, fill=VURGU[0], anchor="mt", stroke_width=2, stroke_fill="black")
    y += boy + 34
    kelimeler = parcala(metin)
    for boy in (54, 50, 46, 42):
        fp = font("Barlow-Medium.ttf", boy)
        satirlar = satirla(kelimeler, fp, G - 2 * KENAR)
        if y + len(satirlar) * boy * 1.22 < GORSEL_ALT - 520:
            break
    bosluk = fp.getlength(" ")
    for satir in satirlar:
        genislik = fp.getlength(" ".join(w for w, _ in satir))
        x = (G - genislik) / 2
        for w, r in satir:
            renk = VURGU[r] if r >= 0 else "white"
            d.text((x, y), w, font=fp, fill=renk, stroke_width=2, stroke_fill="black")
            x += fp.getlength(w) + bosluk
        y += int(boy * 1.22)
    return kat, y


def kareler(gorsel: Path, kanca: str, metin: str, atif: str, kanal: str):
    kat, metin_alt = ust_katman(kanca, metin, kanal)
    ust = metin_alt + 36
    alan = (G, GORSEL_ALT - ust)
    img = Image.open(gorsel).convert("RGB")
    # alanı kaplayacak ölçek (+%8 zoom payı), görselin üst-orta kısmı korunur
    olcek = max(alan[0] / img.width, alan[1] / img.height) * 1.08
    buyuk = img.resize((round(img.width * olcek), round(img.height * olcek)), Image.LANCZOS)
    fa = font("Barlow-Regular.ttf", 24)
    n = int(SURE * FPS)
    for i in range(n):
        s = 1.08 - 0.08 * i / (n - 1)  # yavaş geri çekilme: kare sabit görünmesin, metin yerinde kalsın
        w, h = alan[0] * 1.08 / s, alan[1] * 1.08 / s
        cx = buyuk.width / 2
        cy = min(max(h / 2, buyuk.height * 0.45), buyuk.height - h / 2)  # uzun görselde üst-orta (yüzler)
        kutu = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
        parca = buyuk.crop(tuple(round(v) for v in kutu)).resize(alan, Image.BILINEAR)
        kare = Image.new("RGB", (G, Y), ZEMIN)
        kare.paste(parca, (0, ust))
        # görselin üst ve alt kenarı zemine yumuşak geçsin
        golge = Image.linear_gradient("L").resize((G, 60))
        kare.paste(Image.new("RGB", (G, 60), ZEMIN), (0, ust), Image.eval(golge, lambda p: 255 - p))
        kare.paste(Image.new("RGB", (G, 60), ZEMIN), (0, GORSEL_ALT - 60), golge)
        kare.paste(kat, (0, 0), kat)
        ImageDraw.Draw(kare).text((G - KENAR, GORSEL_ALT - 30), atif, font=fa, fill=(150, 150, 150), anchor="rs")
        yield kare


def render(ornek: dict, cikti: Path, kanal: str = "Inkwell Oddities") -> Path:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    p = subprocess.Popen(
        [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{G}x{Y}", "-r", str(FPS),
         "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(cikti)],
        stdin=subprocess.PIPE,
    )  # fmt: skip
    for k in kareler(Path(ornek["gorsel"]), ornek["kanca"], ornek["metin"], ornek["atif"], kanal):
        p.stdin.write(np.asarray(k).tobytes())
    p.stdin.close()
    p.wait()
    return cikti


def main():
    ornekler = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    cikti = Path(sys.argv[2])
    cikti.mkdir(parents=True, exist_ok=True)
    for o in ornekler:
        print(render(o, cikti / f"{o['ad']}.mp4"))


if __name__ == "__main__":
    main()
