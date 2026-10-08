"""Format spike'ı 2: S10 + Cloudflare Workers AI (gpt-oss-120b senaryo ve hakem, flux-2-klein-4b sahne görseli).

    uv run python spikes/s11_hikaye_cf.py "London Beer Flood" [--ses bm_george]

Sırlar: sirlar/cloudflare.json ya da CF_ACCOUNT_ID / CF_API_TOKEN.
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import wave
from io import BytesIO
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from s10_hikaye import kapi, makale  # noqa: E402

from otomat.ayarlar import KOK  # noqa: E402
from otomat.ses import Parca, _kokoro, altyazi_parcalari  # noqa: E402

G, Y, FPS = 1080, 1920, 30
FONT = KOK / "otomat/varliklar/fontlar/BarlowCondensed-Bold.ttf"
STIL = (
    "Hand-drawn storybook illustration, confident ink lines, muted watercolor, warm paper texture, "
    "cinematic composition, expressive faces, full-bleed edge-to-edge artwork with no border or frame, "
    "no text, no letters, no signs, no captions"
)
MUZIK = {  # Freesound CC0 (Openverse aramasıyla, 2026-10-08)
    "mysterious": ("Mystery And Thriller Music", "https://cdn.freesound.org/previews/418/418210_2316649-hq.mp3"),
    "tragic": ("Slow Cinematic Music", "https://cdn.freesound.org/previews/384/384202_2866779-hq.mp3"),
    "epic": ("Cinematic Dramatic Buildup", "https://cdn.freesound.org/previews/456/456102_7241289-hq.mp3"),
    "funny": ("Piano Remix", "https://cdn.freesound.org/previews/112/112071_682033-hq.mp3"),
}


def cf_kimlik() -> tuple[str, str]:
    if os.environ.get("CF_API_TOKEN"):
        return os.environ["CF_ACCOUNT_ID"], os.environ["CF_API_TOKEN"]
    d = json.loads((KOK / "sirlar/cloudflare.json").read_text(encoding="utf-8"))
    return d["account_id"], d["api_token"]


NEURON = {"toplam": 0.0}


def sohbet(istem: str, sema: dict, model: str = "@cf/openai/gpt-oss-120b") -> dict:
    hesap, belirtec = cf_kimlik()
    govde = {
        "model": model,
        "messages": [{"role": "user", "content": istem}],
        "response_format": {"type": "json_schema", "json_schema": {"name": "cikti", "schema": sema}},
        "max_tokens": 8000,
        "reasoning_effort": "medium",
    }
    istek = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/accounts/{hesap}/ai/v1/chat/completions",
        json.dumps(govde).encode(),
        {"Authorization": f"Bearer {belirtec}", "Content-Type": "application/json"},
    )
    y = json.load(urllib.request.urlopen(istek, timeout=180))
    NEURON["toplam"] += y.get("usage", {}).get("neurons", 0)
    c = y["choices"][0]
    if not c["message"].get("content"):
        raise RuntimeError(f"boş yanıt: {c.get('finish_reason')} {y.get('usage')}")
    return _duz(json.loads(c["message"]["content"]))


DUZ = {"‑": "-", "‐": "-", "–": "-", "—": " - ", "’": "'", "‘": "'", "“": '"', "”": '"', " ": " "}


def _duz(x):
    if isinstance(x, str):
        for a, b in DUZ.items():
            x = x.replace(a, b)
        return x
    if isinstance(x, list):
        return [_duz(v) for v in x]
    if isinstance(x, dict):
        return {k: _duz(v) for k, v in x.items()}
    return x


def gorsel(istem: str, yol: Path) -> Image.Image:
    if yol.exists():
        return Image.open(yol)
    hesap, belirtec = cf_kimlik()
    sinir = "----otomat"
    for deneme in range(4):
        alanlar = {"prompt": istem, "width": "768", "height": "1344", "seed": str(1000 + deneme)}
        parcalar = [
            f'--{sinir}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'
            for k, v in alanlar.items()
        ]
        govde = "".join(parcalar) + f"--{sinir}--\r\n"
        istek = urllib.request.Request(
            f"https://api.cloudflare.com/client/v4/accounts/{hesap}/ai/run/@cf/black-forest-labs/flux-2-klein-4b",
            govde.encode(),
            {"Authorization": f"Bearer {belirtec}", "Content-Type": f"multipart/form-data; boundary={sinir}"},
        )
        try:
            y = json.load(urllib.request.urlopen(istek, timeout=180))
            break
        except urllib.error.HTTPError as e:
            govde_hata = e.read()
            print(f"   görsel {e.code}: {govde_hata[:120]!r}")
            if deneme == 3:
                raise
            if b"3030" in govde_hata:  # güvenlik filtresi: sahneyi yumuşat, tohumu değiştir
                istem += ". Calm, gentle, non-graphic, nobody hurt."
            time.sleep(3)
    NEURON["toplam"] += 6 * 26.05  # 768x1344 = 6 karo
    yol.write_bytes(base64.b64decode(y["result"]["image"]))
    return Image.open(yol)


SEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "mood": {"type": "string", "enum": list(MUZIK)},
        "world": {"type": "string"},
        "cast": {"type": "array", "items": {"type": "string"}},
        "scenes": {
            "type": "array",
            "minItems": 7,
            "maxItems": 8,
            "items": {
                "type": "object",
                "properties": {"line": {"type": "string"}, "image": {"type": "string"}},
                "required": ["line", "image"],
            },
        },
    },
    "required": ["title", "mood", "world", "cast", "scenes"],
}

ISTEM = """You write scripts for 35-second YouTube Shorts that tell ONE true, strange story from history.
Viewers swipe away in one second unless the first line grabs them, so the story must pull them to the end.

Source (Wikipedia article "{baslik}"):
<<<
{metin}
>>>
Why Wikipedia editors list it as unusual: {tanim}

Write 7-8 scenes, 75-90 words in total. Each scene = one spoken line (5-12 words) + one illustration.
Story shape:
1. Hook: the most surprising concrete image of the story, stated plainly, as if already happening.
2-3. Who, where, when, in vivid concrete detail.
4-6. What went wrong / what was strange, building tension; the turn.
Last: the payoff or the absurd consequence, short and memorable, so the viewer wants to watch again.
Rules:
- Spoken, plain English. Past tense. No "did you know", no questions to the viewer, no "subscribe", no moralizing.
- EVERY fact, number, name, date and cause must be stated in the source. If the source is unsure, say "reportedly".
  Do not merge different events. Do not round numbers differently from the source.
- Write numbers as digits only if they appear as digits in the source.
title: a curiosity title under 60 characters, no clickbait words (SHOCKING, INSANE).
mood: the music mood that fits the story.
world: one sentence describing era, place, clothing and palette for the illustrator (consistent across scenes).
cast: 0-3 recurring characters, each a fixed visual description (age, clothes, hair) reused verbatim in image prompts.
image: a concrete visual description of that scene for an illustrator (who, doing what, where, camera angle).
  No text, signs or letters in the image. Never show dead bodies, injuries or blood; show the moment before
  or the aftermath through objects and reactions. Copy cast descriptions verbatim when a character appears.{geri}"""

HAKEM = {
    "type": "object",
    "properties": {
        "problems": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"line": {"type": "integer"}, "reason": {"type": "string"}},
                "required": ["line", "reason"],
            },
        }
    },
    "required": ["problems"],
}

HAKEM_ISTEM = """You are a strict fact checker. SOURCE (the only truth):
<<<
{metin}
>>>
SCRIPT LINES:
{satirlar}

For each line, check every claim (numbers, names, dates, places, causes, sequence, who did what) against the SOURCE.
Flag a line if it states something the source does not say, contradicts it, attaches a fact to the wrong person or
event, or exaggerates. Dramatic wording is fine when the facts underneath are correct. Return only real problems."""


ONARIM = {
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

ONARIM_ISTEM = """SOURCE:
<<<
{metin}
>>>
A script for a short story video has lines a fact checker rejected:
{satirlar}

PROBLEMS:
{sorun}

Rewrite ONLY the flagged lines so every claim is exactly what the source says (if unsure, say less). Keep each line
5-12 words, spoken, past tense, and keep the story flowing with the lines around it. Return the fixed lines."""


def denetle(satirlar: list[str], metin: str, kisa: str) -> list[tuple[int, str]]:
    sorun = [(i + 1, h) for i, s in enumerate(satirlar) for h in kapi([s], metin)]
    numarali = "\n".join(f"{i + 1}. {x}" for i, x in enumerate(satirlar))
    h = sohbet(HAKEM_ISTEM.format(metin=kisa, satirlar=numarali), HAKEM)
    sorun += [(p["line"], p["reason"]) for p in h["problems"]]
    return sorun


def senaryo(baslik: str, metin: str, tanim: str) -> tuple[dict, list]:
    kisa = metin[:6000]
    s = sohbet(ISTEM.format(baslik=baslik, metin=kisa, tanim=tanim, geri=""), SEMA)
    for tur in range(4):
        satirlar = [x["line"] for x in s["scenes"]]
        sorun = denetle(satirlar, metin, kisa)
        print(f"tur {tur}: {s['title']} | sorun {len(sorun)}")
        for n, x in sorun:
            print(f"    {n}: {x[:150]}")
        if not sorun:
            return s, []
        if tur == 3:
            break
        numarali = "\n".join(f"{i + 1}. {x}" for i, x in enumerate(satirlar))
        f = sohbet(
            ONARIM_ISTEM.format(metin=kisa, satirlar=numarali, sorun="\n".join(f"line {n}: {x}" for n, x in sorun)),
            ONARIM,
        )
        for d in f["fixes"]:
            if 1 <= d["line"] <= len(s["scenes"]):
                s["scenes"][d["line"] - 1]["line"] = d["text"]
    return s, sorun


def seslendir(satirlar: list[str], ses: str, cikti: Path) -> tuple[float, list[Parca]]:
    k = _kokoro()
    parcalar, sesler, an, sr = [], [], 0.0, 24000
    for i, s in enumerate(satirlar):
        ornek, sr = k.create(s, voice=ses, speed=1.08, lang="en-gb" if ses.startswith("b") else "en-us")
        sure = len(ornek) / sr
        parcalar.append(Parca(an, an + sure, s))
        ara = 0.3 if i < len(satirlar) - 1 else 1.2
        sesler += [ornek, np.zeros(int(ara * sr), dtype=np.float32)]
        an += sure + ara
    tum = np.concatenate(sesler)
    with wave.open(str(cikti), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(tum, -1, 1) * 32767).astype(np.int16).tobytes())
    return len(tum) / sr, parcalar


def kareler(img: Image.Image, n: int, yakinlas: bool):
    img = img.convert("RGB")
    o = max(G / img.width, Y / img.height) * 1.12
    buyuk = img.resize((round(img.width * o), round(img.height * o)), Image.LANCZOS)
    for k in range(n):
        t = k / max(n - 1, 1)
        t = t * t * (3 - 2 * t)
        z = 1.0 + 0.10 * (t if yakinlas else 1 - t)
        w, h = round(G * 1.12 / z), round(Y * 1.12 / z)
        x0, y0 = (buyuk.width - w) // 2, (buyuk.height - h) // 2
        yield buyuk.crop((x0, y0, x0 + w, y0 + h)).resize((G, Y), Image.BILINEAR)


def yaz(kare: Image.Image, metin: str, font: ImageFont.FreeTypeFont) -> None:
    d = ImageDraw.Draw(kare)
    s = metin.upper()
    gen = d.textlength(s, font=font)
    if gen > G - 80:
        font = ImageFont.truetype(str(FONT), int(font.size * (G - 80) / gen))
        gen = d.textlength(s, font=font)
    d.text(((G - gen) / 2, Y * 0.66), s, font=font, fill="white", stroke_width=11, stroke_fill="black")


def muzik(mood: str, dizin: Path) -> Path:
    yol = dizin.parent / f"muzik_{mood}.mp3"
    if not yol.exists():
        istek = urllib.request.Request(MUZIK[mood][1], headers={"User-Agent": "Otomat/0.1"})
        yol.write_bytes(urllib.request.urlopen(istek, timeout=60).read())
    return yol


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("baslik")
    p.add_argument("--ses", default="bm_george")
    a = p.parse_args()
    dizin = Path("spikes/out/hikaye_cf") / re.sub(r"\W+", "_", a.baslik)
    dizin.mkdir(parents=True, exist_ok=True)
    havuz = json.loads(Path("calisma/hikaye_havuz.json").read_text(encoding="utf-8"))
    tanim = next((x["tanim"] for x in havuz if x["baslik"] == a.baslik), "")
    t0 = time.time()
    metin, _ = makale(a.baslik)
    s, sorun = senaryo(a.baslik, metin, tanim)
    (dizin / "senaryo.json").write_text(json.dumps({**s, "sorun": sorun}, ensure_ascii=False, indent=1), "utf-8")
    t1 = time.time()
    resimler = []
    for i, sc in enumerate(s["scenes"]):
        istem = f"{STIL}. {s['world']} {sc['image']}"
        resimler.append(gorsel(istem[:2000], dizin / f"sahne_{i}.jpg"))
    t2 = time.time()
    satirlar = [x["line"] for x in s["scenes"]]
    sure, parcalar = seslendir(satirlar, a.ses, dizin / "ses.wav")
    alt = altyazi_parcalari(parcalar, kelime=3)
    font = ImageFont.truetype(str(FONT), 104)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    sessiz = dizin / "sessiz.mp4"
    proc = subprocess.Popen(
        [ff, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{G}x{Y}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(sessiz)],
        stdin=subprocess.PIPE,
    )  # fmt: skip
    kare_no = 0
    for i in range(len(parcalar)):
        son = parcalar[i + 1].bas if i + 1 < len(parcalar) else sure
        for kare in kareler(resimler[i], round(son * FPS) - kare_no, i % 2 == 0):
            an = kare_no / FPS
            x = next((x for x in alt if x.bas <= an < x.son), None)
            if x:
                yaz(kare, x.metin, font)
            proc.stdin.write(kare.tobytes())
            kare_no += 1
    proc.stdin.close()
    proc.wait()
    m = muzik(s["mood"], dizin)
    subprocess.run(
        [ff, "-y", "-v", "error", "-i", str(sessiz), "-i", str(dizin / "ses.wav"), "-stream_loop", "-1", "-i", str(m),
         "-filter_complex",
         f"[2:a]volume=0.13,afade=t=out:st={sure - 1.5:.2f}:d=1.5[m];[1:a][m]amix=inputs=2:duration=first:normalize=0[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", f"{sure:.2f}",
         str(dizin / "video.mp4")],
        check=True,
    )  # fmt: skip
    print(
        f"{dizin / 'video.mp4'} {sure:.1f} sn | senaryo {t1 - t0:.0f}s, görsel {t2 - t1:.0f}s, "
        f"toplam {time.time() - t0:.0f}s | ~{NEURON['toplam']:.0f} neuron | müzik {MUZIK[s['mood']][0]}"
    )


if __name__ == "__main__":
    main()
