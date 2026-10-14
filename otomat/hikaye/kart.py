"""Kart formatı (K-25, 2026-10-14): anlatıcısız, tek paragraf ekran yazısıyla 8 saniyelik hikâye.

Neden: Earth'ün sahneli anlatımı (TTS + 8 AI illüstrasyon, 30-35 sn) 3-81 izlenmede kaldı; izlenmelerin yalnız
%25-38'i ilk saniyeleri geçti. Aynı nişte tutarlı izlenen küçük kanallar (Dark History, History Flash, Past Vault,
Mechanism Hub: son 50 videonun medyanı 23-39 bin; 10-14 rakip taraması, docs/arastirma/10) hikâyeyi tek ekranda
veriyor: üstte kısa kanca, altında 40-55 kelimelik paragraf (anahtar sözler renkli), altında konunun gerçek görseli,
5-8 sn, müzik. Paragraf bir okumada bitmez, izleyici videoyu döndürür.

Akış: kaynak metin → kart metni (gpt-oss) + kod kapısı + olgu hakemi, en çok 4 tur onarım → görsel (makalenin
Wikimedia Commons ana görseli: serbest lisans, yazı ağırlıklı değil; yoksa kanal stiliyle tek AI illüstrasyonu) →
render (dönen kare: zoom başa döner) → müzik → meta.json (cumleler = kart cümleleri, altyazı yok).
"""

import datetime as dt
import html
import json
import math
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from otomat import kanal
from otomat.ayarlar import KOK
from otomat.hikaye import cf, kaynaklar, panel, senaryo, yazi
from otomat.veri import OlguPaketi

G, Y, FPS = 1080, 1920, 30
SURE = 8.0
KELIME = (38, 58)  # paragraf; istem 40-55 der
CUMLE = (3, 6)
VURGU_SAYISI = (2, 6)
VURGU_KELIME = 6
KANCA_KELIME = (2, 7)
SAYI_SINIRI = 4
YIL = re.compile(r"1[0-9]{3}|20[0-9]{2}")
FONT = KOK / "otomat" / "varliklar" / "fontlar"
ZEMIN = (12, 12, 14)
RENKLER = ("#FFD84D", "#FF8A3D", "#7FE07A")  # vurgular sırayla
KENAR = 64
METIN_UST = 250  # üstteki ~200 px Shorts arayüzünün (arama, menü) altında kalır
GORSEL_ALT = 1500  # altındaki ~420 px başlık, kanal adı ve düğmelerin altında kalır
METIN_ALT = 980  # paragraf bundan aşağı inmez: görsele en az ~520 px kalır
SAHNE = "sahne_0.jpg"  # yarım üretim ve artifact düzeni sahne dosyası adını bekliyor
VURGU = re.compile(r"\[\[(.+?)\]\]")
LISANS = re.compile(r"^(?:public domain|pd\b|pd-|cc0|cc[ -]by(?:-sa)?\b|no restrictions|attribution\b)", re.I)
BELGE_HARF = 40  # OCR'da bu kadar Latin harf: görsel belge ya da yazı sayfası (Tarrare'nin ana görseli), AI'a düşer
UA = kaynaklar.UA
COMMONS = "https://commons.wikimedia.org/w/api.php"

ISTEM = """You write the on-screen text for an 8-second YouTube Short about ONE true, strange story. There is no
narrator: the viewer reads your text over a picture. It must hook in the first three words and pay off at the end,
so the viewer reads it to the last word (and watches again to finish it).

Source (Wikipedia article "{baslik}"):
<<<
{metin}
>>>
Why Wikipedia editors list it as unusual: {konu}

Write:
- hook: a 2-6 word headline that names the strange thing (e.g. "The town that couldn't stop dancing"). No "did you
  know", no question.
- sentences: 3-5 sentences, 40-55 words in total. First sentence: {kalip} The middle sentences tell what happened,
  each one stranger than the last. The last sentence is the absurd consequence or twist, short.
- Mark the 3-5 most striking phrases (the key number, the strangest fact, the outcome) with [[double brackets]],
  each 1-5 words. Never bracket a whole sentence.
- title: a curiosity title under 60 characters that only uses facts from the source; no clickbait words.
- image: one sentence describing ONE picture of the story for an illustrator who knows nothing about it (who, doing
  what, where, era); used only if the article has no photo. Nothing that carries writing (no signs, papers, maps).
- mood: the music mood that fits.
Rules:
- Plain, vivid English, past tense. No questions to the viewer, no "subscribe", no moralizing, no emojis.
- EVERY fact, number, name, date and cause must be stated in the source. If the source is unsure, say "reportedly".
  Do not merge different events. Use at most three numbers; write a number as digits only if the source does."""

ONARIM = """SOURCE:
<<<
{metin}
>>>
The text of a short video card was checked. Line 0 = title, line 1 = headline, the other lines are the card's
sentences:
{satirlar}

PROBLEMS:
{sorun}

Rewrite ONLY the flagged lines so every problem is fixed; if unsure, say less. Use only what the source states: add no
new detail, purpose, cause or number. Keep the [[double bracket]] marks on the most striking phrases (1-5 words each).
The headline stays 2-6 words, each sentence under 22 words. Return the fixed lines."""

ONARIM_SEMA = {
    "type": "object",
    "properties": {
        "fixes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"line": {"type": "integer"}, "text": {"type": "string"}},
                "required": ["line", "text"],
            },
        }
    },
    "required": ["fixes"],
}


def sema(moodlar: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "hook": {"type": "string"},
            "sentences": {"type": "array", "items": {"type": "string"}},
            "image": {"type": "string"},
            "mood": {"type": "string", "enum": moodlar},
        },
        "required": ["title", "hook", "sentences", "image", "mood"],
    }


@dataclass
class Kart:
    baslik: str
    kanca: str
    cumleler: list[str]  # [[vurgu]] işaretli
    gorsel_tarifi: str
    mood: str
    turlar: list[list] = field(default_factory=list)


def duz(metin: str) -> str:
    """Vurgu işaretleri olmadan metin (hakem, kapılar, açıklama ve çeviri bunu görür)."""
    return VURGU.sub(r"\1", metin).replace("[[", "").replace("]]", "")


def kod_kontrolu(k: Kart, kaynak: str) -> list[tuple[int, str]]:
    """Satır 0 başlık, 1 kanca, 2.. cümleler (hakemle aynı numaralar)."""
    sorun = []
    if not senaryo.BASLIK_UZUNLUK[0] <= len(k.baslik.strip()) <= senaryo.BASLIK_UZUNLUK[1]:
        sorun.append((0, f"the title must be {senaryo.BASLIK_UZUNLUK[0]}-{senaryo.BASLIK_UZUNLUK[1]} characters"))
    if not KANCA_KELIME[0] <= len(k.kanca.split()) <= KANCA_KELIME[1]:
        sorun.append((1, f"the headline must be {KANCA_KELIME[0]}-{KANCA_KELIME[1] - 1} words"))
    satirlar = [k.baslik, k.kanca, *k.cumleler]
    for i, s in enumerate(satirlar):
        if bulunan := kaynaklar.HAKARET.findall(s):
            sorun.append((i, f"remove the slur or profanity: {', '.join(bulunan)}"))
        sorun += [(i, h) for h in senaryo.sayi_ad_kapisi(duz(s), kaynak, adlar=i > 1)]
    for i, s in enumerate(k.cumleler, 2):
        if s.count("[[") != s.count("]]"):
            sorun.append((i, "unbalanced [[ ]] marks"))
        for v in VURGU.findall(s):
            if len(v.split()) > VURGU_KELIME:
                sorun.append((i, f"the marked phrase is too long ({len(v.split())} words); mark 1-5 words"))
    # yıl sayılmaz: kartta tarih kancanın parçası ("On January 15, 1919, ..."); yığılan ölçüler okunmuyor
    sayilar = [
        n for n in re.findall(r"\d[\d,.]*", " ".join(duz(s) for s in k.cumleler)) if not YIL.fullmatch(n.strip(".,"))
    ]
    if len(sayilar) > SAYI_SINIRI:
        sorun.append((len(satirlar) - 1, f"the card has {len(sayilar)} numbers; keep at most 3"))
    vurgular = sum(len(VURGU.findall(s)) for s in k.cumleler)
    if not VURGU_SAYISI[0] <= vurgular <= VURGU_SAYISI[1]:
        sorun.append((2, f"mark 3-5 striking phrases with [[ ]] across the sentences (now {vurgular})"))
    toplam = sum(len(duz(s).split()) for s in k.cumleler)
    if not CUMLE[0] <= len(k.cumleler) <= CUMLE[1]:
        sorun.append((2, f"write {CUMLE[0]}-{CUMLE[1] - 1} sentences (now {len(k.cumleler)})"))
    if not KELIME[0] <= toplam <= KELIME[1]:
        sorun.append((len(satirlar) - 1, f"the card has {toplam} words; it must be 40-55"))
    return sorun


def _hakem(kisa: str, k: Kart, kalip: str) -> list[tuple[int, str]]:
    satirlar = [duz(k.kanca), *map(duz, k.cumleler)]
    acilis = f"line 1 is a short headline; line 2 follows this instruction: {senaryo.KALIPLAR[kalip]}"
    istem = senaryo.HAKEM_ISTEM["tuhaf"].format(
        metin=kisa, baslik=k.baslik, satirlar=senaryo._numarali(satirlar), acilis=acilis
    )
    h = cf.sohbet(istem, senaryo.SORUN_SEMA)
    return [(p["line"], p["reason"]) for p in h["problems"] if 0 <= p["line"] <= len(satirlar)]


def yaz(baslik: str, kaynak: str, konu: str, kalip: str, moodlar: list[str]) -> Kart:
    """Senaryo motorunun kart karşılığı: yalnız işaretlenen satırlar onarılır (S11 dersi); TUR_SAYISI turda
    temizlenmezse SenaryoHatasi (gunluk sıradaki hikâyeyi dener)."""
    kisa = senaryo.kisalt(kaynak)
    istem = ISTEM.format(baslik=baslik, metin=kisa, konu=konu, kalip=senaryo.KALIPLAR[kalip])
    s = cf.sohbet(istem, sema(moodlar))
    k = Kart(s["title"].strip(), s["hook"].strip(), [c.strip() for c in s["sentences"] if c.strip()],
             s["image"].strip(), s["mood"])  # fmt: skip
    for tur_no in range(senaryo.TUR_SAYISI):
        sorun = kod_kontrolu(k, kaynak)
        if not sorun:  # kod kapısı temizse hakem; kapı sorunluyken hakem çağrısı boşa kota
            sorun = _hakem(kisa, k, kalip)
        k.turlar.append([[n, r[:300]] for n, r in sorun])
        if not sorun:
            return k
        if tur_no == senaryo.TUR_SAYISI - 1:
            break
        satirlar = [k.baslik, k.kanca, *k.cumleler]
        f = cf.sohbet(
            ONARIM.format(
                metin=kisa,
                satirlar="\n".join(f"{i}. {s}" for i, s in enumerate(satirlar)),
                sorun="\n".join(f"line {n}: {r}" for n, r in sorun),
            ),
            ONARIM_SEMA,
        )
        for d in f["fixes"]:
            if d["line"] == 0:
                k.baslik = d["text"].strip()
            elif d["line"] == 1:
                k.kanca = d["text"].strip()
            elif 2 <= d["line"] < len(satirlar):
                k.cumleler[d["line"] - 2] = d["text"].strip()
    raise senaryo.SenaryoHatasi(f"kart {senaryo.TUR_SAYISI} turda hakemden geçmedi", k.turlar)


# --- görsel ---


def _api(url: str, params: dict) -> dict:
    q = urllib.parse.urlencode({**params, "format": "json", "formatversion": 2})
    for bekle in (5, 20, 0):
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{url}?{q}", headers=UA), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503) or not bekle:
                raise
            time.sleep(bekle)
    raise AssertionError


def _yazar(em: dict) -> str:
    """Commons'ın HTML yazar alanı düz metne. "Unknown author" şablonu gizli etiketle iki kez geliyordu ("Unknown
    authorUnknown author"): bilinmeyen yazar boş döner (atıf satırı lisansla kalır)."""
    ham = em.get("Artist", {}).get("value") or ""
    yazar = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", ham))).strip()
    if not yazar or re.match(r"(?i)(unknown|anonymous|unbekannt)\b", yazar):
        return ""
    return yazar[:60] + ("…" if len(yazar) > 60 else "")


def wiki_gorseli(baslik: str) -> dict | None:
    """Makalenin ana görseli kullanılabiliyorsa {url, sayfa, lisans, yazar}; değilse None. Kullanılabilir: serbest
    lisans (kamu malı, CC0, CC BY, CC BY-SA), raster, en kısa kenar ≥ 400 px, en-boy 0,35-2,5."""
    p = _api(kaynaklar.WIKI_API, {"action": "query", "titles": baslik, "prop": "pageimages", "piprop": "name",
                                  "redirects": 1})["query"]["pages"][0]  # fmt: skip
    if not (dosya := p.get("pageimage")):
        return None
    d = _api(COMMONS, {"action": "query", "titles": f"File:{dosya}", "prop": "imageinfo",
                       "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1280})["query"]["pages"][0]  # fmt: skip
    ii = (d.get("imageinfo") or [None])[0]
    if not ii:
        return None
    em = ii.get("extmetadata", {})
    lisans = (em.get("LicenseShortName", {}).get("value") or "").strip()
    w, h = ii.get("width", 0), ii.get("height", 0)
    if (
        em.get("NonFree", {}).get("value")
        or not LISANS.match(lisans)
        or ii.get("mime") not in ("image/jpeg", "image/png")
        or min(w, h) < 400
        or not 0.35 <= w / max(h, 1) <= 2.5
    ):
        return None
    return {"url": ii.get("thumburl") or ii["url"], "sayfa": ii.get("descriptionurl", ""), "lisans": lisans,
            "yazar": _yazar(em), "dosya": dosya}  # fmt: skip


def _indir(url: str, yol: Path) -> None:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        veri = r.read()
    gecici = yol.with_suffix(".tmp")
    gecici.write_bytes(veri)
    Image.open(gecici).convert("RGB").save(yol, quality=92)  # bozuk dosya burada düşer
    gecici.unlink()


def belge_mi(yol: Path) -> bool:
    """Görselde OCR'ın okuduğu Latin harf sayısı BELGE_HARF'ı aşıyor mu (OCR kurulu değilse hayır)."""
    okunan = yazi.oku(yol) or []
    return sum(len(re.findall(r"[A-Za-z]", m)) for m in okunan) >= BELGE_HARF


def gorsel_al(paket: OlguPaketi, k: Kart, dizin: Path, tohum: int) -> dict:
    """Önce makalenin kendi görseli (gerçek fotoğraf/gravür: rakip kanalların hepsi gerçek görüntü kullanıyor), sonra
    kanal stiliyle tek AI illüstrasyonu. Panel ya da yazı çıkan AI karesi bir kez yeniden çizilir."""
    yol = dizin / SAHNE
    try:
        w = wiki_gorseli(paket.gorsel["baslik"])
    except (OSError, ValueError, KeyError) as e:
        w, hata = None, str(e)[:120]
    else:
        hata = None
    if w:
        try:
            _indir(w["url"], yol)
        except (OSError, ValueError) as e:
            hata = f"indirilemedi: {str(e)[:120]}"
        else:
            if not belge_mi(yol):
                return {"kaynak": "wikimedia", **w}
            hata = "yazı ağırlıklı (belge)"
            yol.unlink()
    k_ = kanal.aktif()
    istem = f"{k_.stil}. A single full-frame scene, not a comic, no panels. {k.gorsel_tarifi} {uretim_yazisiz()}"
    cf.gorsel(istem, yol, tohum)
    yeniden = 0
    if panel.panelli(yol) or (yazi.oku(yol) or []):
        yeniden = 1
        yol.unlink()
        cf.gorsel(istem, yol, tohum + 7)
    return {"kaynak": "ai", "model": cf.GORSEL_MODELI, "wiki": hata or "görsel yok", "yeniden": yeniden}


def uretim_yazisiz() -> str:
    from otomat.hikaye.uretim import TEK_KARE, YAZISIZ

    return f"{TEK_KARE} {YAZISIZ}"


# --- render ---


@lru_cache(maxsize=32)
def _font(ad: str, boy: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT / ad), boy)


def kelimeler(cumleler: list[str]) -> list[tuple[str, int]]:
    """[[vurgu]] işaretli cümleler → (kelime, renk no; -1 düz). Vurgudan sonra gelen noktalama önceki kelimeye
    yapışır ("died ." değil "died.")."""
    sonuc: list[tuple[str, int]] = []
    vno = 0
    for parca in re.split(r"(\[\[.+?\]\])", " ".join(cumleler)):
        if parca.startswith("[["):
            sonuc += [(w, vno % len(RENKLER)) for w in parca[2:-2].split()]
            vno += 1
            continue
        for w in parca.split():
            if sonuc and re.fullmatch(r"[.,;:!?)’'\"”]+", w):
                onceki, r = sonuc[-1]
                sonuc[-1] = (onceki + w, r)
            else:
                sonuc.append((w, -1))
    return sonuc


def satirla(kel: list[tuple[str, int]], f: ImageFont.FreeTypeFont, genislik: int) -> list[list[tuple[str, int]]]:
    satirlar, satir = [], []
    for k in kel:
        if satir and f.getlength(" ".join(w for w, _ in [*satir, k])) > genislik:
            satirlar.append(satir)
            satir = []
        satir.append(k)
    return [*satirlar, satir] if satir else satirlar


def ust_katman(kanca: str, cumleler: list[str], kanal_adi: str) -> tuple[Image.Image, int]:
    """Sabit katman (kanal adı, kanca, paragraf) ve paragrafın bittiği y. Kanca en çok iki satır; paragraf METIN_ALT'a
    sığana kadar küçülür."""
    kat = Image.new("RGBA", (G, Y), (0, 0, 0, 0))
    d = ImageDraw.Draw(kat)
    d.text((G / 2, METIN_UST - 70), kanal_adi.upper(), font=_font("Barlow-Medium.ttf", 34), fill=(170, 170, 170),
           anchor="mm")  # fmt: skip
    y = METIN_UST
    for boy in (92, 84, 76, 68):
        fh = _font("BarlowCondensed-Bold.ttf", boy)
        kanca_satir = satirla([(w, 0) for w in kanca.upper().split()], fh, G - 2 * KENAR)
        if len(kanca_satir) <= 2:
            break
    for satir in kanca_satir:
        d.text((G / 2, y), " ".join(w for w, _ in satir), font=fh, fill=RENKLER[0], anchor="mt", stroke_width=2,
               stroke_fill="black")  # fmt: skip
        y += int(boy * 1.05)
    y += 30
    kel = kelimeler(cumleler)
    for boy in (56, 52, 48, 44, 40):
        fp = _font("Barlow-Medium.ttf", boy)
        satirlar = satirla(kel, fp, G - 2 * KENAR)
        if y + len(satirlar) * boy * 1.22 <= METIN_ALT:
            break
    bosluk = fp.getlength(" ")
    for satir in satirlar:
        x = (G - fp.getlength(" ".join(w for w, _ in satir))) / 2
        for w, r in satir:
            d.text((x, y), w, font=fp, fill=RENKLER[r] if r >= 0 else "white", stroke_width=2, stroke_fill="black")
            x += fp.getlength(w) + bosluk
        y += int(boy * 1.22)
    return kat, y


def kareler(gorsel: Path, kanca: str, cumleler: list[str], atif: str, kanal_adi: str, sure: float = SURE):
    """Görsel yavaşça yaklaşıp başa döner (cos): Shorts döngüye girdiğinde kare sıçramaz."""
    kat, metin_alt = ust_katman(kanca, cumleler, kanal_adi)
    ust = metin_alt + 36
    alan = (G, GORSEL_ALT - ust)
    img = Image.open(gorsel).convert("RGB")
    olcek = max(alan[0] / img.width, alan[1] / img.height) * 1.08
    buyuk = img.resize((round(img.width * olcek), round(img.height * olcek)), Image.LANCZOS)
    gecis = Image.linear_gradient("L").resize((G, 60))
    zemin_seridi = Image.new("RGB", (G, 60), ZEMIN)
    taban = Image.new("RGB", (G, Y), ZEMIN)
    ImageDraw.Draw(taban).text((G - KENAR, GORSEL_ALT + 32), atif, font=_font("Barlow-Regular.ttf", 24),
                               fill=(140, 140, 140), anchor="rs")  # fmt: skip
    n = round(sure * FPS)
    for i in range(n):
        s = 1.04 + 0.04 * math.cos(2 * math.pi * i / n)  # 1,08 → 1,00 → 1,08
        w, h = alan[0] * 1.08 / s, alan[1] * 1.08 / s
        cx = buyuk.width / 2
        cy = min(max(h / 2, buyuk.height * 0.45), buyuk.height - h / 2)  # uzun görselde üst-orta (yüzler)
        parca = buyuk.crop((round(cx - w / 2), round(cy - h / 2), round(cx + w / 2), round(cy + h / 2)))
        kare = taban.copy()
        kare.paste(parca.resize(alan, Image.BILINEAR), (0, ust))
        kare.paste(zemin_seridi, (0, ust), Image.eval(gecis, lambda p: 255 - p))
        kare.paste(zemin_seridi, (0, GORSEL_ALT - 60), gecis)
        kare.paste(kat, (0, 0), kat)
        yield kare


def render(gorsel: Path, kanca: str, cumleler: list[str], atif: str, cikti: Path, sure: float = SURE) -> Path:
    p = subprocess.Popen(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
         f"{G}x{Y}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(cikti)],
        stdin=subprocess.PIPE,
    )  # fmt: skip
    try:
        for k in kareler(gorsel, kanca, cumleler, atif, kanal.aktif().ad, sure):
            p.stdin.write(np.asarray(k).tobytes())
    finally:
        p.stdin.close()
        p.wait()
    if p.returncode:
        raise RuntimeError(f"kart render'ı düştü (ffmpeg {p.returncode})")
    return cikti


MUZIK_LUFS = -16.0  # anlatıcı yok: müzik tek ses; YouTube'un hedefine yakın


def muzikle(sessiz: Path, muzik: Path, cikti: Path, sure: float = SURE) -> Path:
    subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-v", "error", "-i", str(sessiz), "-stream_loop", "-1", "-i",
         str(muzik), "-filter_complex",
         f"[1:a]atrim=0:{sure + 1:.2f},loudnorm=I={MUZIK_LUFS}:TP=-2:LRA=11,afade=t=in:d=0.2,"
         f"afade=t=out:st={sure - 0.5:.2f}:d=0.5,aresample=48000[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", f"{sure:.2f}", str(cikti)],
        check=True,
    )  # fmt: skip
    return cikti


# --- meta ---


def atif_satiri(g: dict) -> str:
    """Görselin altındaki satır (CC BY/BY-SA atfı videoda da durur)."""
    if g["kaynak"] != "wikimedia":
        return "Illustration: AI"
    return f"Image: {g['yazar'] + ' · ' if g['yazar'] else ''}{g['lisans']} · Wikimedia Commons"


def aciklama(paket: OlguPaketi, k: Kart, g: dict, muzik_adi: str) -> str:
    from otomat.hikaye.uretim import MUZIK_ATIF

    etiket = " ".join(dict.fromkeys("#" + "".join(w[:1].upper() + w[1:] for w in e.split()) for e in paket.etiketler))
    ad = paket.gorsel["baslik"]
    if g["kaynak"] == "wikimedia":
        gorsel = f"Image: {g['yazar'] or 'see file page'}, {g['lisans']}, via Wikimedia Commons {g['sayfa']}"
    else:
        gorsel = "Illustration made with AI."
    return (
        f"{' '.join(duz(c) for c in k.cumleler)}\n\n"
        f'Source: Wikipedia, "{ad}" ({paket.kaynak.lisans}) {paket.kaynak.url}\n{gorsel}\n'
        f"Music: {MUZIK_ATIF.format(muzik_adi)}\nhttps://creativecommons.org/licenses/by/4.0/\n\n{etiket}"
    )


def uret(paket: OlguPaketi, kalip: str, sablon: str, dizin: Path, tohum: str) -> dict:
    from otomat.hikaye.uretim import muzik_sec

    k_ = kanal.aktif()
    dizin.mkdir(parents=True, exist_ok=True)
    for eski in [*dizin.glob("sahne_*"), *dizin.glob("*.srt"), dizin / "video.mp4", dizin / "meta.json"]:
        eski.unlink(missing_ok=True)  # aynı slotta önceki denemenin çıktısı karışmasın
    cf.NEURON["toplam"] = 0.0
    t0 = time.time()
    k = yaz(paket.gorsel["baslik"], kaynaklar.metin(paket), paket.konu, kalip, list(k_.muzik))
    t_metin = time.time()
    g = gorsel_al(paket, k, dizin, sum(map(ord, paket.anahtar)) % 100_000)
    t_gorsel = time.time()
    sessiz = render(dizin / SAHNE, duz(k.kanca), k.cumleler, atif_satiri(g), dizin / "sessiz.mp4")
    muzik, muzik_adi = muzik_sec(k.mood, tohum + paket.anahtar)
    video = muzikle(sessiz, muzik, dizin / "video.mp4")
    sessiz.unlink()
    meta = {
        "bicim": "kart",
        "baslik": k.baslik,
        "aciklama": aciklama(paket, k, g, muzik_adi),
        "etiketler": paket.etiketler,
        "mfk": k_.mfk,
        "paket": {"anahtar": paket.anahtar, "hash": paket.hash, "kol": paket.kol, "tur": paket.tur},
        "secim": {
            "kalip": kalip,
            "sablon": sablon,
            "kaynak": {"senaryo": cf.METIN_MODELI, "gorsel": g.get("model", "wikimedia")},
        },  # fmt: skip
        "kanca": duz(k.kanca),
        "cumleler": [duz(c) for c in k.cumleler],
        "kart": {"kanca": k.kanca, "cumleler": k.cumleler, "gorsel": g, "gorsel_tarifi": k.gorsel_tarifi},
        "senaryo": {"mood": k.mood, "hakem_turlari": k.turlar},
        "muzik": muzik_adi,
        "altyazi": [],
        "sure_sn": SURE,
        "neuron": round(cf.NEURON["toplam"]),
        "zaman_sn": {
            "senaryo": round(t_metin - t0, 1),
            "gorsel": round(t_gorsel - t_metin, 1),
            "ses_render": round(time.time() - t_gorsel, 1),
        },  # fmt: skip
        "uretildi": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "video": str(video.relative_to(KOK)) if video.is_relative_to(KOK) else str(video),
    }
    (dizin / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    (dizin / "kart.json").write_text(json.dumps(asdict(k), ensure_ascii=False, indent=1), encoding="utf-8")
    return meta
