"""Trend açıklayıcı senaryosu: kaynak paketi → yazar modeli → kod kapıları → olgu denetçisi → onarım.

Kurallar nereden geliyor (docs/arastirma/14-trend-kanali.md):
- YPP "inauthentic/reused content" (support 1311392): haber akışını seslendirmek uygun değil; her videonun kendi tezi
  (özgün açı) olur ve bölüm sırası konuya göre değişir. Yazara "tez" zorunlu alan olarak verilir.
- İlk 5-10 sn vaadi verir (YouTube blog 2026-07-14); kanal tanıtımı yok.
- Soru ile biten başlık ortalamanın altında (vidIQ 2026); somut hikâye çerçevesi.
- HyperFrames film.md: sahne başına ~19 kelime (en çok 30), görünen her parça söylendiği an gelir.
- vox-explainer: statik sahne ≤ 1/3, ardışık iki sahne aynı türde olmaz.
- open-edit: ekrandaki her sayı kaynakta geçer (kod kapısı `sayi_kapisi`).
"""

from __future__ import annotations

import json
import re
from collections import Counter

from otomat.trend.llm import Oturum

TURLER = ("foto", "manset", "sayi", "alinti", "zaman", "bolum", "ikili", "ifade", "kapanis", "harita")
STATIK = ("ifade", "ikili", "alinti")  # tek başına poster gibi duran türler
KELIME_HEDEF = (950, 1350)
SAHNE_KELIME_EN_COK = 34
YASAK_IFADE = ("unlock", "seamless", "supercharge", "game-changer", "game changer", "revolutionize", "effortless",
               "delve", "tapestry", "in today's fast-paced", "buckle up", "let's dive in", "dive into",
               "without further ado", "smash that", "don't forget to subscribe", "in conclusion")  # fmt: skip

SISTEM_YAZAR = """You are the head writer of a fast, smart YouTube explainer channel about whatever the world is talking
about right now. Faceless, narrated, motion-graphics heavy. Viewers arrive curious ("why is everyone talking about X?")
and must leave understanding it better than their friends do.

Write in clear, spoken, energetic but trustworthy English (like a great documentary narrator, not a hype YouTuber).
Short sentences. Concrete nouns. Real numbers only from the sources. No filler, no throat-clearing, no channel intro.

HARD RULES
1. Every factual claim must come from the SOURCE PACK. Cite source ids per scene in "kaynak". If the sources don't say
   it, don't say it. Never invent numbers, dates, quotes, names. Quotes must be verbatim from a source.
2. You must have an original angle: a one-sentence THESIS that reframes the story (a tension, a surprising cause, what
   it reveals about something bigger). The video argues and pays off this thesis; it is not a news readout.
3. The first scene (hook) states the promise within ~8 seconds: what happened + why it is bigger than it looks.
   Never start with "In this video", a greeting, or the channel name.
4. Re-hook every ~90 seconds with a new question or turn ("But here's the part nobody's talking about...").
5. Each scene's narration ("anlatim") is 8-30 words, one idea. Scenes of type sayi, ikili, ifade and alinti hold one
   still graphic, so their narration is at most 20 words. Total narration 950-1350 words.
6. Scene types (field "tur") and their fields — use the type that SHOWS the line, vary them, never the same type twice
   in a row, and keep ifade+ikili+alinti under one third of scenes:
   - "foto": a real photo from the IMAGE LIST. fields: gorsel (image id like "G3"), baslik (optional on-screen headline,
     3-7 words, NOT a copy of the narration), vurgu (list of 1 word from baslik to highlight), etiket (optional
     lower-third naming who/what is shown, 2-5 words), ipucu (word from the narration when the headline appears)
   - "manset": 2-4 real news headlines from the SOURCE PACK shown as clippings. fields: mansetler [{kaynak (publisher),
     baslik (headline text, may be shortened but not changed in meaning), ipucu (narration word that triggers it)}],
     gorsel (optional background image id)
   - "sayi": one real number landing big. fields: deger (number, digits only, no commas), on (prefix like "$"),
     son (suffix like "%" or "M"), etiket (what it measures, 4-10 words), vurgu (1-2 words of etiket), ipucu
   - "alinti": a verbatim quote from a source. fields: metin (≤ 22 words), kim (speaker, role), gorsel (optional id)
   - "zaman": 2-4 dated events. fields: olaylar [{tarih (short, e.g. "2013" or "Dec 2023"), olay (≤ 8 words),
     ipucu (narration word)}]
   - "bolum": chapter card between acts. fields: no ("01".."05"), baslik (2-5 words), gorsel (optional image id that
     fits the chapter). anlatim is one short line (≤ 12 words).
   - "ikili": comparison of two values. fields: baslik (optional), sol {etiket, deger, ipucu}, sag {etiket, deger, ipucu}
   - "ifade": one big statement or question on screen. fields: metin (≤ 9 words, may echo the narration's key line),
     vurgu (1 word), gorsel (optional id)
   - "harita": a satellite flight from space down to a real place that matters to the story (at most 2 per video,
     only when the place itself is part of the story). fields: yer (on-screen place label, 1-3 words), yer_wiki (the
     exact English Wikipedia article title of that place, e.g. "Miami", "Edinburgh"), yakinlik ("city", "region" or
     "country"). Narration 12-26 words.
   - "kapanis": final scene only. fields: metin (the one idea to remember, ≤ 8 words), vurgu (1 word)
7. 3-5 chapters ("bolum" scenes) after the hook. Last scene is "kapanis". No "subscribe" begging; at most one natural
   line inviting viewers to share what they think, inside the last two scenes.
8. Use images from the IMAGE LIST only by id. Use each image at most twice. Prefer images that show what the line says.
9. On-screen text never repeats the narration word for word (except quotes and ifade's key line).
10. Banned words/phrases: unlock, seamless, supercharge, game-changer, revolutionize, effortless, delve, tapestry,
    "let's dive in", "buckle up", "without further ado", "in conclusion".
11. Numbers in narration: write them as digits ("750,000", "2013", "$265 million") — the voice engine reads digits.

Also produce:
- "baslik_adaylari": 5 YouTube titles, 45-70 characters, concrete story frame, no clickbait lies, not ending with "?",
  name the trending thing in the first 40 characters.
- "kapak_metni": 2-5 punchy words for the thumbnail (not the title).
- "kapak_gorsel": image id for the thumbnail.
- "aciklama": a 2-3 sentence YouTube description opening (no hashtags).
- "kesitler": 3 Shorts cut from the video: each {"sahneler": [list of scene indexes, consecutive, 25-50 seconds of
  narration total], "baslik": Shorts title ≤ 60 chars, "kanca": the first line on screen ≤ 7 words}. Each Short must
  make sense on its own and start with a strong line.

Return ONLY JSON:
{"tez": str, "baslik_adaylari": [..], "kapak_metni": str, "kapak_gorsel": str, "aciklama": str,
 "sahneler": [{"tur": str, "anlatim": str, "kaynak": [ids], ...type fields}], "kesitler": [..]}"""

SISTEM_DENETCI = """You are a meticulous fact-checker for a documentary explainer. You get a SOURCE PACK and a SCRIPT
(JSON scenes). For every scene, check every factual claim in "anlatim" and in on-screen fields (baslik, etiket, deger,
on, son, mansetler, metin, olaylar, sol, sag, kim) against the SOURCE PACK only — not your memory.
Flag: unsupported claims, wrong numbers/dates/names, quotes that are not verbatim in a source, headlines not present in
the sources, causal claims the sources do not make, and anything that presents speculation as fact.
Do NOT flag style. Do NOT flag claims that are clearly supported.
Return ONLY JSON: {"sorunlar": [{"sahne": index, "alan": field, "sorun": what is wrong, "duzeltme": a corrected
version that the sources support (or "REMOVE")}]}. Empty list if everything is supported."""

SISTEM_ONARIM = """You revise a documentary explainer script (JSON) to fix the listed fact-check problems. Change only
what is needed; keep scene count roughly the same, keep the structure, types and style. If a claim can't be supported,
rewrite the line with a supported fact or remove the scene. Keep all HARD RULES of the original brief (types, fields,
word counts, no same type twice in a row). Return ONLY the full corrected JSON object (same schema)."""


def kaynak_paketi(wiki, haberler: list, ek_metinler: list[tuple[str, str]] | None = None,
                  en_cok_karakter: int = 32000) -> tuple[str, dict]:  # fmt: skip
    """Numaralı kaynak metni: W1.. Wikipedia bölümleri, N1.. haber başlıkları, A1.. ek metinler. Dönüş: (metin, kimlik→URL)."""
    parcalar, bag, n = [], {}, 0
    for i, (b, govde) in enumerate(wiki.bolumler()):
        kimlik = f"W{i + 1}"
        parca = f"[{kimlik}] Wikipedia — {wiki.baslik} — section: {b}\n{govde.strip()}\n"
        if n + len(parca) > en_cok_karakter * 0.8:
            break
        parcalar.append(parca)
        bag[kimlik] = f"https://en.wikipedia.org/w/index.php?oldid={wiki.revid}"
        n += len(parca)
    for i, h in enumerate(haberler[:25]):
        kimlik = f"N{i + 1}"
        parcalar.append(f"[{kimlik}] News headline — {h.yayinci}, {h.zaman:%Y-%m-%d}: {h.baslik}\n")
        bag[kimlik] = h.url
    for i, (url, metin) in enumerate(ek_metinler or []):
        kimlik = f"A{i + 1}"
        parca = f"[{kimlik}] Article text ({url}):\n{metin.strip()[:6000]}\n"
        if n + len(parca) > en_cok_karakter:
            break
        parcalar.append(parca)
        bag[kimlik] = url
        n += len(parca)
    return "\n".join(parcalar), bag


def gorsel_listesi(gorseller: list) -> str:
    satirlar = []
    for i, g in enumerate(gorseller):
        ad = g.dosya.removeprefix("File:").rsplit(".", 1)[0]
        yon = "landscape" if g.genislik >= g.yukseklik * 1.15 else ("portrait" if g.yukseklik > g.genislik * 1.15
                                                                     else "square")  # fmt: skip
        satirlar.append(f"G{i + 1}: {ad} ({yon})")
    return "\n".join(satirlar)


# ------------------------------------------------------------------------------------------------- kod kapıları
def _rakamlar(s: str) -> set[str]:
    """Metindeki sayılar, binlik ayırıcısız ("750,227" → "750227"); tek haneliler sayılmaz."""
    return {re.sub(r"[,\s]", "", m) for m in re.findall(r"\d[\d,]*(?:\.\d+)?", s) if len(re.sub(r"\D", "", m)) >= 2}


def _ekran_metni(sh: dict) -> str:
    alanlar = [sh.get(k, "") for k in ("baslik", "etiket", "metin", "kim", "on", "son")]
    alanlar.append(str(sh.get("deger", "")))
    for m in sh.get("mansetler") or []:
        alanlar += [m.get("baslik", ""), m.get("kaynak", "")]
    for o in sh.get("olaylar") or []:
        alanlar += [o.get("tarih", ""), o.get("olay", "")]
    for y in ("sol", "sag"):
        if isinstance(sh.get(y), dict):
            alanlar += [sh[y].get("etiket", ""), str(sh[y].get("deger", ""))]
    return " ".join(str(a) for a in alanlar)


def _sayi_cevir(s: str) -> set[str]:
    """'$265M' → {'265', '265000000'}; '1.2 billion' → {'1.2', '1200000000'} gibi eşdeğerler."""
    out = set()
    for m in re.finditer(r"(\d[\d,]*(?:\.\d+)?)\s*(k|m|b|thousand|million|billion|trillion)?\b", s.lower()):
        ham = m.group(1).replace(",", "")
        out.add(ham)
        kat = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6, "b": 1e9, "billion": 1e9, "trillion": 1e12}
        if m.group(2):
            try:
                out.add(str(int(round(float(ham) * kat[m.group(2)]))))
            except ValueError:
                pass
    return out


def sayi_kapisi(senaryo: dict, kaynak_metni: str) -> list[str]:
    """Anlatımdaki ve ekrandaki her ≥2 haneli sayı kaynak paketinde (eşdeğer biçimiyle) geçmeli."""
    kaynakta = _sayi_cevir(kaynak_metni) | _rakamlar(kaynak_metni)
    sorunlar = []
    for i, sh in enumerate(senaryo.get("sahneler", [])):
        for alan, metin in (("anlatim", sh.get("anlatim", "")), ("ekran", _ekran_metni(sh))):
            for s in _sayi_cevir(metin):
                if len(re.sub(r"\D", "", s)) < 2 or s in kaynakta:
                    continue
                if any(s.split(".")[0] == k.split(".")[0] for k in kaynakta if "." in s):
                    continue
                sorunlar.append(f"sahne {i} {alan}: '{s}' kaynak paketinde yok")
    return sorunlar


def yapi_kapisi(senaryo: dict, gorsel_sayisi: int) -> list[str]:
    """Biçim kuralları: türler, alanlar, kelime sınırları, çeşitlilik, görsel kimlikleri, yasak ifadeler."""
    s = senaryo.get("sahneler") or []
    hata = []
    if len(s) < 25:
        hata.append(f"sahne sayısı {len(s)} (< 25)")
    toplam = sum(len(sh.get("anlatim", "").split()) for sh in s)
    if not KELIME_HEDEF[0] <= toplam <= KELIME_HEDEF[1] + 150:
        hata.append(f"toplam anlatım {toplam} kelime (hedef {KELIME_HEDEF[0]}-{KELIME_HEDEF[1]})")
    if not senaryo.get("tez"):
        hata.append("tez yok")
    gorsel_kullanim: Counter = Counter()
    for i, sh in enumerate(s):
        tur = sh.get("tur")
        if tur not in TURLER:
            hata.append(f"sahne {i}: bilinmeyen tür {tur}")
            continue
        n = len(sh.get("anlatim", "").split())
        sinir = 22 if tur in ("sayi", "ikili", "ifade", "alinti") else (14 if tur == "bolum" else SAHNE_KELIME_EN_COK)
        if not 1 <= n <= sinir:
            hata.append(f"sahne {i} ({tur}): anlatım {n} kelime (en çok {sinir})")
        if i and tur == s[i - 1].get("tur") and tur not in ("foto",):
            hata.append(f"sahne {i}: bir öncekiyle aynı tür ({tur})")
        if i >= 2 and tur == "foto" == s[i - 1].get("tur") == s[i - 2].get("tur"):
            hata.append(f"sahne {i}: üç foto üst üste")
        gerek = {"foto": ["gorsel"], "manset": ["mansetler"], "sayi": ["deger", "etiket"], "alinti": ["metin", "kim"],
                 "zaman": ["olaylar"], "bolum": ["baslik"], "ikili": ["sol", "sag"], "ifade": ["metin"],
                 "kapanis": ["metin"], "harita": ["yer", "yer_wiki"]}[tur]  # fmt: skip
        for alan in gerek:
            if not sh.get(alan):
                hata.append(f"sahne {i} ({tur}): '{alan}' eksik")
        for alan in ("gorsel",):
            g = sh.get(alan)
            if g:
                m = re.fullmatch(r"G(\d+)", str(g))
                if not m or not 1 <= int(m.group(1)) <= gorsel_sayisi:
                    hata.append(f"sahne {i}: görsel kimliği geçersiz ({g})")
                else:
                    gorsel_kullanim[g] += 1
        if tur == "sayi":
            try:
                float(str(sh.get("deger")).replace(",", ""))
            except ValueError:
                hata.append(f"sahne {i}: sayi.deger sayı değil ({sh.get('deger')})")
        metin = (sh.get("anlatim", "") + " " + _ekran_metni(sh)).lower()
        for y in YASAK_IFADE:
            if y in metin:
                hata.append(f"sahne {i}: yasak ifade '{y}'")
    for g, n in gorsel_kullanim.items():
        if n > 2:
            hata.append(f"görsel {g} {n} kez kullanılmış (en çok 2)")
    if s and s[-1].get("tur") != "kapanis":
        hata.append("son sahne kapanis değil")
    statik = sum(1 for sh in s if sh.get("tur") in STATIK)
    if s and statik > len(s) / 3:
        hata.append(f"statik sahne {statik}/{len(s)} (en çok üçte bir)")
    if sum(1 for sh in s if sh.get("tur") == "harita") > 2:
        hata.append("harita sahnesi 2'den fazla")
    bolum = sum(1 for sh in s if sh.get("tur") == "bolum")
    if not 3 <= bolum <= 5:
        hata.append(f"bölüm kartı {bolum} (3-5)")
    for b in senaryo.get("baslik_adaylari") or []:
        if b.strip().endswith("?"):
            hata.append(f"başlık soru ile bitiyor: {b}")
    if len(senaryo.get("kesitler") or []) < 3:
        hata.append("3 kesit yok")
    return hata


# ------------------------------------------------------------------------------------------------- akış
def yaz(oturum: Oturum, konu: dict, kaynak_metni: str, gorsel_metni: str, model: str = "kimi-k3") -> dict:
    mesaj = (f"TOPIC: {konu['ad']}\nWHY IT IS TRENDING (from the radar): {konu.get('neden', '')}\n"
             f"EDITOR'S SUGGESTED ANGLE (you may sharpen it): {konu.get('aci', '')}\n\n"
             f"=== SOURCE PACK ===\n{kaynak_metni}\n\n=== IMAGE LIST (real, licensed; use by id) ===\n{gorsel_metni}\n\n"
             "Write the full script JSON now.")  # fmt: skip
    return oturum.json_sor(SISTEM_YAZAR, mesaj, model=model, en_cok=16000, sicaklik=0.75)


def denetle(oturum: Oturum, senaryo: dict, kaynak_metni: str, model: str = "glm-5.3") -> list[dict]:
    sade = {"sahneler": [{k: v for k, v in sh.items() if k != "kaynak"} | {"i": i}
                         for i, sh in enumerate(senaryo.get("sahneler", []))]}  # fmt: skip
    mesaj = f"=== SOURCE PACK ===\n{kaynak_metni}\n\n=== SCRIPT ===\n{json.dumps(sade, ensure_ascii=False)}"
    y = oturum.json_sor(SISTEM_DENETCI, mesaj, model=model, en_cok=8000, sicaklik=0.0)
    return list(y.get("sorunlar", [])) if isinstance(y, dict) else []


def onar(oturum: Oturum, senaryo: dict, sorunlar: list, kaynak_metni: str, gorsel_metni: str,
         model: str = "kimi-k3") -> dict:  # fmt: skip
    mesaj = (f"=== SOURCE PACK ===\n{kaynak_metni}\n\n=== IMAGE LIST ===\n{gorsel_metni}\n\n=== ORIGINAL BRIEF ===\n"
             f"{SISTEM_YAZAR}\n\n=== CURRENT SCRIPT ===\n{json.dumps(senaryo, ensure_ascii=False)}\n\n"
             f"=== PROBLEMS TO FIX ===\n{json.dumps(sorunlar, ensure_ascii=False, indent=1)}")  # fmt: skip
    return oturum.json_sor(SISTEM_ONARIM, mesaj, model=model, en_cok=16000, sicaklik=0.3)


def uret(oturum: Oturum, konu: dict, kaynak_metni: str, gorsel_metni: str, gorsel_sayisi: int,
         tur_sayisi: int = 4, kayit: list | None = None) -> dict:  # fmt: skip
    """Yaz → (kod kapıları + olgu denetimi) → onar döngüsü. Turlar bitince hâlâ desteklenmeyen sahne çıkarılır
    (son çare, Shorts hattındaki satır çıkarmanın karşılığı); kod kapısı yine geçmezse çağıran düşürür."""
    kayit = kayit if kayit is not None else []
    print("senaryo: yazılıyor", flush=True)
    s = yaz(oturum, konu, kaynak_metni, gorsel_metni)
    for tur in range(tur_sayisi):
        kod = yapi_kapisi(s, gorsel_sayisi) + sayi_kapisi(s, kaynak_metni)
        olgu = denetle(oturum, s, kaynak_metni)
        kayit.append({"tur": tur, "kod": kod, "olgu": olgu, "sahne": len(s.get("sahneler", []))})
        print(f"senaryo tur {tur}: {len(s.get('sahneler', []))} sahne, kod {len(kod)}, olgu {len(olgu)}", flush=True)
        if not kod and not olgu:
            return s
        sorunlar = [{"kod_kurali": k} for k in kod] + olgu
        s = onar(oturum, s, sorunlar, kaynak_metni, gorsel_metni)
    olgu = denetle(oturum, s, kaynak_metni)
    korunan = {"bolum", "kapanis"}
    cikar = {int(o["sahne"]) for o in olgu if str(o.get("sahne", "")).isdigit()}
    cikar = {i for i in cikar if 0 < i < len(s.get("sahneler", [])) and s["sahneler"][i].get("tur") not in korunan}
    if cikar:
        s["sahneler"] = [sh for i, sh in enumerate(s["sahneler"]) if i not in cikar]
    kod = yapi_kapisi(s, gorsel_sayisi) + sayi_kapisi(s, kaynak_metni)
    kayit.append({"tur": tur_sayisi, "kod": kod, "olgu": olgu, "cikarilan": sorted(cikar),
                  "sahne": len(s.get("sahneler", []))})  # fmt: skip
    print(f"senaryo son: {len(cikar)} sahne çıkarıldı, kod {len(kod)}", flush=True)
    return s
