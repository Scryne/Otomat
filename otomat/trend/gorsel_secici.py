"""Görsel havuzu süzgeci: konuyla ilgisiz görselleri senaryo yazılmadan önce atar.

Neden görüntüye bakılır: 11-26 Riemann havuzunda yalnız başlığa bakan süzgeç "University of Gottingen Library" dosyasını
tuttu; fotoğraf İkinci Dünya Savaşı'nda yıkılmış kütüphanenin kalıntısıydı ve "Endorsed within a day" başlığının
arkasında göründü. Başlık masum, içerik alakasız. Görsel eleştirmenin modeli (gemini-4-argon, OpenCode Go) görüntü
okuyor: görseller numaralı kontak sayfalarına dizilir, model başlıkla birlikte görüntüyü de görüp karar verir. Model
düşerse başlıkla süzme (glm-5.3) yedektir.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from otomat.trend.llm import Oturum, json_cikar

MODEL_GORUNTU = "gemini-4-argon"
MODEL_METIN = "glm-5.3"
HUCRE = (384, 256)
SUTUN, SATIR = 4, 4  # sayfa başına 16 görsel, 1536×1024 (görüntü modelinin rahat okuduğu boy)

SISTEM = """You are the picture researcher of a documentary explainer. You get the STORY, a list of freely licensed
images (id: file title) and contact sheets where every image is labelled with its id. Look at each IMAGE itself, not
only its title. Keep an image only if it could honestly illustrate a moment of THIS story: its named people, the places
where it happens, its objects, documents, events, or its subject shown directly (a diagram of the actual thing).
Drop: portraits of anyone who is not named in the story (the wrong person on screen), places that only share a city or
institution with the story, anything from an unrelated era or event (war ruins, an old book scan, a medal), images
where the subject is unrecognisable or tiny, and text-heavy scans that cannot be read on screen. When unsure, drop.
Then, among the images you keep, list GROUPS of images that show the same subject in a similar way (the same building
from outside, the same person at the same event, the same chart): a viewer would see them as the same shot repeated.
Order each group best first (sharpest, most telling). Images with no near-twin are not listed.
Return ONLY JSON: {"tut": ["G1", ...], "gruplar": [["G3", "G7", "G9"], ...]}"""
GRUP_EN_COK = 3  # aynı konudan en çok üç görsel (11-26 Miss Universe: kolezyumun 7 fotoğrafı ~15 sahnede; 2'de havuz
#                 8 görsele inip sahneler görselsiz kaldı)


def _yazi_tipi(boy: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for yol in ("C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(yol, boy)
        except OSError:
            continue
    return ImageFont.load_default(size=boy)


def kontak_sayfalari(yollar: list[Path]) -> list[bytes]:
    """Görselleri G1, G2… etiketli JPEG kontak sayfalarına dizer (sayfa başına SUTUN×SATIR)."""
    w, h = HUCRE
    yazi = _yazi_tipi(30)
    sayfalar = []
    adim = SUTUN * SATIR
    for bas in range(0, len(yollar), adim):
        sayfa = Image.new("RGB", (w * SUTUN, h * SATIR), (24, 24, 26))
        cizim = ImageDraw.Draw(sayfa)
        for j, yol in enumerate(yollar[bas : bas + adim]):
            x, y = (j % SUTUN) * w, (j // SUTUN) * h
            try:
                with Image.open(yol) as im:
                    kucuk = ImageOps.exif_transpose(im).convert("RGB")
                    kucuk.thumbnail((w - 8, h - 8))
                sayfa.paste(kucuk, (x + (w - kucuk.width) // 2, y + (h - kucuk.height) // 2))
            except OSError:
                pass
            etiket = f"G{bas + j + 1}"
            cizim.rectangle((x + 4, y + 4, x + 18 + 20 * len(etiket), y + 42), fill=(255, 214, 10))
            cizim.text((x + 10, y + 6), etiket, fill=(17, 17, 17), font=yazi)
        tampon = io.BytesIO()
        sayfa.save(tampon, "JPEG", quality=82)
        sayfalar.append(tampon.getvalue())
    return sayfalar


def _kimlikler(y: object, n: int) -> set[int]:
    tut = (y.get("tut") or []) if isinstance(y, dict) else []
    return {int(str(k)[1:]) - 1 for k in tut if str(k)[1:].isdigit() and 0 < int(str(k)[1:]) <= n}


def gruplari_kirp(y: object, tut: set[int], n: int, en_cok: int = GRUP_EN_COK) -> set[int]:
    """Aynı konuyu gösteren grupta ilk `en_cok` görsel kalır (model en iyisini başa koyar). Farklı dosya ama aynı
    görüntü (aynı binanın yedi dış çekimi) dosya başına tekrar sınırına takılmıyor, izleyici aynı kareyi görüyordu."""
    gruplar = (y.get("gruplar") or []) if isinstance(y, dict) else []
    kalan = set(tut)
    for g in gruplar if isinstance(gruplar, list) else []:
        if not isinstance(g, list):
            continue
        ids = [int(str(k)[1:]) - 1 for k in g if str(k)[1:].isdigit() and 0 < int(str(k)[1:]) <= n]
        ids = [i for i in ids if i in kalan]
        for i in ids[en_cok:]:
            kalan.discard(i)
    return kalan


def goruntuyle_sec(oturum: Oturum, hikaye: str, liste: str, yollar: list[Path]) -> set[int]:
    """Görüntü modeline kontak sayfaları + başlık listesi; tutulacak görsellerin sıra numaraları (0 tabanlı)."""
    icerik: list[dict] = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                       "data": base64.b64encode(s).decode()}}
                          for s in kontak_sayfalari(yollar)]  # fmt: skip
    icerik.append({"type": "text", "text": f"STORY: {hikaye}\n\nIMAGES (id: file title):\n{liste}"})
    govde = {"model": MODEL_GORUNTU, "max_tokens": 1500, "temperature": 0, "system": SISTEM,
             "messages": [{"role": "user", "content": icerik}]}  # fmt: skip
    y = oturum._istek(govde, toplam_sure=300)
    metin = "".join(c.get("text", "") for c in y.get("content", []) if c.get("type") == "text")
    cevap = json_cikar(metin)
    return gruplari_kirp(cevap, _kimlikler(cevap, len(yollar)), len(yollar))


def basliktan_sec(oturum: Oturum, hikaye: str, liste: str, n: int) -> set[int]:
    y = oturum.json_sor(SISTEM, f"STORY: {hikaye}\n\nIMAGES (id: file title; no contact sheets this time):\n{liste}",
                        model=MODEL_METIN, en_cok=1500, sicaklik=0.0, dusun=False)  # fmt: skip
    return gruplari_kirp(y, _kimlikler(y, n), n)
