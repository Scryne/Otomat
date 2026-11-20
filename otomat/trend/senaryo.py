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
from pathlib import Path

from otomat.trend.llm import Oturum

TURLER = ("foto", "manset", "sayi", "alinti", "zaman", "bolum", "ikili", "ifade", "kapanis", "harita")
STATIK = ("ifade", "ikili", "alinti")  # tek başına poster gibi duran türler
KELIME_HEDEF = (650, 1350)  # ~6-9 dk (Chatterbox ~2,4 kelime/sn + aralar)
BOLUM_MODEL = "glm-5.3"  # bölüm sahneleri: kimi-k3 çağrı başı ~0,07 pay, glm-5.3 ~0,007 (11-20 ölçümü)
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

"""

SISTEM_ISKELET = (
    SISTEM_YAZAR
    + """

YOUR TASK NOW: plan the video, do not write scenes yet. Return ONLY JSON:
{"tez": the one-sentence thesis,
 "kanca": what the first 2-3 scenes (before chapter 01) must establish, 1-2 sentences,
 "bolumler": [{"no": "01", "baslik": 2-5 words, "amac": what this chapter shows and how it moves the thesis forward
   (2 sentences), "kaynaklar": [source ids to use], "kelime": target narration words for the chapter}],   (3-5 chapters;
   hook ~110 words, chapters together ~950-1150 words, closing ~60 words)
 "kapanis": the closing idea (1 sentence),
 "baslik_adaylari": 5 YouTube titles, 45-70 characters, concrete story frame, not ending with "?", the trending thing
   named in the first 40 characters,
 "kapak_metni": 2-5 punchy thumbnail words (not the title), "kapak_gorsel": image id for the thumbnail,
 "aciklama": 2-3 sentence YouTube description opening (no hashtags)}"""
)

SISTEM_BOLUM = (
    SISTEM_YAZAR
    + """

YOUR TASK NOW: write the scenes for ONE part of the video (the plan and the scenes written so far are given). Continue
naturally from the previous scene (no repeated facts, no repeated scene type at the boundary). Hit the target word
count for this part. Return ONLY JSON: {"sahneler": [{"tur": str, "anlatim": str, "kaynak": [ids], ...type fields}]}"""
)

SISTEM_KESIT = """You pick Shorts from a finished explainer script. Each Short is a run of CONSECUTIVE scenes whose
narration totals 70-130 words (25-50 seconds), makes sense on its own without the rest of the video, starts with a
strong line and ends on a payoff. Pick the 3 strongest, non-overlapping. Avoid runs that start with a chapter card.
Return ONLY JSON: {"kesitler": [{"sahneler": [indexes], "baslik": Shorts title of at most 60 chars, "kanca": the first
line on screen, at most 7 words (a hook, not a summary)}]}"""

SISTEM_DENETCI = """You are a meticulous fact-checker for a documentary explainer. You get a SOURCE PACK and a SCRIPT
(JSON scenes). For every scene, check every factual claim in "anlatim" and in on-screen fields (baslik, etiket, deger,
on, son, mansetler, metin, olaylar, sol, sag, kim) against the SOURCE PACK only — not your memory.
Flag: unsupported claims, wrong numbers/dates/names, quotes that are not verbatim in a source, headlines not present in
the sources, causal claims the sources do not make, and anything that presents speculation as fact.
Do NOT flag style. Do NOT flag claims that are clearly supported. A headline shortened without changing its meaning
is fine. A sentence from a Wikipedia article is Wikipedia's narration, not a quote of a person: flag it if the script
presents it as someone's spoken quote.
Return ONLY JSON: {"sorunlar": [{"sahne": index, "alan": field, "sorun": what is wrong, "duzeltme": a corrected
version that the sources support (or "REMOVE")}]}. Empty list if everything is supported."""

SISTEM_ONARIM = (
    SISTEM_YAZAR
    + """

YOUR TASK NOW: fix the listed problems by rewriting ONLY the affected scenes (you get each problem with its scene index
and the neighbouring scenes for context). Keep each rewritten scene's role in the story; replace an unsupported claim
with a supported fact, change a scene's type when the problem is a repeated type, or delete the scene when nothing
supported fits. Return ONLY JSON: {"duzeltmeler": [{"i": scene index, "sahne": full corrected scene object, or null to
delete}]}"""
)


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


def _gorsel_say(sahneler: list[dict]) -> Counter:
    return Counter(str(sh.get("gorsel")) for sh in sahneler if sh.get("gorsel"))


def _en_az_kullanilan(sahneler: list[dict], gorsel_sayisi: int, i: int) -> str | None:
    """i. sahne için en az kullanılmış görsel (komşu sahnelerinkinden farklı)."""
    say = _gorsel_say(sahneler)
    komsu = {str(sahneler[j].get("gorsel")) for j in (i - 1, i + 1) if 0 <= j < len(sahneler)}
    adaylar = [f"G{k}" for k in range(1, gorsel_sayisi + 1) if f"G{k}" not in komsu and say[f"G{k}"] < 2]
    return min(adaylar, key=lambda g: (say[g], int(g[1:]))) if adaylar else None


def yapi_onar(senaryo: dict, gorsel_sayisi: int) -> list[str]:
    """LLM onarımının düzeltemediği yapısal kuralları kodla düzeltir (yerinde). Dönüş: yapılanlar.

    11-20 GTA VI koşusu: dört onarım turundan sonra kalan sorunlar hep buydu (görsel 4-6 kez, durağan sahne 21/60,
    sayi.deger "<475", çift kapanış). Bunlar anlam değil biçim; kod doğru ve ücretsiz düzeltir."""
    s = senaryo.get("sahneler") or []
    yapilan: list[str] = []
    # 1. kapanis yalnız sonda; sonundaki fazlalık (kapanıştan sonra gelen sahneler) atılır
    son_k = max((i for i, sh in enumerate(s) if sh.get("tur") == "kapanis"), default=None)
    if son_k is not None:
        once = [sh for i, sh in enumerate(s) if not (sh.get("tur") == "kapanis" and i != son_k)]
        if len(once) != len(s) or son_k != len(s) - 1:
            yapilan.append("kapanış tekilleştirildi")
        s = [sh for sh in once if sh.get("tur") != "kapanis"] + [s[son_k]]
    # 2. sayi.deger sayı değilse rakamları ayıkla, yoksa ifade'ye çevir
    for i, sh in enumerate(s):
        if sh.get("tur") != "sayi":
            continue
        ham = str(sh.get("deger", ""))
        try:
            float(ham.replace(",", ""))
            continue
        except ValueError:
            pass
        rakam = re.search(r"\d[\d,]*(?:\.\d+)?", ham)
        if rakam:
            sh["deger"] = rakam.group(0).replace(",", "")
            yapilan.append(f"sahne {i}: sayi.deger '{ham}' → {sh['deger']}")
        else:
            s[i] = {**sh, "tur": "ifade", "metin": sh.get("etiket") or ham}
            yapilan.append(f"sahne {i}: sayısız sayi → ifade")
    # 2b. tek olaylı zaman çizgisi kareyi boş bırakıyor (11-20 GTA VI, "2023" tek düğüm): tarihli büyük ifadeye döner
    for i, sh in enumerate(s):
        if sh.get("tur") == "zaman" and len(sh.get("olaylar") or []) < 2:
            o = (sh.get("olaylar") or [{}])[0]
            s[i] = {**sh, "tur": "ifade", "metin": f"{o.get('tarih', '')}: {o.get('olay', '')}".strip(": ")}
            yapilan.append(f"sahne {i}: tek olaylı zaman → ifade")
    # 3. görsel en çok 2 kez
    for i, sh in enumerate(s):
        g = sh.get("gorsel")
        if g and _gorsel_say(s[: i + 1])[str(g)] > 2:
            yeni = _en_az_kullanilan(s, gorsel_sayisi, i)
            if yeni:
                sh["gorsel"] = yeni
            else:
                sh.pop("gorsel", None)
            yapilan.append(f"sahne {i}: görsel {g} → {yeni or 'yok'}")
            if sh.get("tur") == "foto" and not sh.get("gorsel"):
                s[i] = {**sh, "tur": "ifade", "metin": sh.get("baslik") or " ".join(sh.get("anlatim", "").split()[:8])}

    # 4. durağan sahne ≤ 1/3 ve ardışık aynı durağan tür yok: fazlası görselli foto'ya döner
    def _foto_yap(i: int) -> bool:
        sh = s[i]
        g = sh.get("gorsel") or _en_az_kullanilan(s, gorsel_sayisi, i)
        if not g:
            return False
        if i >= 2 and s[i - 1].get("tur") == "foto" == s[i - 2].get("tur"):
            return False
        if i + 2 < len(s) and s[i + 1].get("tur") == "foto" == s[i + 2].get("tur"):
            return False
        baslik = sh.get("metin") or sh.get("baslik") or ""
        if sh.get("tur") == "ikili":
            baslik = f"{sh.get('sol', {}).get('deger', '')} vs {sh.get('sag', {}).get('deger', '')}".strip(" vs")
        s[i] = {"tur": "foto", "anlatim": sh.get("anlatim", ""), "kaynak": sh.get("kaynak", []), "gorsel": g,
                "baslik": " ".join(str(baslik).split()[:7]), "vurgu": sh.get("vurgu", [])[:1] if sh.get("vurgu") else []}  # fmt: skip
        if sh.get("tur") == "alinti" and sh.get("kim"):
            s[i]["etiket"] = sh["kim"]
        return True

    for i in range(1, len(s)):
        if s[i].get("tur") in STATIK and s[i].get("tur") == s[i - 1].get("tur") and _foto_yap(i):
            yapilan.append(f"sahne {i}: ardışık {s[i - 1].get('tur')} → foto")
    for tur in ("ifade", "ikili", "alinti"):
        for i, sh in enumerate(s):
            if sum(1 for x in s if x.get("tur") in STATIK) <= len(s) / 3:
                break
            if sh.get("tur") == tur and _foto_yap(i):
                yapilan.append(f"sahne {i}: durağan {tur} → foto")
    senaryo["sahneler"] = s
    return yapilan


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
    for i, sh in enumerate(s[:-1]):
        if sh.get("tur") == "kapanis":
            hata.append(f"sahne {i}: kapanis yalnız son sahne olabilir (fazlasını sil)")
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
def _mesaj_kaynak(kaynak_metni: str, gorsel_metni: str) -> str:
    return f"=== SOURCE PACK ===\n{kaynak_metni}\n\n=== IMAGE LIST (real, licensed; use by id) ===\n{gorsel_metni}\n\n"


def iskelet(oturum: Oturum, konu: dict, kaynak_metni: str, gorsel_metni: str, model: str = "kimi-k3") -> dict:
    mesaj = (f"TOPIC: {konu['ad']}\nWHY IT IS TRENDING: {konu.get('neden', '')}\n"
             f"EDITOR'S SUGGESTED ANGLE (sharpen it): {konu.get('aci', '')}\n\n" + _mesaj_kaynak(kaynak_metni, gorsel_metni)
             + "Plan the video now.")  # fmt: skip
    return oturum.json_sor(SISTEM_ISKELET, mesaj, model=model, en_cok=12000, sicaklik=0.7)


def _ozet(sahneler: list[dict]) -> str:
    return "\n".join(f"{i}. [{sh.get('tur')}] {sh.get('anlatim', '')}" for i, sh in enumerate(sahneler))


def yaz(oturum: Oturum, konu: dict, kaynak_metni: str, gorsel_metni: str, model: str = "kimi-k3",
        dizin: Path | None = None, bolum_model: str = BOLUM_MODEL) -> dict:  # fmt: skip
    """İskelet (düşünerek, kısa) → kanca → her bölüm (düşünmeden, kısa JSON) → kapanış → kesit seçimi.
    Tek çağrıda ~60 sahnelik JSON 32k token'a sığmadı ve aboneliğin ~1,9 birimini yedi (11-20)."""
    plan_yol = dizin / "senaryo_iskelet.json" if dizin else None
    if plan_yol and plan_yol.exists():
        plan = json.loads(plan_yol.read_text(encoding="utf-8"))
    else:
        plan = iskelet(oturum, konu, kaynak_metni, gorsel_metni, model)
        if plan_yol:
            plan_yol.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    sahneler: list[dict] = []
    kaynak = _mesaj_kaynak(kaynak_metni, gorsel_metni)
    plan_metni = json.dumps({k: plan.get(k) for k in ("tez", "kanca", "bolumler", "kapanis")}, ensure_ascii=False)
    parcalar = [("HOOK (scenes before chapter 01; no chapter card)", "~110 words", plan.get("kanca", ""))]
    for b in plan.get("bolumler") or []:
        parcalar.append((f"CHAPTER {b.get('no')}: start with ONE 'bolum' scene (no {b.get('no')}, baslik "
                         f"\"{b.get('baslik')}\"), then its scenes", f"~{b.get('kelime', 250)} words in about {max(6, round(int(b.get('kelime', 250) or 250) / 21))} scenes", b.get("amac", "")))  # fmt: skip
    parcalar.append(
        ("CLOSING (last 2-3 scenes; the very last scene is 'kapanis')", "~60 words", plan.get("kapanis", ""))
    )
    for ad, hedef, amac in parcalar:
        mesaj = (kaynak + f"=== PLAN ===\n{plan_metni}\n\n=== SCENES SO FAR ===\n{_ozet(sahneler) or '(none)'}\n\n"
                 f"=== WRITE NOW ===\n{ad}. Target: {hedef}. Goal: {amac}")  # fmt: skip
        y = oturum.json_sor(SISTEM_BOLUM, mesaj, model=bolum_model, en_cok=9000, sicaklik=0.75, dusun=False)
        yeni = y.get("sahneler") if isinstance(y, dict) else y
        sahneler += [sh for sh in (yeni or []) if isinstance(sh, dict)]
        print(f"senaryo: {ad.split(':')[0].split('(')[0].strip()} -> toplam {len(sahneler)} sahne", flush=True)
    s = {k: plan.get(k) for k in ("tez", "baslik_adaylari", "kapak_metni", "kapak_gorsel", "aciklama")}
    s["sahneler"] = sahneler
    s["kesitler"] = kesit_sec(oturum, sahneler)
    return s


def kesit_sec(oturum: Oturum, sahneler: list[dict], model: str = BOLUM_MODEL) -> list[dict]:
    y = oturum.json_sor(
        SISTEM_KESIT, f"SCRIPT:\n{_ozet(sahneler)}", model=model, en_cok=3000, sicaklik=0.4, dusun=False
    )
    return list(y.get("kesitler") or []) if isinstance(y, dict) else []


def denetle(oturum: Oturum, senaryo: dict, kaynak_metni: str, model: str = "gemini-4-argon",
            gorsel_metni: str = "") -> list[dict]:  # fmt: skip
    """gorsel_metni: fotoğraf alt yazısı (etiket/baslik) gösterilen görselin Commons başlığına dayanabilir; denetçi
    görmezse "Toronto metrosundaki reklamlar" gibi doğru alt yazıları kaynaksız sayıyordu (11-20)."""
    sade = {"sahneler": [{k: v for k, v in sh.items() if k != "kaynak"} | {"i": i}
                         for i, sh in enumerate(senaryo.get("sahneler", []))]}  # fmt: skip
    gorsel = (f"\n\n=== IMAGE LIST (titles of the real photos; an etiket/baslik that only describes what its photo "
              f"shows is supported by the photo title) ===\n{gorsel_metni}") if gorsel_metni else ""  # fmt: skip
    mesaj = f"=== SOURCE PACK ===\n{kaynak_metni}{gorsel}\n\n=== SCRIPT ===\n{json.dumps(sade, ensure_ascii=False)}"
    y = oturum.json_sor(SISTEM_DENETCI, mesaj, model=model, en_cok=16000, sicaklik=0.0, dusun=False)
    return list(y.get("sorunlar", [])) if isinstance(y, dict) else []


def _sahne_no(metin: str) -> int | None:
    m = re.search(r"sahne (\d+)", metin)
    return int(m.group(1)) if m else None


def onar(oturum: Oturum, senaryo: dict, sorunlar: list, kaynak_metni: str, gorsel_metni: str,
         model: str = BOLUM_MODEL) -> dict:  # fmt: skip
    """Yalnız sorunlu sahneler yeniden yazılır (tam metni yeniden üretmek uzun ve pahalı)."""
    sahneler = senaryo.get("sahneler", [])
    ilgili: set[int] = set()
    for s_ in sorunlar:
        i = s_.get("sahne") if "sahne" in s_ else _sahne_no(str(s_.get("kod_kurali", "")))
        if isinstance(i, int) and 0 <= i < len(sahneler):
            ilgili.add(i)
    baglam = sorted({j for i in ilgili for j in (i - 1, i, i + 1) if 0 <= j < len(sahneler)})
    mesaj = (_mesaj_kaynak(kaynak_metni, gorsel_metni) + "=== FULL SCRIPT (index. [type] narration) ===\n"
             + _ozet(sahneler) + "\n\n=== SCENES IN CONTEXT (full objects) ===\n"
             + json.dumps({i: sahneler[i] for i in baglam}, ensure_ascii=False)
             + f"\n\n=== PROBLEMS ===\n{json.dumps(sorunlar, ensure_ascii=False, indent=1)}")  # fmt: skip
    y = oturum.json_sor(SISTEM_ONARIM, mesaj, model=model, en_cok=9000, sicaklik=0.3, dusun=False)
    duz = (y.get("duzeltmeler") or []) if isinstance(y, dict) else []
    yeni = list(sahneler)
    silinen = set()
    for d in duz:
        try:
            i = int(d.get("i"))
        except (TypeError, ValueError, AttributeError):
            continue
        if not 0 <= i < len(yeni):
            continue
        if d.get("sahne") is None:
            silinen.add(i)
        elif isinstance(d["sahne"], dict):
            yeni[i] = d["sahne"]
    return {**senaryo, "sahneler": [sh for i, sh in enumerate(yeni) if i not in silinen]}


def uret(oturum: Oturum, konu: dict, kaynak_metni: str, gorsel_metni: str, gorsel_sayisi: int,
         tur_sayisi: int = 4, kayit: list | None = None, dizin: Path | None = None) -> dict:  # fmt: skip
    """Yaz → (kod kapıları + olgu denetimi) → sahne onarımı döngüsü. Turlar bitince hâlâ desteklenmeyen sahne çıkarılır
    (son çare); kod kapısı yine geçmezse çağıran düşürür."""
    kayit = kayit if kayit is not None else []
    print("senaryo: yazılıyor", flush=True)
    taslak = dizin / "senaryo_taslak.json" if dizin else None
    son_hal = dizin / "senaryo_son.json" if dizin else None
    if son_hal and son_hal.exists():
        s = json.loads(son_hal.read_text(encoding="utf-8"))
    elif taslak and taslak.exists():
        s = json.loads(taslak.read_text(encoding="utf-8"))
    else:
        s = yaz(oturum, konu, kaynak_metni, gorsel_metni, dizin=dizin)
        if taslak:
            taslak.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    for tur in range(tur_sayisi):
        if duz := yapi_onar(s, gorsel_sayisi):
            print(f"senaryo yapı onarımı: {len(duz)} değişiklik", flush=True)
        if son_hal:
            son_hal.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
        kod = yapi_kapisi(s, gorsel_sayisi) + sayi_kapisi(s, kaynak_metni)
        olgu = denetle(oturum, s, kaynak_metni, gorsel_metni=gorsel_metni)
        kayit.append({"tur": tur, "kod": kod, "olgu": olgu, "sahne": len(s.get("sahneler", []))})
        if dizin:  # her tur diske: koşu kesilse de sorunlar okunabilsin
            (dizin / "senaryo_turlar.json").write_text(
                json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8"
            )
        print(f"senaryo tur {tur}: {len(s.get('sahneler', []))} sahne, kod {len(kod)}, olgu {len(olgu)}", flush=True)
        if not kod and not olgu:
            return s
        s = onar(oturum, s, [{"kod_kurali": k} for k in kod] + olgu, kaynak_metni, gorsel_metni)
        if any("kesit" in k for k in kod) or len(s.get("kesitler") or []) < 3:
            s["kesitler"] = kesit_sec(oturum, s["sahneler"])
    olgu = denetle(oturum, s, kaynak_metni, gorsel_metni=gorsel_metni)
    korunan = {"bolum", "kapanis"}
    cikar = {int(o["sahne"]) for o in olgu if str(o.get("sahne", "")).isdigit()}
    cikar = {i for i in cikar if 0 < i < len(s.get("sahneler", [])) and s["sahneler"][i].get("tur") not in korunan}
    if cikar:
        s["sahneler"] = [sh for i, sh in enumerate(s["sahneler"]) if i not in cikar]
        s["kesitler"] = kesit_sec(oturum, s["sahneler"])
    yapi_onar(s, gorsel_sayisi)
    if son_hal:
        son_hal.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    kod = yapi_kapisi(s, gorsel_sayisi) + sayi_kapisi(s, kaynak_metni)
    kayit.append({"tur": tur_sayisi, "kod": kod, "olgu": olgu, "cikarilan": sorted(cikar),
                  "sahne": len(s.get("sahneler", []))})  # fmt: skip
    print(f"senaryo son: {len(cikar)} sahne çıkarıldı, kod {len(kod)}", flush=True)
    return s
