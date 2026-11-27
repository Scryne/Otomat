"""Stok video (b-roll): Pixabay video API'si → sahne zemini (`klip`). Kişiye özgü olmayan sahnelerde fotoğraf yerine
gerçek hareketli görüntü.

Neden (11-20/21): v2 videosunda her sahne fotoğraf + parallax'tı; ~36 Commons görseli 55 sahneye üçer kez dağıldı ve
konuya uzak dolgu görseller kaldı (eleştirmen). Pexels yeni anahtar vermiyor ("issuance paused", 11-21); Pixabay
ücretsiz, 1920×1080 mp4 (`medium`), 100 istek/dk, yanıtlar 24 saat önbelleklenmeli, sistematik toplu indirme yok
(pixabay.com/api/docs). "ai generated" etiketli klipler elenir: üretilmiş görüntüyü gerçek gibi göstermek yanıltır.

Akış: `broll_sec` (LLM: hangi sahne stok video olur, iki arama sorgusu) → `ara` (önbellekli) → `aday_sec` (görüntü
modeli: adayların küçük resimlerine bakıp en uygun klip ya da hiçbiri; düşerse etiketlerle) → `hazirla` (ffmpeg: sahne
süresine kırp, 1920×1080, 30 fps, kısa GOP, sessiz).

11-27: etiketle seçim Miss Universe videosunda 17 klibin ~10'unu ilgisiz yaptı ("judges table" → dosya dolabı,
"children playing" → gökyüzünde sabun köpüğü, "moving boxes" → havalimanı yürüyen merdiveni) ve "she decided to
prepare" sahnesine spor yapan yabancı bir kadın koydu (izleyici onu yarışmacı sanar). Etiket klibin ne gösterdiğini
söylemiyor; seçim artık küçük resme bakılarak yapılıyor ve belirli bir kişiyi anlatan sahne (zamirle de olsa) stok
almıyor.
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
    # tanınabilir tek yüz: izleyici hikâyedeki kişi sanıyor (11-26 Riemann: "yaşlı adam yakın plan")
    "portrait",
    "face",
    "close-up",
    "closeup",
    "headshot",
    "selfie",
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
    if hit.get("isAiGenerated") or hit.get("isLowQuality"):  # Pixabay'in kendi işaretleri (etiketsiz AI klipler de var)
        return False
    etiket = str(hit.get("tags", "")).lower()
    if any(re.search(rf"\b{re.escape(y)}\b", etiket) for y in YASAK_ETIKET):  # sözcük sınırı: "iconic" ≠ "icon"
        return False
    m = (hit.get("videos") or {}).get("medium") or {}
    return bool(m.get("url")) and int(m.get("width", 0)) >= 1280 and float(hit.get("duration", 0)) >= min(sure, 5.0)


def kaynak_url(hit: dict) -> str:
    """1080p varsa o ("large"), yoksa "medium" (1280×720; 1920'ye büyütülünce yumuşak duruyordu)."""
    v = hit.get("videos") or {}
    b = v.get("large") or {}
    if b.get("url") and int(b.get("width", 0)) >= 1920 and int(b.get("size", 0) or 0) < 120_000_000:
        return b["url"]
    return v["medium"]["url"]


SISTEM_SEC = """You are the picture editor of a documentary explainer. Most scenes show a real photo of the story's
people and places. Some scenes would look better as moving STOCK FOOTAGE (generic real-world video: a city at night,
a film set, cameras flashing, newspapers printing, a stock-market screen, people on phones, a crowd). Choose those.
Rules:
- Never for a scene that names or is about a specific person, quotes someone, or has a photo caption: those keep the
  photo. This includes lines that refer to the story's person only by a pronoun ("she trained for months", "he moved
  to Paris"): any person in stock footage would be taken for them. Never for a scene that needs a specific real place
  or object the stock library cannot have.
- Prefer scenes whose line is about a general idea, mood, industry, reaction, place type or action.
- Choose about {n} scenes, spread through the video, never two neighbouring scenes. Scenes marked [NO PHOTO: needs
  footage] have no picture at all: choose every one of them you can.
- For each, write TWO different 2-4 word English stock-footage search queries describing what should be SEEN
  (concrete, visual, things a stock library really has: "paparazzi camera flashes", "london street night", "film crew
  on set"), not the abstract topic. The second is a broader fallback ("stage spotlights" for "pageant stage").
Return ONLY JSON: {{"secimler": [{{"i": scene index, "sorgular": ["...", "..."]}}]}}"""

SISTEM_GORUNTU = """You are the picture editor of a documentary explainer. For each SCENE you get its narration and
a row of stock-footage candidates on the contact sheet (labels like 12a, 12b: scene 12, candidate a), each with its
tags. Look at the PICTURES. Pick the candidate that a viewer would accept as showing what the line is about, or null
if none does. Reject:
- anything unrelated to the line or the story (a rock concert for a beauty pageant, soap bubbles for a childhood
  memory, an airport for "moving house"),
- one person as the clear subject (a face, a woman exercising, a man at a desk): the viewer takes them for a person in
  the story. People only as crowds, hands, silhouettes, backs or far away,
- animation, graphics, icons, renders, text on screen, logos, a plain background, a near-empty frame,
- the wrong country, era or season when the line makes it obvious,
- for a scene marked ABOUT A SPECIFIC PERSON: any candidate where a person is visible (even partly: hair, body,
  a figure at a desk); only places, objects, landscapes or a crowd too far to see faces.
Prefer a clear real subject, good light, a frame that fills the screen. When unsure, null: the scene keeps a photo.
Return ONLY JSON: {"secim": [{"i": scene index, "id": "12a" or null}]}"""

SISTEM_ADAY = """For each scene you get its narration and up to 6 stock clips (id: tags). Pick the clip whose tags
best show what the line is about, or null if none fits (wrong country, wrong era, unrelated subject, cartoon/animation,
icons or graphics on a plain background, an empty frame with one small object). Only real filmed footage with a clear
subject in a real place. Never a close-up or portrait of one identifiable person (a viewer would take a random
face for a person in the story); people only as crowds, hands, backs or far away.
Return ONLY JSON: {"secim": [{"i": scene index, "id": clip id or null}]}"""


def broll_sec(oturum: Oturum, sahneler: list[dict]) -> list[dict]:
    satirlar = []
    for i, sh in enumerate(sahneler):
        if sh.get("tur") in ("harita", "kapanis"):
            continue
        kilit = " [KEEP PHOTO]" if sh.get("tur") == "alinti" or sh.get("etiket") or sh.get("gorsel_uyum") == 2 else ""
        if sh.get("tur") == "foto" and not sh.get("gorsel"):
            kilit = " [NO PHOTO: needs footage]"  # görsel havuzu tükenmiş sahne: önce bunlar seçilir
        satirlar.append(f"{i}. [{sh.get('tur')}]{kilit} {sh.get('anlatim', '')}")
    gorselsiz = sum(1 for sh in sahneler if sh.get("tur") == "foto" and not sh.get("gorsel"))
    n = max(3, int(len(sahneler) * ORAN), gorselsiz)
    y = oturum.json_sor(SISTEM_SEC.format(n=n), "\n".join(satirlar), model=MODEL, en_cok=4000, sicaklik=0.3,
                        dusun=False)  # fmt: skip
    out, alinan = [], set()
    for s in (y.get("secimler") or []) if isinstance(y, dict) else []:
        try:
            i = int(s["i"])
        except (KeyError, TypeError, ValueError):
            continue
        sh = sahneler[i] if 0 <= i < len(sahneler) else None
        sorgular = [str(q)[:60] for q in (s.get("sorgular") or [s.get("sorgu")]) if q][:2]
        if not sh or sh.get("tur") in ("harita", "kapanis", "alinti") or sh.get("etiket") or not sorgular:
            continue
        gorselsiz = sh.get("tur") == "foto" and not sh.get("gorsel")
        if (not gorselsiz and {i - 1, i + 1} & alinan) or len(out) >= n:  # görselsiz sahnede komşu kuralı yok
            continue
        alinan.add(i)
        out.append({"i": i, "sorgu": sorgular[0], "sorgular": sorgular})
    return out


ZAMIR = re.compile(r"\b(she|he|her|his|him|herself|himself)\b", re.I)


def kisili(anlatim: str) -> bool:
    """Satır belirli bir kişiyi tekil zamirle anlatıyor mu. 11-27: "she decided to prepare" sahnesinde görüntü modeli
    saçı yapılan bir kişiyi seçti; izleyici onu hikâyedeki kadın sanar. Bu satırlarda görünür kişi kabul edilmez
    (yer, nesne, kalabalık olur)."""
    return bool(ZAMIR.search(anlatim))


ADAY_EN_COK = 6  # sahne başına küçük resim (kontak sayfasında bir satır)
HUCRE = (256, 144)
SAYFA_SAHNE = 4  # sayfa başına sahne satırı: 1536×576; görüntü modelinin rahat okuduğu boy


def adaylari_topla(secimler: list[dict], sureler: dict[int, float]) -> dict[int, list[dict]]:
    """Her sahne için iki sorgunun uygun sonuçları (önce birinci sorgu), tekrarsız, en çok ADAY_EN_COK."""
    adaylar: dict[int, list[dict]] = {}
    for s in secimler:
        gorulen, liste = set(), []
        for q in s.get("sorgular") or [s["sorgu"]]:
            try:
                hits = ara(q, n=10)
            except Exception as e:  # noqa: BLE001 — arama düşerse sahne fotoğrafta kalır
                print(f"stok arama düştü ({q}): {str(e)[:100]}", flush=True)
                continue
            for h in hits:
                if h["id"] not in gorulen and uygun(h, sureler.get(s["i"], 6.0)):
                    gorulen.add(h["id"])
                    liste.append(h)
        adaylar[s["i"]] = liste[:ADAY_EN_COK]
    return adaylar


def _kucuk_resim(hit: dict) -> Path | None:
    yol = ONBELLEK / "kucuk" / f"{hit['id']}.jpg"
    if yol.exists():
        return yol
    url = ((hit.get("videos") or {}).get("medium") or {}).get("thumbnail")
    if not url:
        return None
    yol.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as y:
            yol.write_bytes(y.read())
    except Exception:  # noqa: BLE001 — küçük resmi inmeyen aday sayfada boş kalır, seçilmez
        return None
    return yol


def aday_sayfalari(adaylar: dict[int, list[dict]]) -> list[tuple[bytes, list[int]]]:
    """Sahne başına bir satır: `12a`, `12b`… etiketli küçük resimler. Dönüş: (JPEG, sayfadaki sahneler)."""
    import io

    from PIL import Image, ImageDraw

    from otomat.trend.gorsel_secici import _yazi_tipi

    w, h = HUCRE
    yazi = _yazi_tipi(24)
    sahneler = [i for i, hs in adaylar.items() if hs]
    out = []
    for bas in range(0, len(sahneler), SAYFA_SAHNE):
        grup = sahneler[bas : bas + SAYFA_SAHNE]
        sayfa = Image.new("RGB", (w * ADAY_EN_COK, h * len(grup)), (24, 24, 26))
        cizim = ImageDraw.Draw(sayfa)
        for r, i in enumerate(grup):
            for c, hit in enumerate(adaylar[i]):
                x, y = c * w, r * h
                if (k := _kucuk_resim(hit)) is not None:
                    try:
                        with Image.open(k) as im:
                            kucuk = im.convert("RGB")
                            kucuk.thumbnail((w - 4, h - 4))
                        sayfa.paste(kucuk, (x + (w - kucuk.width) // 2, y + (h - kucuk.height) // 2))
                    except OSError:
                        pass
                etiket = f"{i}{chr(97 + c)}"
                cizim.rectangle((x + 3, y + 3, x + 12 + 15 * len(etiket), y + 33), fill=(255, 214, 10))
                cizim.text((x + 7, y + 4), etiket, fill=(17, 17, 17), font=yazi)
        tampon = io.BytesIO()
        sayfa.save(tampon, "JPEG", quality=85)
        out.append((tampon.getvalue(), grup))
    return out


def goruntuyle_sec(oturum: Oturum, sahneler: list[dict], adaylar: dict[int, list[dict]],
                   hikaye: str = "") -> dict[int, dict]:  # fmt: skip
    """Görüntü modeli her sahne satırına bakar; dönüş sahne → seçilen hit. Sayfa düşerse o sahneler seçilmez."""
    from otomat.trend.gorsel_secici import goruntu_sor

    out: dict[int, dict] = {}
    for sayfa, grup in aday_sayfalari(adaylar):
        sahne_metni = []
        for i in grup:
            kisi = " [ABOUT A SPECIFIC PERSON: reject every candidate with a visible person]" if kisili(
                sahneler[i].get("anlatim", "")) else ""  # fmt: skip
            satir = [f"SCENE {i}{kisi}: {sahneler[i].get('anlatim', '')}"]
            satir += [f"  {i}{chr(97 + c)}: {h.get('tags', '')}" for c, h in enumerate(adaylar[i])]
            sahne_metni.append("\n".join(satir))
        metin = f"STORY: {hikaye[:400]}\n\n" + "\n\n".join(sahne_metni)
        try:
            y = goruntu_sor(oturum, SISTEM_GORUNTU, [sayfa], metin, en_cok=800)
        except Exception as e:  # noqa: BLE001
            print(f"stok görüntü seçimi düştü (sahne {grup}): {str(e)[:100]}", flush=True)
            continue
        for s in (y.get("secim") or []) if isinstance(y, dict) else []:
            m = re.fullmatch(r"(\d+)([a-z])", str(s.get("id") or "").strip().lower())
            if not m or int(m.group(1)) not in grup:
                continue
            i, c = int(m.group(1)), ord(m.group(2)) - 97
            if 0 <= c < len(adaylar[i]):
                out[i] = adaylar[i][c]
    return out


def aday_sec(oturum: Oturum, sahneler: list[dict], secimler: list[dict], sureler: dict[int, float],
             hikaye: str = "") -> dict[int, dict]:  # fmt: skip
    """Her seçili sahne için arama; görüntü modeli küçük resimlere bakıp klibi seçer (bütünüyle düşerse LLM
    etiketlerle). Aynı klip iki sahnede kullanılmaz."""
    adaylar = adaylari_topla(secimler, sureler)
    secilen: dict[int, dict] | None
    try:
        secilen = goruntuyle_sec(oturum, sahneler, adaylar, hikaye)
    except Exception as e:  # noqa: BLE001
        print(f"stok görüntü seçimi atlandı, etiketle seçilir: {str(e)[:120]}", flush=True)
        secilen = None
    if secilen is not None:
        out: dict[int, dict] = {}
        for i, hit in sorted(secilen.items()):
            if hit["id"] not in {h["id"] for h in out.values()}:
                out[i] = hit
        return out
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
    if karanlik_bas(hedef):
        hedef.unlink(missing_ok=True)
        raise RuntimeError("klip karanlık başlıyor (animasyon girişi)")
    return hedef


def karanlik_bas(yol: Path, sure: float = 0.6, esik: float = 22.0) -> bool:
    """İlk `sure` saniyenin ortalama parlaklığı (Y, 0-255) eşiğin altında mı. 11-26 Riemann: "news broadcast studio"
    klibi siyahla açılan bir hareketli grafik girişiydi, videoda 0,37 sn siyah kare kaldı. Çağıran (`plan_kur`) bu
    hatada sahneyi fotoğrafta bırakır."""
    suzgec = "signalstats,metadata=print:file=-:key=lavfi.signalstats.YAVG"  # -v error'da yalnız file=- yazar
    r = subprocess.run(["ffmpeg", "-v", "error", "-t", f"{sure}", "-i", str(yol), "-vf", suzgec, "-f", "null", "-"],
                       capture_output=True, text=True)  # fmt: skip
    degerler = [float(m) for m in re.findall(r"YAVG=([\d.]+)", r.stderr + r.stdout)]
    return bool(degerler) and min(degerler) < esik


def uygula(oturum: Oturum, sahneler: list[dict], sureler: dict[int, float], hikaye: str = "") -> list[str]:
    """Senaryo sahnelerine `klip` (Pixabay kimliği + etiket) yazar (yerinde). Dönüş: yapılanlar."""
    if not anahtar():
        return ["PIXABAY_API_KEY yok: stok video atlandı"]
    secimler = broll_sec(oturum, sahneler)
    sec = aday_sec(oturum, sahneler, secimler, sureler, hikaye)
    yapilan = []
    for i, hit in sorted(sec.items()):
        sorgu = next((s["sorgu"] for s in secimler if s["i"] == i), "")
        sahneler[i]["klip"] = {"id": hit["id"], "sorgu": sorgu, "etiket": hit.get("tags", ""),
                               "sayfa": hit.get("pageURL", ""), "yazar": hit.get("user", ""),
                               "url": kaynak_url(hit), "sure": hit.get("duration")}  # fmt: skip
        yapilan.append(f"sahne {i}: {sorgu} → {hit['id']} ({str(hit.get('tags', ''))[:60]})")
    return yapilan


def gecerli_klip(sh: dict) -> bool:
    k = sh.get("klip")
    return isinstance(k, dict) and bool(re.fullmatch(r"\d+", str(k.get("id", "")))) and bool(k.get("url"))
