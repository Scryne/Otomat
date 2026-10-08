"""Format spike'ı: Wikipedia'nın tuhaf-ama-gerçek makalesinden 30-40 sn'lik hikâye Short'u.

Kaynak havuzu: Wikipedia:Unusual articles (editörlerin seçtiği ~2.500 makale + tek satırlık esprili tanım).
Görsel: makalenin Commons görselleri (AI yok), Ken Burns. Ses: Kokoro. Metin: yerel LLM, sayı/ad kapısı.

    uv run python spikes/s10_hikaye.py havuz
    uv run python spikes/s10_hikaye.py video "Bal des Ardents" [--cikti spikes/out/hikaye]
"""

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from otomat.anlati.llm import json_uret
from otomat.ayarlar import KOK
from otomat.ses import altyazi_parcalari, seslendir

UA = {"User-Agent": "Otomat/0.1 (https://github.com/Scryne; daily educational shorts)"}
API = "https://en.wikipedia.org/w/api.php"
COMMONS = "https://commons.wikimedia.org/w/api.php"
ALT = [
    "History",
    "Science",
    "Technology, inventions and products",
    "Food",
    "Sports",
    "Folklore",
    "Society, economy and law",
    "Military",
    "Places and infrastructure",
]
G, Y, FPS = 1080, 1920, 30
FONT = KOK / "otomat/varliklar/fontlar/BarlowCondensed-Bold.ttf"
UYGUN_LISANS = re.compile(r"^(public domain|pd|cc0|cc by(-sa)? \d)", re.I)
RED_AD = re.compile(r"(logo|icon|flag|map|symbol|commons|wiki|edit|question|ambox|signature|coat of arms)", re.I)


def al(url: str, params: dict) -> dict:
    for deneme in range(4):
        try:
            istek = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers=UA)
            return json.load(urllib.request.urlopen(istek, timeout=30))
        except urllib.error.HTTPError as e:
            if e.code != 429 or deneme == 3:
                raise
            time.sleep(5 * (deneme + 1))
    raise RuntimeError


def havuz() -> None:
    tum = []
    for a in ALT:
        t = al(
            API,
            dict(
                action="parse", page=f"Wikipedia:Unusual articles/{a}", prop="wikitext", format="json", formatversion=2
            ),
        )["parse"]["wikitext"]
        for baslik, tanim in re.findall(
            r"^\|-\s*\n\|\s*(?:\{\{[^}]*\}\}\s*)?'*\[\[([^\]|]+)(?:\|[^\]]*)?\]\]'*\s*\n\|\s*(.+)$", t, re.M
        ):
            tanim = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", tanim)
            tum.append({"baslik": baslik, "tanim": tanim, "bolum": a})
        time.sleep(1.5)
    Path("calisma/hikaye_havuz.json").write_text(json.dumps(tum, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(tum))


def makale(baslik: str) -> tuple[str, list[dict]]:
    d = al(
        API,
        dict(
            action="query",
            titles=baslik,
            prop="extracts|images",
            explaintext=1,
            exsectionformat="plain",
            imlimit=50,
            format="json",
            formatversion=2,
            redirects=1,
        ),
    )["query"]["pages"][0]
    metin = d["extract"]
    dosyalar = [i["title"] for i in d.get("images", []) if not RED_AD.search(i["title"])]
    dosyalar = [f for f in dosyalar if f.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff"))]
    gorseller = []
    if dosyalar:
        time.sleep(1)
        ii = al(
            COMMONS,
            dict(
                action="query",
                titles="|".join(dosyalar[:20]),
                prop="imageinfo",
                iiprop="url|size|extmetadata|mime",
                iiurlwidth=1600,
                format="json",
                formatversion=2,
            ),
        )["query"]["pages"]
        for p in ii:
            if "imageinfo" not in p:
                continue
            i = p["imageinfo"][0]
            em = i.get("extmetadata", {})
            lisans = em.get("LicenseShortName", {}).get("value", "")
            if i["width"] < 500 or not UYGUN_LISANS.match(lisans):
                continue
            yazar = re.sub("<[^>]+>", "", em.get("Artist", {}).get("value", "")).strip()
            gorseller.append({"dosya": p["title"], "url": i["thumburl"], "lisans": lisans, "yazar": yazar[:80]})
    # makaledeki sıraya diz (images API alfabetik döner)
    return metin, gorseller


SEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "lines": {"type": "array", "items": {"type": "string"}, "minItems": 6, "maxItems": 9},
    },
    "required": ["title", "lines"],
}

ISTEM = """You write scripts for 35-second YouTube Shorts that tell one true, strange story.

Source (Wikipedia article "{baslik}"):
<<<
{metin}
>>>
Why editors call it unusual: {tanim}

Write 7 or 8 spoken lines (about 90 words total) that tell this as a STORY, not a list of facts:
- Line 1 is the hook: the single most surprising thing, in under 10 words, said as if mid-story.
  No question about "did you know".
- Then: who, where, when; what went wrong or what was strange; the turn; the payoff.
- The last line lands the punchline or the consequence, short and memorable.
- Plain spoken English, short sentences, past tense, concrete details (names, places, objects).
- Every fact, number, name and date MUST come from the source. Do not invent anything.
- No moralizing, no "Subscribe", no "Stay tuned", no emojis.
title: a curiosity title under 60 characters, no clickbait words like SHOCKING."""


def senaryo(baslik: str, metin: str, tanim: str, tohum: int = 1) -> dict:
    kisa = metin[:3500]
    return json_uret(ISTEM.format(baslik=baslik, metin=kisa, tanim=tanim), SEMA, sicaklik=0.7, tohum=tohum)


def kapi(satirlar: list[str], metin: str) -> list[str]:
    """Senaryodaki her sayı ve özel ad kaynakta geçmeli."""
    hata = []
    kaynak = metin.lower()
    for s in satirlar:
        for n in re.findall(r"\d[\d,.]*", s):
            if n.strip(".,").replace(",", "") not in kaynak.replace(",", ""):
                hata.append(f"sayı yok: {n} ({s})")
        for ad in re.findall(r"(?<![.!?]\s)(?<!^)\b[A-Z][a-z]{2,}\b", s):
            if ad.lower() not in kaynak:
                hata.append(f"ad yok: {ad} ({s})")
    return hata


def kapla(img: Image.Image, g: int, y: int) -> Image.Image:
    o = max(g / img.width, y / img.height)
    img = img.resize((round(img.width * o), round(img.height * o)), Image.LANCZOS)
    x0, y0 = (img.width - g) // 2, (img.height - y) // 2
    return img.crop((x0, y0, x0 + g, y0 + y))


def sahne_kareleri(img: Image.Image, n: int, yon: int):
    """Arka: bulanık-karartılmış kaplama; ön: genişliğe oturan görsel, yavaş zoom + kaydırma."""
    img = img.convert("RGB")
    arka = kapla(img, G, Y).filter(ImageFilter.GaussianBlur(40))
    arka = Image.blend(arka, Image.new("RGB", (G, Y), (8, 8, 12)), 0.55)
    on_g = int(G * 1.18)
    on = img.resize((on_g, round(img.height * on_g / img.width)), Image.LANCZOS)
    if on.height > Y * 0.62:  # dikey görsel: kaplama yeter
        on = kapla(img, int(G * 1.12), int(Y * 1.12))
    for k in range(n):
        t = k / max(n - 1, 1)
        z = 1.0 + 0.08 * t
        w, h = round(on.width * z), round(on.height * z)
        o = on.resize((w, h), Image.BILINEAR)
        kay = (w - G) * (t if yon > 0 else 1 - t)
        kare = arka.copy()
        yy = max((Y - h) // 2 - 150, 0) if h < Y else (Y - h) // 2
        kare.paste(o, (int(-kay), yy))
        yield kare


def yaz(kare: Image.Image, metin: str, font: ImageFont.FreeTypeFont) -> None:
    d = ImageDraw.Draw(kare)
    s = metin.upper()
    gen = d.textlength(s, font=font)
    d.text(((G - gen) / 2, Y * 0.70), s, font=font, fill="white", stroke_width=10, stroke_fill="black")


def video(baslik: str, tanim: str, cikti: Path, tohum: int) -> None:
    cikti.mkdir(parents=True, exist_ok=True)
    metin, gorseller = makale(baslik)
    print(f"metin {len(metin)} kr, uygun görsel {len(gorseller)}")
    for i in range(3):
        s = senaryo(baslik, metin, tanim, tohum + i)
        h = kapi(s["lines"], metin)
        print(f"deneme {i}: {s['title']} | kapı: {h or 'geçti'}")
        if not h:
            break
    satirlar = s["lines"]
    (cikti / "senaryo.json").write_text(
        json.dumps({**s, "kapi": h, "gorseller": gorseller}, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    sure, parcalar = seslendir(satirlar, satirlar, cikti / "ses.wav")
    alt = altyazi_parcalari(parcalar, kelime=3)
    resimler = []
    for g in gorseller[:8]:
        resimler.append(
            Image.open(BytesIO(urllib.request.urlopen(urllib.request.Request(g["url"], headers=UA)).read()))
        )
        time.sleep(0.5)
    if not resimler:
        sys.exit("görsel yok")
    font = ImageFont.truetype(str(FONT), 96)
    # her satır bir sahne; görseller döngüyle
    proc = subprocess.Popen(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-y",
            "-v",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{G}x{Y}",
            "-r",
            str(FPS),
            "-i",
            "-",
            "-i",
            str(cikti / "ses.wav"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "21",
            "-c:a",
            "aac",
            "-shortest",
            str(cikti / "video.mp4"),
        ],
        stdin=subprocess.PIPE,
    )
    kare_no = 0
    for i in range(len(parcalar)):
        son = parcalar[i + 1].bas if i + 1 < len(parcalar) else sure
        n = round(son * FPS) - kare_no
        for kare in sahne_kareleri(resimler[i % len(resimler)], n, 1 if i % 2 else -1):
            an = kare_no / FPS
            a = next((x for x in alt if x.bas <= an < x.son), None)
            if a:
                yaz(kare, a.metin, font)
            proc.stdin.write(kare.tobytes())
            kare_no += 1
    proc.stdin.close()
    proc.wait()
    print(f"{cikti / 'video.mp4'}  {sure:.1f} sn")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("komut", choices=["havuz", "video"])
    p.add_argument("baslik", nargs="?")
    p.add_argument("--cikti", type=Path)
    p.add_argument("--tohum", type=int, default=1)
    a = p.parse_args()
    if a.komut == "havuz":
        havuz()
    else:
        h = json.loads(Path("calisma/hikaye_havuz.json").read_text(encoding="utf-8"))
        tanim = next((x["tanim"] for x in h if x["baslik"] == a.baslik), "")
        video(a.baslik, tanim, a.cikti or Path("spikes/out/hikaye") / re.sub(r"\W+", "_", a.baslik), a.tohum)
