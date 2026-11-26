"""Stok video (b-roll): Pixabay video API'si → sahne zemini (`klip`). Kişiye özgü olmayan sahnelerde fotoğraf yerine
gerçek hareketli görüntü.

Neden (11-20/21): v2 videosunda her sahne fotoğraf + parallax'tı; ~36 Commons görseli 55 sahneye üçer kez dağıldı ve
konuya uzak dolgu görseller kaldı (eleştirmen). Pexels yeni anahtar vermiyor ("issuance paused", 11-21); Pixabay
ücretsiz, 1920×1080 mp4 (`medium`), 100 istek/dk, yanıtlar 24 saat önbelleklenmeli, sistematik toplu indirme yok
(pixabay.com/api/docs). "ai generated" etiketli klipler elenir: üretilmiş görüntüyü gerçek gibi göstermek yanıltır.

Akış: `broll_sec` (LLM: hangi sahne stok video olur, arama sorgusu) → `ara` (önbellekli) → `aday_sec` (LLM: etiketlere
göre en uygun klip ya da hiçbiri) → `hazirla` (ffmpeg: sahne süresine kırp, 1920×1080, 30 fps, kısa GOP, sessiz).
Anahtar: `PIXABAY_API_KEY` (ortam ya da yerel .env); yoksa adım atlanır, video fotoğraflarla üretilir.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

from otomat.ayarlar import KOK
from otomat.trend.llm import Oturum

UC = "https://pixabay.com/api/videos/"
UA = {"User-Agent": "otomat-trend/1.0"}
ONBELLEK = KOK / "calisma" / "trend" / "_stok_onbellek"
ORAN = 0.4  # sahnelerin en çok bu kadarı stok video (geri kalanı konunun gerçek fotoğrafları)
YASAK_ETIKET = (
    "ai generated",
    "ai-generated",
    "generated",
    "artificial intelligence render",
    # 11-26 Riemann: soyut hareketli grafik (beyaz zeminde ikon, siyahta tek harita iğnesi) eleştirmende
    # "boş kadraj" oldu; belgesel b-roll'u gerçek çekim ister
    "animation",
    "animated",
    "motion graphic",
    "3d render",
    "render",
    "particles",
    "abstract",
    "background loop",
    "loop",
    "cartoon",
    "icon",
    "infographic",
    "hologram",
    "intro",
    "logo",
)
MODEL = "glm-5.3"


def anahtar() -> str | None:
    if k := os.environ.get("PIXABAY_API_KEY"):
        return k
    env = KOK / ".env"
    if env.exists():
        for satir in env.read_text(encoding="utf-8").splitlines():
            if satir.startswith("PIXABAY_API_KEY="):
                return satir.split("=", 1)[1].strip() or None
    return None


def ara(sorgu: str, n: int = 8) -> list[dict]:
    """Önbellekli arama (Pixabay şartı: yanıt 24 saat saklanır). Dönüş: ham `hits`."""
    ONBELLEK.mkdir(parents=True, exist_ok=True)
    yol = ONBELLEK / (hashlib.sha1(f"{sorgu}|{n}".encode()).hexdigest()[:16] + ".json")
    if yol.exists() and time.time() - yol.stat().st_mtime < 24 * 3600:
        return json.loads(yol.read_text(encoding="utf-8"))
    k = anahtar()
    if not k:
        return []
    url = UC + "?" + urllib.parse.urlencode({"key": k, "q": sorgu[:100], "per_page": max(3, n), "safesearch": "true"})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as y:
        hits = json.loads(y.read()).get("hits", [])
    yol.write_text(json.dumps(hits), encoding="utf-8")
    time.sleep(0.7)  # 100 istek/dk sınırının altında kal
    return hits


def uygun(hit: dict, sure: float) -> bool:
    etiket = str(hit.get("tags", "")).lower()
    if any(re.search(rf"\b{re.escape(y)}\b", etiket) for y in YASAK_ETIKET):  # sözcük sınırı: "iconic" ≠ "icon"
        return False
    m = (hit.get("videos") or {}).get("medium") or {}
    return bool(m.get("url")) and int(m.get("width", 0)) >= 1280 and float(hit.get("duration", 0)) >= min(sure, 5.0)


SISTEM_SEC = """You are the picture editor of a documentary explainer. Most scenes show a real photo of the story's
people and places. Some scenes would look better as moving STOCK FOOTAGE (generic real-world video: a city at night,
a film set, cameras flashing, newspapers printing, a stock-market screen, people on phones, a crowd). Choose those.
Rules:
- Never for a scene that names or is about a specific person, quotes someone, or has a photo caption: those keep the
  photo. Never for a scene that needs a specific real place or object the stock library cannot have.
- Prefer scenes whose line is about a general idea, mood, industry, reaction, place type or action.
- Choose about {n} scenes, spread through the video, never two neighbouring scenes.
- For each, write a 2-4 word English stock-footage search query describing what should be SEEN (concrete, visual:
  "paparazzi camera flashes", "london street night", "film crew on set"), not the abstract topic.
Return ONLY JSON: {{"secimler": [{{"i": scene index, "sorgu": "..."}}]}}"""

SISTEM_ADAY = """For each scene you get its narration and up to 6 stock clips (id: tags). Pick the clip whose tags
best show what the line is about, or null if none fits (wrong country, wrong era, unrelated subject, cartoon/animation,
icons or graphics on a plain background, an empty frame with one small object). Only real filmed footage with a clear
subject in a real place.
Return ONLY JSON: {"secim": [{"i": scene index, "id": clip id or null}]}"""


def broll_sec(oturum: Oturum, sahneler: list[dict]) -> list[dict]:
    satirlar = []
    for i, sh in enumerate(sahneler):
        if sh.get("tur") in ("harita", "kapanis"):
            continue
        kilit = " [KEEP PHOTO]" if sh.get("tur") == "alinti" or sh.get("etiket") or sh.get("gorsel_uyum") == 2 else ""
        satirlar.append(f"{i}. [{sh.get('tur')}]{kilit} {sh.get('anlatim', '')}")
    n = max(3, int(len(sahneler) * ORAN))
    y = oturum.json_sor(SISTEM_SEC.format(n=n), "\n".join(satirlar), model=MODEL, en_cok=4000, sicaklik=0.3,
                        dusun=False)  # fmt: skip
    out, alinan = [], set()
    for s in (y.get("secimler") or []) if isinstance(y, dict) else []:
        try:
            i = int(s["i"])
        except (KeyError, TypeError, ValueError):
            continue
        sh = sahneler[i] if 0 <= i < len(sahneler) else None
        if not sh or sh.get("tur") in ("harita", "kapanis", "alinti") or sh.get("etiket") or not s.get("sorgu"):
            continue
        if {i - 1, i + 1} & alinan or len(out) >= n:
            continue
        alinan.add(i)
        out.append({"i": i, "sorgu": str(s["sorgu"])[:60]})
    return out


def aday_sec(oturum: Oturum, sahneler: list[dict], secimler: list[dict], sureler: dict[int, float]) -> dict[int, dict]:
    """Her seçili sahne için arama; LLM etiketlere bakıp klibi seçer. Aynı klip iki sahnede kullanılmaz."""
    adaylar: dict[int, list[dict]] = {}
    for s in secimler:
        try:
            hits = ara(s["sorgu"])
        except Exception as e:  # noqa: BLE001 — arama düşerse sahne fotoğrafta kalır
            print(f"stok arama düştü ({s['sorgu']}): {str(e)[:100]}", flush=True)
            continue
        adaylar[s["i"]] = [h for h in hits if uygun(h, sureler.get(s["i"], 6.0))][:6]
    mesaj = "\n\n".join(
        f"SCENE {i}: {sahneler[i].get('anlatim', '')}\n" + "\n".join(f"  {h['id']}: {h.get('tags', '')}" for h in hs)
        for i, hs in adaylar.items() if hs
    )  # fmt: skip
    if not mesaj:
        return {}
    y = oturum.json_sor(SISTEM_ADAY, mesaj, model=MODEL, en_cok=3000, sicaklik=0.1, dusun=False)
    out: dict[int, dict] = {}
    kullanilan: set[int] = set()
    for s in (y.get("secim") or []) if isinstance(y, dict) else []:
        try:
            i, kid = int(s["i"]), s.get("id")
        except (KeyError, TypeError, ValueError):
            continue
        if kid is None:
            continue
        hit = next((h for h in adaylar.get(i, []) if str(h["id"]) == str(kid)), None)
        if hit and hit["id"] not in kullanilan:
            kullanilan.add(hit["id"])
            out[i] = hit
    return out


def hazirla(hit: dict, sure: float, dizin: Path) -> Path:
    """Klibi indir, sahne süresine (+0,5 sn) kırp; kısa klip en çok 1,5× yavaşlatılır. 1920×1080 doldur, 30 fps,
    0,5 sn GOP (HyperFrames her kareyi ayrı arar), ses yok."""
    dizin.mkdir(parents=True, exist_ok=True)
    hedef = dizin / f"px{hit['id']}_{sure:.1f}.mp4"
    if hedef.exists():
        return hedef
    ham = dizin / f"px{hit['id']}_ham.mp4"
    if not ham.exists():
        url = hit["videos"]["medium"]["url"]
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as y:
            ham.write_bytes(y.read())
    sure_k = float(hit.get("duration", sure)) or sure
    yavas = min(1.5, max(1.0, (sure + 0.5) / sure_k))
    vf = (f"setpts={yavas:.3f}*PTS,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,"
          "format=yuv420p")  # fmt: skip
    komut = ["ffmpeg", "-v", "error", "-y", "-i", str(ham), "-t", f"{sure + 0.5:.2f}", "-vf", vf, "-an",
             "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-g", "15", str(hedef)]  # fmt: skip
    subprocess.run(komut, check=True)
    return hedef


def uygula(oturum: Oturum, sahneler: list[dict], sureler: dict[int, float]) -> list[str]:
    """Senaryo sahnelerine `klip` (Pixabay kimliği + etiket) yazar (yerinde). Dönüş: yapılanlar."""
    if not anahtar():
        return ["PIXABAY_API_KEY yok: stok video atlandı"]
    secimler = broll_sec(oturum, sahneler)
    sec = aday_sec(oturum, sahneler, secimler, sureler)
    yapilan = []
    for i, hit in sorted(sec.items()):
        sorgu = next((s["sorgu"] for s in secimler if s["i"] == i), "")
        sahneler[i]["klip"] = {"id": hit["id"], "sorgu": sorgu, "etiket": hit.get("tags", ""),
                               "sayfa": hit.get("pageURL", ""), "yazar": hit.get("user", ""),
                               "url": hit["videos"]["medium"]["url"], "sure": hit.get("duration")}  # fmt: skip
        yapilan.append(f"sahne {i}: {sorgu} → {hit['id']} ({str(hit.get('tags', ''))[:60]})")
    return yapilan


def gecerli_klip(sh: dict) -> bool:
    k = sh.get("klip")
    return isinstance(k, dict) and bool(re.fullmatch(r"\d+", str(k.get("id", "")))) and bool(k.get("url"))
