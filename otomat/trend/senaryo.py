"""Trend açıklayıcı senaryosu: kaynak paketi → yazar modeli → kod kapıları → olgu denetçisi → onarım.

Kurallar nereden geliyor (docs/arastirma/14-trend-kanali.md):
- YPP "inauthentic/reused content" (support 1311392): haber akışını seslendirmek uygun değil; her videonun kendi tezi
  (özgün açı) olur ve bölüm sırası konuya göre değişir. Yazara "tez" zorunlu alan olarak verilir.
- İlk 5-10 sn vaadi verir (YouTube blog 2026-07-14); kanal tanıtımı yok.
- Soru ile biten başlık ortalamanın altında (vidIQ 2026); somut hikâye çerçevesi.
- HyperFrames film.md: sahne başına ~19 kelime (en çok 30), görünen her parça söylendiği an gelir.
- vox-explainer: statik sahne ≤ 1/3, ardışık iki sahne aynı türde olmaz.
- open-edit: ekrandaki her sayı kaynakta geçer (kod kapısı `sayi_kapisi`).
- 11-20 izleyici geri bildirimi ("dümdüz metin anlatıyor", "düz renk zeminde yazılar sıkıcı"): yazar hikâye anlatıcısı
  gibi yazar (karakter, an, gerilim, açık döngü, ritim), her sahneye anlatıcı için `ton` notu verir; her sahnenin
  altında görsel olur (kod atar, `gorsel_ata`), bölümler müzik ruh hali taşır (`MUZIK_RUHLARI`).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from otomat.trend.llm import Oturum

TURLER = ("foto", "manset", "sayi", "alinti", "zaman", "bolum", "ikili", "ifade", "kapanis", "harita")
STATIK = ("ifade", "ikili", "alinti")  # tek başına poster gibi duran türler
STATIK_PAY = 0.25  # 11-26: Bond videosunda 55 sahnenin 36'sı yazılı kart, 19 fotoğrafın 14'ü başlıklı ("slayt" hissi)
BASLIKLI_FOTO_PAY = 0.34  # fotoğraf sahnelerinin en çok üçte biri ekranda başlık taşır; kalanı resim + ses
KELIME_HEDEF = (650, 1350)  # ~6-9 dk (Chatterbox ~2,4 kelime/sn + aralar)
BOLUM_MODEL = "glm-5.3"  # bölüm sahneleri: kimi-k3 çağrı başı ~0,07 pay, glm-5.3 ~0,007 (11-20 ölçümü)
SAHNE_KELIME_EN_COK = 40  # 11-26: bağlı konuşma dili (12-25 kelimelik cümleler) 34'ü aşıyordu
GORSEL_EN_COK = 3  # her sahnenin altında görsel var (11-20); havuz ~36 görsel, komşu sahnede tekrar yok
KELIME_GORSEL_BASI = 75  # süre görsel havuzuna göre: 11-27 Miss Universe 11 görselle 1452 kelime (72 sahne) yazıldı,
#                          bir fotoğraf 9 kez döndü. Fotoğraf başına ~3 kullanım + stok ~%20 → görsel başına ~75 kelime.


def kelime_hedefi(gorsel_sayisi: int) -> tuple[int, int]:
    """Toplam anlatım kelimesi (alt, üst). Üst sınır havuzla büyür (en çok KELIME_HEDEF[1]); alt sınır üstün ~%65'i.
    Kısa ama tekrarsız video, aynı fotoğrafa dönen uzun videodan iyidir (izleyici tekrarı ilk dakikalarda görür)."""
    ust = max(700, min(KELIME_HEDEF[1], KELIME_GORSEL_BASI * gorsel_sayisi))
    return max(550, round(ust * 0.65)), ust


MUZIK_RUHLARI = ("merak", "gerilim", "dram", "umut", "enerji", "sakin", "karanlik")
YASAK_IFADE = ("unlock", "seamless", "supercharge", "game-changer", "game changer", "revolutionize", "effortless",
               "delve", "tapestry", "in today's fast-paced", "buckle up", "let's dive in", "dive into",
               "without further ado", "smash that", "don't forget to subscribe", "in conclusion",
               # 11-26: "anlatım gerçek insan gibi olmalı" — YouTube anlatıcı kalıpları senaryoyu yapay gösteriyor
               "here's the thing", "here's the part", "here's what", "hold that thought", "nobody's talking about",
               "nobody is talking about", "let that sink in", "the real story", "changes everything",
               "nobody saw it coming", "little did", "fast forward", "spoiler", "plot twist", "make no mistake",
               "the answer might surprise you", "the answer may surprise you", "stay with me", "but wait",
               "it's not just", "this isn't just", "more than just", "at the end of the day",
               "in a world where", "and that's when", "it all started",
               "here's where", "took a turn", "nobody expected", "gets interesting")  # fmt: skip
# 11-27: sabit ifade listesi karşıtlık kalıbını yakalamıyordu ("the real question isn't whether a mom can win a beauty
# pageant, it's whether the pageant deserves her"); K-46 "X değil Y" yasağı biçim olarak da denetlenir
YASAK_KALIP = (
    re.compile(r"\bthe real (?:question|story|point|reason)\b"),
    re.compile(
        r"\b(?:isn't|wasn't|is not|was not|aren't|weren't)\s+(?:really\s+)?(?:whether|about|that)\b"
        r"[^.?!]{0,90}?[,;—–-]\s*(?:it's|it is|it was|they're|but)\b"
    ),  # fmt: skip
    re.compile(r"\bnot because\b[^.?!]{0,90}\bbut because\b"),
    re.compile(r"\bless about\b[^.?!]{0,70}\bmore about\b"),
    # 11-27 A/B: "This wasn't a side project, because…", "The timing wasn't random, because…"
    re.compile(r"\b(?:wasn't|isn't|was not|is not)\b[^.?!,]{0,40},\s*because\b"),
    # slogan kapanış: "and that gap is the story", "that's the story worth telling"
    re.compile(r"\b(?:that|this|which)(?:'s| is)?(?: \w+)? (?:is )?the story\b"),
    re.compile(r"\b(?:worth|deserves) (?:telling|a closer look)\b"),
)
BAGLAC_BAS = re.compile(r"^\s*(?:so|and|but|because|which)\b", re.I)
BAGLAC_PAY = 0.22  # sahnelerin en çok ~beşte biri bağlaçla başlar (11-27 A/B: 43 sahnenin 17'si)


def ritim_kapisi(sahneler: list[dict]) -> list[str]:
    """Bağlaç ritmi: bağlaçla başlayan sahne payı, art arda aynı başlangıç ve "because" sıklığı. Yazara "cümleler
    bir öncekine bağlı" denince (K-46) model bunu "So…/And…/because…" zinciriyle yaptı; insan kulağı bu ritmi
    hemen AI diye duyuyor."""
    hata: list[str] = []
    bas = [(m.group(0).strip().lower() if (m := BAGLAC_BAS.match(sh.get("anlatim", ""))) else "") for sh in sahneler]
    hak = int(len(sahneler) * BAGLAC_PAY)
    sayac = 0
    for i, b in enumerate(bas):
        if not b:
            continue
        sayac += 1
        if i > 0 and bas[i - 1]:
            hata.append(f"ritim: sahne {i}: art arda iki sahne bağlaçla başlıyor ('{b}'); bu cümleyi bağlaçsız başlat")
        elif sayac > hak:
            hata.append(
                f"ritim: sahne {i}: bağlaçla başlayan sahne fazla ({sayac}/{len(sahneler)}); '{b}' olmadan başlat"
            )
    toplam = sum(len(sh.get("anlatim", "").split()) for sh in sahneler)
    because = [i for i, sh in enumerate(sahneler) if re.search(r"\bbecause\b", sh.get("anlatim", ""), re.I)]
    hak_b = max(3, toplam // 220)
    for i in because[hak_b:]:
        hata.append(
            f"ritim: sahne {i}: 'because' videoda {len(because)} kez (en çok {hak_b}); nedeni başka biçimde söyle"
        )
    return hata


SISTEM_YAZAR = """You are the head writer of a fast, smart YouTube explainer channel about whatever the world is talking
about right now. Faceless, narrated, motion-graphics heavy. Viewers arrive curious ("why is everyone talking about X?")
and must leave understanding it better than their friends do.

VOICE: write exactly what a real, thoughtful person would SAY out loud to one smart friend who asked "wait, what's
going on with X?". Not a newsreader, not a hype YouTuber, not a trailer. Listen to how good hosts actually talk (Johnny
Harris, Wendover, ColdFusion): plain words, full thoughts that flow from one sentence into the next, a scene set with
concrete detail, people with names, and the occasional aside ("which, to be fair, is a lot of money"). Our last videos
were rejected because the narration sounded written by AI: every line a punchline, slogans, YouTube catchphrases,
dramatic fragments. Fix that:
- Story over summary: each chapter follows a person or group who wants something, hits an obstacle, and turns.
- Connected speech: most sentences are 12-25 words and grow out of the previous one through CONTENT (the next line
  picks up a name, an object, a number or a consequence from the last), not through connective words. A scene may
  end mid-thought and the next scene finishes it. Starting a scene with "So", "And", "But", "Because" or "Which" is
  fine now and then (about one scene in five), never twice in a row. "because" at most once per chapter; never the
  "X wasn't random, because..." / "this wasn't a side project, because..." construction. Say a name once and move on
  (never "...won Miss Universe. Her name is Jennifer Barreto"). At most ONE 2-4 word fragment per chapter, and only
  where a person would really pause to land a point.
- No slogans and no trailer voice: never "X. Y. Z." triplets, never "It's not X, it's Y", never one-line drama
  ("Then the screaming started."), never announce that something is surprising or important — just say the fact and
  let it work. No clichés: "here's the thing", "hold that thought", "the real story", "nobody saw it coming", "changes
  everything", "but wait", "let that sink in", "fast forward", "enter X", "it's not just".
- Talk to the viewer: "you", contractions (it's, didn't, they'd), an honest question now and then, mild humour when
  the facts are funny. Causality, not lists.
- Open loops the natural way ("we'll come back to that number") and pay them off.
- Make numbers feel physical with comparisons built only from numbers in the sources.
- End each chapter with a plain question or turn that leads into the next, not a cliffhanger slogan.
Clear spoken English, trustworthy, calm confidence. Real numbers only from the sources. No filler, no channel intro.

HARD RULES
1. Every factual claim must come from the SOURCE PACK. Cite source ids per scene in "kaynak". If the sources don't say
   it, don't say it. Never invent numbers, dates, quotes, names. Quotes must be verbatim from a source.
2. You must have an original angle: a one-sentence THESIS that reframes the story (a tension, a surprising cause, what
   it reveals about something bigger). The video argues and pays off this thesis; it is not a news readout.
3. The first scene (hook) states the promise within ~8 seconds: what happened + why it is bigger than it looks.
   Never start with "In this video", a greeting, or the channel name.
4. Re-hook every ~90 seconds with a new question or turn, said plainly (e.g. "So why would Amazon take that risk?").
5. Each scene's narration ("anlatim") is 8-30 words: one beat of the story, usually one or two connected
   sentences. Scenes of type sayi, ikili, ifade and alinti hold one graphic, so their narration is at most 20 words.
   Total narration follows the plan's word targets (the video is as long as its real pictures allow, no longer).
   Every scene also has "ton": a 3-10 word delivery note for the narrator (how to
   SAY it: e.g. "hushed, building suspense", "wry, amused", "fast and urgent", "slow, let it land", "warm, curious").
   Vary it with the story; most scenes are natural and conversational, the big turns get the strong notes.
6. Scene types (field "tur") and their fields — use the type that SHOWS the line, vary them, never the same type twice
   in a row (except foto: at most 3 foto in a row). Think like a documentary editor, not a slide designer: at least
   HALF of all scenes are "foto" (picture + voice), and most foto scenes have NO headline: the picture and the narration
   carry them. Graphic cards (sayi, ifade, ikili, alinti, zaman) are spice for the moments that need them:
   ifade+ikili+alinti together at most one quarter of scenes, at most 2 "sayi" per chapter.
   - "foto": a real photo from the IMAGE LIST. fields: gorsel (image id like "G3"), baslik (optional on-screen headline,
     3-7 words, NOT a copy of the narration; only on about one foto scene in three), vurgu (list of 1 word from
     baslik to highlight), etiket (optional lower-third naming who/what is shown, 2-5 words, only words that are in
     the image's title), ipucu (word from the narration when the headline appears)
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
8. Use images from the IMAGE LIST only by id. EVERY scene except harita gets a "gorsel" (it moves behind the
   graphics; there are no plain colour backgrounds). Use each image at most 3 times, never in two neighbouring scenes.
   Prefer images that show what the line says.
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
   (2 sentences), "kaynaklar": [source ids to use], "kelime": target narration words for the chapter,
   "muzik": the music mood under this chapter, one of merak|gerilim|dram|umut|enerji|sakin|karanlik}],   (3-5 chapters;
   hook ~110 words, chapters together ~950-1150 words, closing ~60 words)
 "kanca_muzik": music mood under the hook (same options), "kapanis_muzik": music mood under the ending,
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
naturally from the previous scene (no repeated scene type at the boundary). Hit the target word count for this part.
NEVER restate a fact, number or date the viewer already heard in the scenes written so far: a person who just told
you "17 million lines" doesn't say it again two minutes later. If you need it, call back in at most 5 words ("all
those lines of code") and add something new. A "sayi" or "ifade" card shows the line it is spoken on: its narration
says that number or line for the FIRST time, never a scene before or after it. Return ONLY JSON: {"sahneler": [{"tur": str, "anlatim": str, "ton": str, "kaynak": [ids], "gorsel": "G..",
...type fields}]}"""
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
Photo captions ("etiket" of "foto" scenes; in "sayi" scenes etiket labels the number instead) describe the photo of
that scene ("gorsel" id): every name, year, role, film or event in a caption must appear in that image's title in the
IMAGE LIST (e.g. "Pattinson as Batman, 2022" over an image titled
"Robert Pattinson-65808" is unsupported: fix it to what the title says, e.g. "Robert Pattinson").
Also flag REPEATS (the one non-factual check, 11-26: "17 million lines" was said three times): a scene whose narration
restates a fact, number or date already said in an EARLIER scene, beyond a short callback of at most 5 words. Use
alan "anlatim", sorun "repeat of scene N", and a duzeltme that keeps the scene's new information without the repeat.
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
        bag[kimlik] = f'{h.yayinci}: "{h.baslik}" ({h.zaman:%Y-%m-%d})'  # Google News bağlantısı yönlendirme, okunmaz
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


def _en_az_kullanilan(sahneler: list[dict], gorsel_sayisi: int, i: int, sinir: int = GORSEL_EN_COK) -> str | None:
    """i. sahne için en az kullanılmış görsel (komşu sahnelerinkinden farklı)."""
    say = _gorsel_say(sahneler)
    komsu = {str(sahneler[j].get("gorsel")) for j in (i - 1, i + 1) if 0 <= j < len(sahneler)}
    adaylar = [f"G{k}" for k in range(1, gorsel_sayisi + 1) if f"G{k}" not in komsu and say[f"G{k}"] < sinir]
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
    # 3. görsel en çok GORSEL_EN_COK kez ve komşu sahnede aynı görsel yok
    for i, sh in enumerate(s):
        g = sh.get("gorsel")
        komsu = i > 0 and g and str(s[i - 1].get("gorsel")) == str(g)
        if g and (_gorsel_say(s[: i + 1])[str(g)] > GORSEL_EN_COK or komsu):
            yeni = _en_az_kullanilan(s, gorsel_sayisi, i)
            if yeni:
                sh["gorsel"] = yeni
            else:
                sh.pop("gorsel", None)
            yapilan.append(f"sahne {i}: görsel {g} → {yeni or 'yok'}")
            # görselsiz fotoğraf yalnız kendi başlığı varsa ifade kartına döner; anlatımın ilk kelimeleri ekrana yarım
            # cümle olarak çıkıyordu. Başlıksızsa görselsiz kalır, stok video aşaması doldurur.
            if sh.get("tur") == "foto" and not sh.get("gorsel") and sh.get("baslik"):
                s[i] = {**sh, "tur": "ifade", "metin": sh["baslik"]}

    # 4. durağan sahne ≤ 1/3 ve ardışık aynı durağan tür yok: fazlası görselli foto'ya döner
    def _foto_yap(i: int, zorla: bool = False) -> bool:
        sh = s[i]
        # 11-26 Riemann: süzgeç sonrası 16 görselin hepsi 3 kez kullanılmıştı, durağan kart düşürülemiyordu. 11-27:
        # 4. kullanım son çaresi kalktı (Miss Universe'te bir fotoğraf 9 kez döndü); havuz biterse sahne görselsiz
        # fotoğraf olur, stok video aşaması önce onları doldurur.
        g = sh.get("gorsel") or _en_az_kullanilan(s, gorsel_sayisi, i)
        # en çok üç fotoğraf art arda (11-26: sahnelerin yarısı fotoğraf hedefi; belgeselde ardışık fotoğraf doğal,
        # dördüncüsü tekdüzeleşiyor)
        tur = [sh_.get("tur") for sh_ in s]
        tur[i] = "foto"
        for bas in range(max(0, i - 3), i + 1):
            if not zorla and bas + 4 <= len(tur) and all(t == "foto" for t in tur[bas : bas + 4]):
                return False
        baslik = sh.get("metin") or sh.get("baslik") or sh.get("etiket") or ""
        if sh.get("tur") == "sayi" and sh.get("deger"):
            from otomat.trend.kurgu import kisalt

            try:
                d, ek = kisalt(float(str(sh["deger"]).replace(",", "")), sh.get("son") or "")
                d = f"{d:,.0f}" if float(d).is_integer() else f"{d}"
            except ValueError:
                d, ek = sh["deger"], sh.get("son") or ""
            baslik = f"{sh.get('on') or ''}{d}{ek} {sh.get('etiket', '')}"
        if sh.get("tur") == "ikili":
            baslik = f"{sh.get('sol', {}).get('deger', '')} vs {sh.get('sag', {}).get('deger', '')}".strip(" vs")
        if sh.get("tur") not in ("sayi", "ikili"):  # 11-26: dönüşen her kart başlıklı fotoğraf olunca yine yazı yağdı
            baslik = ""
        s[i] = {"tur": "foto", "anlatim": sh.get("anlatim", ""), "kaynak": sh.get("kaynak", []), "gorsel": g,
                "baslik": " ".join(str(baslik).split()[:7]), "vurgu": sh.get("vurgu", [])[:1] if sh.get("vurgu") else []}  # fmt: skip
        if sh.get("tur") == "alinti" and sh.get("kim"):
            s[i]["etiket"] = sh["kim"]
        if not g:
            s[i].pop("gorsel")
        return True

    # kare 0 oynatıcı önizlemesidir, boş olamaz (11-20 Anthropic: açılış sayi sahnesi boş kırmızıyla başladı) → foto
    if s and s[0].get("tur") != "foto" and _foto_yap(0):
        yapilan.append(f"sahne 0: açılış {s[0].get('tur')} → foto")
    # 2'den küçük "sayı" anlamsız ("1 — Stanford physics degree") → fotoğraflı başlık
    for i, sh in enumerate(s):
        if sh.get("tur") == "sayi":
            try:
                kucuk = abs(float(str(sh.get("deger", "0")).replace(",", ""))) < 2
            except ValueError:
                kucuk = False
            if kucuk and _foto_yap(i):
                yapilan.append(f"sahne {i}: anlamsız küçük sayı → foto")
    for i in range(1, len(s)):
        tur = s[i].get("tur")
        if tur not in ("foto", "bolum", "kapanis") and tur == s[i - 1].get("tur") and _foto_yap(i, zorla=True):
            yapilan.append(f"sahne {i}: ardışık {s[i - 1].get('tur')} → foto")
    for tur in ("ifade", "ikili", "alinti"):
        for i, sh in enumerate(s):
            if sum(1 for x in s if x.get("tur") in STATIK) <= len(s) * STATIK_PAY:
                break
            if sh.get("tur") == tur and _foto_yap(i):
                yapilan.append(f"sahne {i}: durağan {tur} → foto")
    # 4b. başlıklı fotoğraf en çok BASLIKLI_FOTO_PAY: fazlasının başlığı düşer (bölüm başındaki ilk foto ve sayı
    # taşıyan başlık korunur). Alt yazı (etiket) kişi ilk göründüğünde bilgi verir; aynı etiket ikinci kez yazılmaz.
    fotolar = [i for i, sh in enumerate(s) if sh.get("tur") == "foto"]
    baslikli = [i for i in fotolar if (s[i].get("baslik") or "").strip()]
    hak = int(len(fotolar) * BASLIKLI_FOTO_PAY)
    if len(baslikli) > hak:

        def _oncelik(i: int) -> tuple:
            sayi_var = bool(re.search(r"\d", s[i].get("baslik", "")))
            bolum_basi = i > 0 and s[i - 1].get("tur") == "bolum"
            return (not sayi_var, not bolum_basi, i)

        tut = set(sorted(baslikli, key=_oncelik)[:hak])
        for i in baslikli:
            if i not in tut:
                s[i]["baslik"], s[i]["vurgu"] = "", []
        yapilan.append(f"başlıklı fotoğraf {len(baslikli)} → {hak}")
    goruldu: set[str] = set()
    for i in fotolar:
        et = (s[i].get("etiket") or "").strip().lower()
        if et and et in goruldu:
            s[i]["etiket"] = ""
        goruldu.add(et)
    # 5. görselsiz sahne kalmasın (harita kendi uydu görüntüsünü taşır): düz renk zemin yok (11-20 geri bildirimi)
    for i, sh in enumerate(s):
        if sh.get("tur") != "harita" and not sh.get("gorsel"):
            g = _en_az_kullanilan(s, gorsel_sayisi, i)
            if g:
                sh["gorsel"] = g
                yapilan.append(f"sahne {i}: görsel atandı {g}")
    # 6. "So"/"And" ile başlayan fazla sahne: bağlaç kod tarafından atılır (anlam değişmez); "but/because/which"
    # anlam taşır, onarım turuna kalır
    for h in ritim_kapisi(s):
        m = re.match(r"ritim: sahne (\d+): (?:art arda|bağlaçla)", h)
        if m and (i := int(m.group(1))) < len(s):
            once = s[i].get("anlatim", "")
            sonra = _baglac_at(once)
            if sonra != once:
                s[i]["anlatim"] = sonra
                yapilan.append(f"sahne {i}: baştaki bağlaç atıldı")
    senaryo["sahneler"] = s
    return yapilan


def _baglac_at(metin: str) -> str:
    """Baştaki "So"/"And" (ve ardından gelen virgül) atılır, ilk harf büyür; başka bağlaca dokunmaz."""
    yeni = re.sub(r"^\s*(?:so|and)\b,?\s*", "", metin, count=1, flags=re.I)
    return yeni[:1].upper() + yeni[1:] if yeni != metin and yeni else metin


def yapi_kapisi(senaryo: dict, gorsel_sayisi: int, butce: int | None = None) -> list[str]:
    """Biçim kuralları: türler, alanlar, kelime sınırları, çeşitlilik, görsel kimlikleri, yasak ifadeler."""
    s = senaryo.get("sahneler") or []
    hata = []
    if len(s) < 25:
        hata.append(f"sahne sayısı {len(s)} (< 25)")
    toplam = sum(len(sh.get("anlatim", "").split()) for sh in s)
    alt, ust = kelime_hedefi(butce or gorsel_sayisi)  # bütçe: etkin görsel (benzer grup ~1,5)
    if not alt <= toplam <= ust + 150:
        hata.append(f"toplam anlatım {toplam} kelime (hedef {alt}-{ust}; görsel havuzu {gorsel_sayisi})")
    if not senaryo.get("tez"):
        hata.append("tez yok")
    gorsel_kullanim: Counter = Counter()
    for i, sh in enumerate(s):
        tur = sh.get("tur")
        if tur not in TURLER:
            hata.append(f"sahne {i}: bilinmeyen tür {tur}")
            continue
        n = len(sh.get("anlatim", "").split())
        sinir = 26 if tur in ("sayi", "ikili", "ifade", "alinti") else (16 if tur == "bolum" else SAHNE_KELIME_EN_COK)
        if not 1 <= n <= sinir:
            hata.append(f"sahne {i} ({tur}): anlatım {n} kelime (en çok {sinir})")
        if i and tur == s[i - 1].get("tur") and tur not in ("foto",):
            hata.append(f"sahne {i}: bir öncekiyle aynı tür ({tur})")
        # görselsiz fotoğraf hata değil (11-26 Miss Universe: süzgeç 8 görsel bıraktı): stok video öncelikle onları
        # doldurur, kalanı kapak görselinin koyu halini alır (uretim.plan_kur)
        gerek = {"foto": [], "manset": ["mansetler"], "sayi": ["deger", "etiket"], "alinti": ["metin", "kim"],
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
        # kıvrık kesme işareti (’) düz olana çevrilir: "here’s the thing" listeden kaçıyordu (11-27)
        metin = (sh.get("anlatim", "") + " " + _ekran_metni(sh)).lower().replace("’", "'").replace("‘", "'")
        for y in YASAK_IFADE:
            if y in metin:
                hata.append(f"sahne {i}: yasak ifade '{y}'")
        for k in YASAK_KALIP:
            if m := k.search(metin):
                hata.append(
                    f"kalıp: sahne {i}: karşıtlık kalıbı '{m.group(0)[:60]}' (düz söyle: asıl iddiayı doğrudan yaz)"
                )
    for g, n in gorsel_kullanim.items():
        if n > GORSEL_EN_COK:  # süre havuza göre ayarlandığı için son çare 4. kullanım kalktı (11-27)
            hata.append(f"görsel {g} {n} kez kullanılmış (en çok {GORSEL_EN_COK})")
    for i, sh in enumerate(s[:-1]):
        if sh.get("tur") == "kapanis":
            hata.append(f"sahne {i}: kapanis yalnız son sahne olabilir (fazlasını sil)")
    if s and s[-1].get("tur") != "kapanis":
        hata.append("son sahne kapanis değil")
    hata += ritim_kapisi(s)
    statik = sum(1 for sh in s if sh.get("tur") in STATIK)
    if s and statik > len(s) * STATIK_PAY:
        hata.append(f"statik sahne {statik}/{len(s)} (en çok dörtte bir)")
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


KANCA_KAPANIS = 170  # kanca ~110 + kapanış ~60 kelime


def iskelet_sistemi(ust: int = KELIME_HEDEF[1]) -> str:
    """Bölümlerin toplam kelimesi süre bütçesinden (`kelime_hedefi`); kısa videoda 3-4 bölüm."""
    b = ust - KANCA_KAPANIS - 30
    s = SISTEM_ISKELET.replace("chapters together ~950-1150 words", f"chapters together ~{b - 200}-{b} words")
    return s.replace("(3-5 chapters;", "(3-4 chapters;") if ust < 1000 else s


def bolum_kelimeleri(plan: dict, ust: int) -> None:
    """Model bütçeyi aşan bölüm kelimeleri verirse orantılı küçültür (yerinde; en az 120 kelime/bölüm)."""
    bolumler = [b for b in plan.get("bolumler") or [] if isinstance(b, dict)]
    toplam = sum(int(b.get("kelime") or 250) for b in bolumler)
    butce = ust - KANCA_KAPANIS - 30
    if bolumler and toplam > butce:
        for b in bolumler:
            b["kelime"] = max(120, round(int(b.get("kelime") or 250) * butce / toplam))


def iskelet(oturum: Oturum, konu: dict, kaynak_metni: str, gorsel_metni: str, model: str = "kimi-k3",
            ust: int = KELIME_HEDEF[1]) -> dict:  # fmt: skip
    mesaj = (f"TOPIC: {konu['ad']}\nWHY IT IS TRENDING: {konu.get('neden', '')}\n"
             f"EDITOR'S SUGGESTED ANGLE (sharpen it): {konu.get('aci', '')}\n\n" + _mesaj_kaynak(kaynak_metni, gorsel_metni)
             + "Plan the video now.")  # fmt: skip
    plan = oturum.json_sor(iskelet_sistemi(ust), mesaj, model=model, en_cok=12000, sicaklik=0.7)
    if isinstance(plan, dict):
        bolum_kelimeleri(plan, ust)
    return plan


def _ozet(sahneler: list[dict]) -> str:
    return "\n".join(f"{i}. [{sh.get('tur')}] {sh.get('anlatim', '')}" for i, sh in enumerate(sahneler))


def yaz(oturum: Oturum, konu: dict, kaynak_metni: str, gorsel_metni: str, model: str = "kimi-k3",
        dizin: Path | None = None, bolum_model: str = BOLUM_MODEL, ust: int = KELIME_HEDEF[1]) -> dict:  # fmt: skip
    """İskelet (düşünerek, kısa) → kanca → her bölüm (düşünmeden, kısa JSON) → kapanış → kesit seçimi.
    Tek çağrıda ~60 sahnelik JSON 32k token'a sığmadı ve aboneliğin ~1,9 birimini yedi (11-20)."""
    plan_yol = dizin / "senaryo_iskelet.json" if dizin else None
    if plan_yol and plan_yol.exists():
        plan = json.loads(plan_yol.read_text(encoding="utf-8"))
    else:
        plan = iskelet(oturum, konu, kaynak_metni, gorsel_metni, model, ust=ust)
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
    s["muzik_plani"] = {"kanca": plan.get("kanca_muzik"), "bolumler": [b.get("muzik") for b in plan.get("bolumler") or []],
                        "kapanis": plan.get("kapanis_muzik")}  # fmt: skip
    s["kesitler"] = kesit_sec(oturum, sahneler)
    return s


def kesit_gecerli(k: dict, sahneler: list[dict]) -> bool:
    """Ardışık sahneler, 60-150 kelime (25-55 sn), bölüm kartıyla başlamıyor."""
    try:
        idx = [int(x) for x in k.get("sahneler") or []]
    except (TypeError, ValueError):
        return False
    if not idx or idx != list(range(idx[0], idx[0] + len(idx))) or not 0 <= idx[0] or idx[-1] >= len(sahneler):
        return False
    kelime = sum(len(sahneler[i].get("anlatim", "").split()) for i in idx)
    return 60 <= kelime <= 150 and sahneler[idx[0]].get("tur") != "bolum" and bool(k.get("kanca"))


def kesit_kirp(k: dict, sahneler: list[dict], hedef: int = 110, tavan: int = 150) -> dict:
    """Model kelime sınırını aşan koşu seçerse (11-20 Bond: 212-259 kelime) baştaki bölüm kartı atılır, koşu ~110
    kelimeye kadar kısaltılır. Geçersiz girdi olduğu gibi döner (kesit_gecerli eler)."""
    try:
        idx = [int(x) for x in k.get("sahneler") or []]
    except (TypeError, ValueError):
        return k
    while idx and 0 <= idx[0] < len(sahneler) and sahneler[idx[0]].get("tur") == "bolum":
        idx = idx[1:]
    out, n = [], 0
    for i in idx:
        if not 0 <= i < len(sahneler):
            break
        w = len(sahneler[i].get("anlatim", "").split())
        if out and (n >= hedef or n + w > tavan):
            break
        out.append(i)
        n += w
    return {**k, "sahneler": out}


def kesit_sec(oturum: Oturum, sahneler: list[dict], model: str = BOLUM_MODEL, deneme: int = 3) -> list[dict]:
    """3 geçerli, çakışmayan kesit toplanana dek en çok `deneme` çağrı (11-20 Bond: tek çağrı 1 kesit döndürdü,
    11 sahnelik 150+ kelimelik bir koşu)."""
    secilen: list[dict] = []
    sayili = "\n".join(f"{i}. [{sh.get('tur')}, {len(sh.get('anlatim', '').split())} words] {sh.get('anlatim', '')}"
                       for i, sh in enumerate(sahneler))  # fmt: skip
    for d in range(deneme):
        dolu = {i for k in secilen for i in k["sahneler"]}
        not_ = "" if not secilen else (f"\n\nAlready chosen (do not overlap): "
                                       f"{[k['sahneler'] for k in secilen]}. Pick {3 - len(secilen)} more.")  # fmt: skip
        y = oturum.json_sor(SISTEM_KESIT, f"SCRIPT (word count per scene in brackets):\n{sayili}{not_}", model=model,
                            en_cok=3000, sicaklik=0.4 + 0.15 * d, dusun=False)  # fmt: skip
        for k in (y.get("kesitler") or []) if isinstance(y, dict) else []:
            k = kesit_kirp(k, sahneler)
            if len(secilen) < 3 and kesit_gecerli(k, sahneler) and not dolu & {int(x) for x in k["sahneler"]}:
                k["sahneler"] = [int(x) for x in k["sahneler"]]
                secilen.append(k)
                dolu |= set(k["sahneler"])
        if len(secilen) >= 3:
            break
    return secilen


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
         tur_sayisi: int = 4, kayit: list | None = None, dizin: Path | None = None,
         butce: int | None = None) -> dict:  # fmt: skip
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
        s = yaz(oturum, konu, kaynak_metni, gorsel_metni, dizin=dizin, ust=kelime_hedefi(butce or gorsel_sayisi)[1])
        if taslak:
            taslak.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    for tur in range(tur_sayisi):
        if duz := yapi_onar(s, gorsel_sayisi):
            print(f"senaryo yapı onarımı: {len(duz)} değişiklik", flush=True)
        if son_hal:
            son_hal.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
        kod = yapi_kapisi(s, gorsel_sayisi, butce) + sayi_kapisi(s, kaynak_metni)
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
    kod = yapi_kapisi(s, gorsel_sayisi, butce) + sayi_kapisi(s, kaynak_metni)
    kayit.append({"tur": tur_sayisi, "kod": kod, "olgu": olgu, "cikarilan": sorted(cikar),
                  "sahne": len(s.get("sahneler", []))})  # fmt: skip
    print(f"senaryo son: {len(cikar)} sahne çıkarıldı, kod {len(kod)}", flush=True)
    return s


SISTEM_ESLE = """You are the picture editor of a documentary explainer. Every scene shows one photo behind its
graphics. You get the scenes (index, type, narration, on-screen text) and the IMAGE LIST (id: Wikimedia file title).
Pick ONE image per scene. Rules, in order:
1. Never show a person the line is not about. If the line names or is about a person, use a photo of THAT person;
   if no photo of them exists, use a place/object/event image connected to the line (a building, a car, a stage),
   never a photo of someone else.
2. Otherwise pick the image that best shows what the line says (the place, the object, the film, the event).
3. If nothing fits, pick a neutral image of the story's setting with no identifiable person.
4. Use each image at most 3 times and never in two neighbouring scenes; spread the images out.
For each scene also say "uyum": 2 (shows exactly what the line is about), 1 (related context), 0 (neutral filler).
Also list, for EVERY image, the identifiable person it shows (from its title; null for places, objects, crowds).
Return ONLY JSON: {"kisiler": {"G1": "Full Name" or null, ...}, "atamalar": [{"i": scene index, "gorsel": "G..",
"uyum": 0|1|2}]} covering every scene."""


def _kisi_uygun(kisi: str | None, metin: str, konu: str) -> bool:
    """Görseldeki kişi sahnede ya da videonun konusunda adıyla geçiyor mu (soyadı/ad parçası, ≥ 4 harf)."""
    if not kisi:
        return True
    hedef = f"{metin} {konu}".lower()
    return any(len(p) >= 4 and p in hedef for p in re.findall(r"[a-zà-ÿ]+", kisi.lower()))


def _altyazili(sh: dict) -> bool:
    """Fotoğraf sahnesinin alt yazısı (etiket) o fotoğrafı tanımlar; sayı sahnesindeki etiket rakamın açıklamasıdır."""
    return sh.get("tur") == "foto" and bool(sh.get("etiket")) and bool(sh.get("gorsel"))


def gorsel_eslestir(oturum: Oturum, senaryo: dict, gorsel_metni: str, gorsel_sayisi: int,
                    model: str = BOLUM_MODEL, konu: str = "") -> list[str]:  # fmt: skip
    """Sahne → görsel atamasını anlam üzerinden yeniden yapar (yerinde). Neden: v2'de her sahnede görsel zorunlu
    (K-44); kodun "en az kullanılan" ataması 11-20 Bond videosunda Pattinson'ın doğum yerini Daniel Craig'in,
    Seydoux alıntısını Pierce Brosnan'ın fotoğrafıyla gösterdi (eleştirmen 29 P0 "anlamsız görsel").
    Sonra kod sınırları uygular (en çok GORSEL_EN_COK, komşu tekrar yok). Dönüş: değişiklik listesi."""
    s = senaryo.get("sahneler") or []
    satirlar = []
    for i, sh in enumerate(s):
        if sh.get("tur") == "harita":
            continue
        ekran = " ".join(str(x) for x in (sh.get("baslik"), sh.get("metin"), sh.get("etiket"), sh.get("kim")) if x)
        satirlar.append(
            f"{i}. [{sh.get('tur')}] {sh.get('anlatim', '')}" + (f" || on screen: {ekran}" if ekran else "")
        )
    mesaj = f"=== IMAGE LIST ===\n{gorsel_metni}\n\n=== SCENES ===\n" + "\n".join(satirlar)
    y = oturum.json_sor(SISTEM_ESLE, mesaj, model=model, en_cok=8000, sicaklik=0.2, dusun=False)
    atama = {}
    for a in (y.get("atamalar") or []) if isinstance(y, dict) else []:
        try:
            i, g = int(a["i"]), str(a["gorsel"])
        except (KeyError, TypeError, ValueError):
            continue
        m = re.fullmatch(r"G(\d+)", g)
        if 0 <= i < len(s) and m and 1 <= int(m.group(1)) <= gorsel_sayisi:
            atama[i] = (g, int(a.get("uyum", 1) or 0))
    kisiler = {str(k): v for k, v in ((y.get("kisiler") or {}) if isinstance(y, dict) else {}).items()}
    yapilan = []
    for i, (g, uyum) in atama.items():
        if s[i].get("tur") == "harita":
            continue
        # alt yazı (etiket) yazarın seçtiği fotoğrafı tanımlar; görsel değişirse yazı yanlış kişinin altında kalır
        # (11-20 Bond: "Pattinson, Venice" alt yazısı Daniel Craig balmumu heykelinin altına düştü)
        if _altyazili(s[i]):
            continue
        if s[i].get("gorsel") != g:
            yapilan.append(f"sahne {i}: {s[i].get('gorsel')} → {g} (uyum {uyum})")
            s[i]["gorsel"] = g
        s[i]["gorsel_uyum"] = uyum
    # sert kural: sahnede/konuda adı geçmeyen birinin fotoğrafı gösterilmez (11-20: Piers Morgan satırında Brosnan)
    kisisiz = [f"G{k}" for k in range(1, gorsel_sayisi + 1) if not kisiler.get(f"G{k}")]
    for i, sh in enumerate(s):
        g = sh.get("gorsel")
        if not g or sh.get("tur") == "harita":
            continue
        metin = " ".join(str(sh.get(k) or "") for k in ("anlatim", "baslik", "metin", "etiket", "kim"))
        if not _kisi_uygun(kisiler.get(str(g)), metin, konu):
            komsu = {str(s[j].get("gorsel")) for j in (i - 1, i + 1) if 0 <= j < len(s)}
            say = _gorsel_say(s)
            aday = [k for k in kisisiz if k not in komsu and say[k] < GORSEL_EN_COK]
            if aday:
                yeni = min(aday, key=lambda k: say[k])
                yapilan.append(f"sahne {i}: {g} ({kisiler.get(str(g))}) adı geçmiyor → {yeni}")
                sh["gorsel"], sh["gorsel_uyum"] = yeni, 0
    # sınırlar: fazla kullanım ve komşu tekrar, uyumu düşük olandan başlayarak çözülür
    for i, sh in enumerate(s):
        g = sh.get("gorsel")
        if not g or sh.get("tur") == "harita":
            continue
        komsu = i > 0 and str(s[i - 1].get("gorsel")) == str(g)
        if _altyazili(sh):  # alt yazılı fotoğraf yerinde kalır; sınır diğer sahnelerden çözülür
            continue
        if komsu or _gorsel_say(s[: i + 1])[str(g)] > GORSEL_EN_COK:
            metin = " ".join(str(sh.get(k) or "") for k in ("anlatim", "baslik", "metin", "etiket", "kim"))
            say = _gorsel_say(s)
            yasak = {str(s[j].get("gorsel")) for j in (i - 1, i + 1) if 0 <= j < len(s)}
            aday = [f"G{k}" for k in range(1, gorsel_sayisi + 1) if f"G{k}" not in yasak and say[f"G{k}"] < GORSEL_EN_COK
                    and _kisi_uygun(kisiler.get(f"G{k}"), metin, konu)]  # fmt: skip
            yeni = min(aday, key=lambda k: (say[k], int(k[1:]))) if aday else None
            if yeni:
                yapilan.append(f"sahne {i}: sınır {g} → {yeni}")
                sh["gorsel"], sh["gorsel_uyum"] = yeni, 0
            else:  # 11-27: aday yoksa aşım kalıyordu (bir fotoğraf 9 kez); fotoğrafı stok, kartı en az kullanılan doldurur
                yapilan.append(f"sahne {i}: sınır {g} → görselsiz (stok)")
                sh.pop("gorsel")
                sh.pop("gorsel_uyum", None)
    senaryo["gorsel_eslendi"] = True
    return yapilan


GRUP_KULLANIM = 4  # benzer grubun (aynı binanın farklı kareleri) videodaki toplam kullanımı
GRUP_UYE_EN_COK = 2  # grup üyesi tek fotoğrafın kullanımı


def grup_siniri(senaryo: dict, gruplar: dict[str, str]) -> list[str]:
    """Benzer görsel grupları için kullanım sınırı (yerinde). `gruplar`: "G5" → grup adı. Sınırı aşan sahne (önce uyumu
    düşük olan) görselsiz kalır: fotoğraf sahnesini stok video, kartı en az kullanılan fotoğrafın koyusu doldurur.
    11-27: grup kırpması gevşedi (GRUP_EN_COK 4); bu sınır olmasa aynı binanın dört karesi on iki sahneye yayılırdı."""
    s = senaryo.get("sahneler") or []
    sira = sorted(range(len(s)), key=lambda i: (-(s[i].get("gorsel_uyum") if s[i].get("gorsel_uyum") is not None
                                                  else 1), i))  # fmt: skip
    uye: Counter = Counter()
    grup: Counter = Counter()
    yapilan = []
    for i in sira:  # uyumu yüksek sahneler hakkı önce alır
        g = str(s[i].get("gorsel") or "")
        k = gruplar.get(g)
        if not k or s[i].get("tur") == "harita":
            continue
        if _altyazili(s[i]) or (uye[g] < GRUP_UYE_EN_COK and grup[k] < GRUP_KULLANIM):
            uye[g] += 1
            grup[k] += 1
            continue
        s[i].pop("gorsel")
        s[i].pop("gorsel_uyum", None)
        yapilan.append(f"sahne {i}: {g} grup sınırı ({k}) → görselsiz")
    return yapilan
