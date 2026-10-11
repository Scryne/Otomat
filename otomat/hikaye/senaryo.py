"""Senaryo: tek hikâye → 7-8 sahne (söz + görsel tarifi), hakem ve satır onarımı.

S11 dersi: bütün senaryoyu yeniden yazdırmak yakınsamıyor (her turda yeni hata); yalnız hakemin işaretlediği satırlar
onarılır. Kalan sorun varsa senaryo düşer, gunluk sıradaki hikâyeyi dener. Açılış kalıbını haydut seçer (kanca
kalıbının hikâye karşılığı). İki tür var: `tuhaf` (gerçek tuhaf olay, genel kitle) ve `masal` (Ezop, 3-7 yaş, MFK).
"""

import re
from dataclasses import dataclass, field

from otomat.hikaye import cf

KALIPLAR = {
    # tuhaf
    "sonuc_once": "Open with the strangest outcome of the story, stated flatly, as if it were ordinary news.",
    "detay": "Open with one vivid, concrete detail that makes no sense yet; the next lines explain it.",
    "zitlik": "Open with the contrast between what was supposed to happen and what actually happened.",
    "kisi": "Open with the main person or animal in the middle of the action, as if the camera is already rolling.",
    # masal
    "karakter": "Open by introducing the main animal warmly, with one fun detail about it.",
    "soru": "Open with one short question to the child that connects to the lesson.",
    "ses": "Open with a playful sound word the main character makes (like Hop! Splash! Munch!), then who makes it.",
    "sorun": "Open with the problem the main character has, in simple words.",
}

ISTEM = {
    "tuhaf": """You write scripts for 35-second YouTube Shorts that tell ONE true, strange story.
Viewers swipe away in one second unless the first line grabs them, so the story must pull them to the end.

Source (Wikipedia article "{baslik}"):
<<<
{metin}
>>>
Why Wikipedia editors list it as unusual: {konu}

Write 7-8 scenes, 75-90 words in total. Each scene = one spoken line (5-12 words) + one illustration.
Opening line: {kalip}
Then tell it like a storyteller, not an encyclopedia: a person (or animal) we can picture, what they expected, the
strange thing that happened, how it got worse or weirder, the turn. Every line must move the story forward; a line
that only lists measurements is a wasted line. Use at most two numbers in the whole script: the most striking ones.
Last line: the payoff or the absurd consequence, short and memorable, so the viewer wants to watch again.
Rules:
- Spoken, plain English that reads naturally aloud. Past tense. No "did you know", no questions to the viewer, no
  "subscribe", no moralizing. No symbols or abbreviations (write "degrees", "percent", "miles per hour").
- EVERY fact, number, name, date and cause must be stated in the source. If the source is unsure, say "reportedly".
  Do not merge different events. Do not round or change numbers; write a number as digits only if the source does.
title: a curiosity title under 60 characters that only uses facts from the source; no clickbait words.""",
    "masal": """You write scripts for 35-second YouTube Shorts for children aged 3 to 7: a gentle retelling of one
Aesop fable, told by a warm storyteller.

The fable ("{baslik}"):
<<<
{metin}
>>>

Write 7 scenes, 60-85 words in total. Each scene = one spoken line (4-12 words) + one illustration.
Opening line: {kalip}
Then tell the fable's events in order, so a 5-year-old can follow. The last line says the lesson in one short,
simple sentence a child can remember.
Rules:
- Simple words a 5-year-old knows. Short sentences. Warm, playful, kind. Past tense, except a question to the child.
- Keep the fable's plot and lesson. Soften any harm: nobody is hurt, killed, eaten or cruelly punished; no scary
  threats; no mean name-calling. If the original is harsh, the character simply learns, leaves or says sorry.
- No "subscribe", "like", "comment" or links. No brand names. No "Once upon a time" unless it truly fits.
title: a friendly title under 50 characters with the main characters, e.g. "The Fox Who Wanted the Grapes".""",
}

GORSEL_KURALI = {
    "tuhaf": "The illustrator cannot draw writing: never describe anything that carries words or numbers (signs, "
    "neon signs, shop names, banners, placards, posters, slogans, newspapers, documents, maps, plaques, labels, "
    "scoreboards, numbered jerseys, license plates, graffiti) and never quote words. Show a protest through faces and "
    "raised fists, a shop as a lit window full of goods, a court through robes and a gavel. Never show dead bodies, "
    "injuries or blood; show the moment before, or the aftermath through objects and faces.",
    "masal": "No text or letters in the image. Cute, friendly, safe and cozy; nothing scary, no sharp teeth shown, "
    "nobody hurt.",
}

# İlk kare kaydırmayı durdurmalı (Shorts feed'inde küçük resim yok; ilk saniye izlendi/kaydırıldı oranını belirler)
ILK_KARE = {
    "tuhaf": "The first scene's image must stop a scrolling viewer: a close, bold, dramatic composition with one clear "
    "subject that shows what the opening line says.",
    "masal": "The first scene's image is a close, cheerful portrait of the main character, big and centered.",
}

SAHNE_ISTEMI = """
world: one sentence describing era, place, clothing and palette for the illustrator (same in every scene).
cast: 0-3 recurring characters, each a fixed visual description (species or age, clothes, colors) reused verbatim.
scenes[].image: a concrete visual description of that scene for an illustrator who knows nothing about the story
  (who, doing what, where, camera angle). Name every object unambiguously ("a huge steel storage tank", never just
  "the tank"). Copy cast descriptions verbatim when a character appears. {ilk_kare} {gorsel_kurali}
mood: the music mood that fits the story."""

HAKEM_ISTEM = {
    "tuhaf": """You are a strict fact checker. SOURCE (the only truth):
<<<
{metin}
>>>
TITLE: {baslik}
SCRIPT LINES:
{satirlar}

Check the title (as line 0) and every line: numbers, names, dates, places, causes, sequence, who did what.
Flag a line if it states something the source does not say, contradicts it, attaches a fact to the wrong person or
event, or exaggerates. Also flag a line that breaks the telling: it gives away the ending before the story gets
there, jumps in time without saying when, or repeats an event an earlier line already told. Dramatic wording is fine
when the facts underneath are correct. Return only real problems.""",
    "masal": """You review a children's story script (ages 3-7) against the original fable.
FABLE:
<<<
{metin}
>>>
TITLE: {baslik}
SCRIPT LINES:
{satirlar}

Flag a line (title = line 0) only if it:
- contradicts the fable or changes its outcome or lesson (softening harm is expected and fine: a threat becoming a
  grumble, hunters becoming "a net", someone leaving instead of being punished);
- contains something scary, violent, cruel, distressing, rude, or unsafe for a child to copy;
- uses a word most 5-year-olds would not understand (like "gnawed", "unconcern", "trellis");
- is the last line and does not state the fable's lesson in a simple sentence;
- cannot be followed from the lines before it: unclear who speaks or acts, a line of dialogue that makes no sense
  in the story, or events out of order.
Do not flag playful sound words, an opening question to the child, small added details that fit the fable, or
style choices. Return only real problems.""",
}

ONARIM_ISTEM = """SOURCE:
<<<
{metin}
>>>
A short video script was checked. TITLE (line 0): {baslik}
LINES:
{satirlar}

PROBLEMS:
{sorun}

Rewrite ONLY the flagged lines (line 0 = title) so every problem is fixed; if unsure, say less. Keep each line
4-12 words, spoken, and keep the story flowing with the lines around it. Return the fixed lines."""

# Yazı taşıyan nesne: flux "no text"i tutmuyor, tarifte tabela/pankart/gazete varsa anlamsız harflerle çiziyor
# (Sister Boom Boom, Wog Rolo, Prester John; 10-12). Olumsuz kalıp ("no signs") sayılmaz.
YAZI_TASIYAN = re.compile(
    r"\b(?:neon|signs?|signboards?|signage|banners?|placards?|posters?|slogans?|newspapers?|headlines?|billboards?|"
    r"graffiti|labels?|plaques?|scoreboards?|menus?|ballots?|documents?|maps?|charts?|inscri\w+|storefronts?|"
    r"shopfronts?|(?:license|number) plates?|jerseys?|captions?|written|lettering|handwritten|text)\b"
    r"|\"[^\"]{2,}\"",
    re.I,
)
GORSEL_TUR = 2
TARIF_KELIME = 8  # onarımdan dönen tarif bundan kısaysa özgün tarif kalır
OLUMSUZ = re.compile(r"\b(?:no|without|never|not any)\b[^.;:]*", re.I)

GORSEL_ONARIM_ISTEM = """These are illustration descriptions for a short video. The illustrator cannot draw writing:
anything that carries words or numbers comes out as garbled letters.
WORLD: {dunya}
SCENES:
{sahneler}

FLAGGED (object that would carry writing):
{sorun}

Rewrite the world and ONLY the flagged scenes so the same moment is shown without the flagged objects. Do not mention
them at all, not even as blank, plain, unmarked or wordless versions: the illustrator writes on any sign, banner or
paper it is given. Show the moment through people, faces, gestures, clothing, light and setting instead (a protest =
a crowd with raised fists; a vote = a hand dropping a folded slip into a wooden box; a shop = a lit window full of
goods; colored light instead of neon signs). Do not quote words. Keep every character description and everything
else unchanged. For each flagged scene return its complete new description (who, doing what, where, camera angle),
never a reference like "same as before" or "SCENE 2"."""
GORSEL_ONARIM_SEMA = {
    "type": "object",
    "properties": {
        "world": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"scene": {"type": "integer"}, "image": {"type": "string"}},
                "required": ["scene", "image"],
            },
        },
    },
    "required": ["world", "scenes"],
}

SORUN_SEMA = {
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
SAHNE_SAYISI = {"tuhaf": (7, 8), "masal": (7, 7)}
KELIME = {"tuhaf": (60, 100), "masal": (50, 95)}  # toplam kelime; dışı onarıma girer
SATIR_KELIME = 14
SAYI_SINIRI = 3  # istem 2 der; bir pay bırakılır
# Oran ("1:4-million" anlatıcıda "1, 4 million" oldu, Tree of Ténéré 10-09). Saat ("12:30") doğru okunuyor.
ORAN = r"\b\d+:(?!\d{2}(?![\d,-]))\d"
SEMBOL = re.compile(rf"[°%&$€£#@/+=<>~^*|]|{ORAN}|\b(?:mph|km/h|ft|lbs?|approx|etc)\b\.?", re.I)
TUR_SAYISI = 4


class SenaryoHatasi(RuntimeError):
    def __init__(self, mesaj: str, sorunlar: list):
        super().__init__(mesaj)
        self.sorunlar = sorunlar


@dataclass
class Senaryo:
    baslik: str
    mood: str
    dunya: str
    oyuncular: list[str]
    satirlar: list[str]
    gorseller: list[str]
    turlar: list[list] = field(default_factory=list)  # her turda bulunan sorunlar (meta.json'a)
    gorsel_onarim: list[list] = field(default_factory=list)  # yazı taşıyan nesne: [onarımdan önce, sonra]


def sema(tur: str, moodlar: list[str]) -> dict:
    en_az, en_cok = SAHNE_SAYISI[tur]
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "mood": {"type": "string", "enum": moodlar},
            "world": {"type": "string"},
            "cast": {"type": "array", "items": {"type": "string"}},
            "scenes": {
                "type": "array",
                "minItems": en_az,
                "maxItems": en_cok,
                "items": {
                    "type": "object",
                    "properties": {"line": {"type": "string"}, "image": {"type": "string"}},
                    "required": ["line", "image"],
                },
            },
        },
        "required": ["title", "mood", "world", "cast", "scenes"],
    }


def sayi_ad_kapisi(metin: str, kaynak: str, adlar: bool = True) -> list[str]:
    """Metindeki her sayı ve cümle ortasındaki her özel ad kaynakta geçmeli (K-4'ün hikâye karşılığı). `adlar=False`:
    başlık "Title Case" yazılır, her kelimesi büyük harfle başlar ("…Curse Haunts the Tigers"); ad sanılıp onarıma
    gidiyordu (10-09, bir hakem turu boşa). Başlıktaki adları hakem denetler."""
    hata = []
    k = kaynak.lower().replace(",", "")
    for n in re.findall(r"\d[\d,.]*", metin):
        if n.strip(".,").replace(",", "") not in k:
            hata.append(f"number not in source: {n}")
    if not adlar:
        return hata
    for ad in re.findall(r"(?<![.!?:\"]\s)(?<!^)\b[A-Z][a-z]{2,}\b", metin):
        if ad.lower()[: max(4, len(ad) - 3)] not in k:  # Londoners → london
            hata.append(f"name not in source: {ad}")
    return hata


def kod_kontrolu(tur: str, baslik: str, satirlar: list[str], kaynak: str) -> list[tuple[int, str]]:
    sorun = []
    if tur == "tuhaf":
        sorun += [(i, h) for i, s in enumerate([baslik, *satirlar]) for h in sayi_ad_kapisi(s, kaynak, adlar=i > 0)]
        # sayı yığını hikâyeyi ölçü listesine çeviriyordu (Molasses: "50-foot, 90-foot tank held 2.3 million gallons")
        sayili = [i for i, s in enumerate(satirlar, 1) for _ in re.findall(r"\d[\d,.]*", s)]
        if len(sayili) > SAYI_SINIRI:
            sorun.append((sayili[-1], f"too many numbers in the script ({len(sayili)}); keep the 2 most striking, "
                                      "tell the rest as story"))  # fmt: skip
    for i, s in enumerate(satirlar, 1):  # anlatıcı sembolü okuyamıyor ("40°F")
        if sembol := SEMBOL.findall(s):
            sorun.append((i, f"spell out symbols as words for the narrator: {' '.join(sembol)}"))
    toplam = sum(len(s.split()) for s in satirlar)
    en_az, en_cok = KELIME[tur]
    for i, s in enumerate(satirlar, 1):
        if len(s.split()) > SATIR_KELIME:
            sorun.append((i, f"too long ({len(s.split())} words); keep it under {SATIR_KELIME}"))
        elif len(s.split()) < 3:  # onarım satırı boşaltabiliyor; yayın kabulü 3 kelimeden kısa satırı reddeder
            sorun.append((i, "too short; write a full spoken line of 4-12 words"))
    if not en_az <= toplam <= en_cok:
        sorun.append((len(satirlar), f"script has {toplam} words in total; it must be {en_az}-{en_cok}"))
    return sorun


def yazi_tasiyanlar(dunya: str, gorseller: list[str]) -> list[tuple[int, str]]:
    """(sahne no, bulunan nesneler); 0 = dünya cümlesi (her sahneye girer)."""
    sorun = []
    for i, metin in enumerate([dunya, *gorseller]):
        if bulunan := YAZI_TASIYAN.findall(OLUMSUZ.sub("", metin)):
            sorun.append((i, ", ".join(dict.fromkeys(b.lower() for b in bulunan))))
    return sorun


def gorsel_temizle(sc: Senaryo) -> None:
    """Tarifte yazı taşıyan nesne varsa en çok GORSEL_TUR onarım turu; ikinci tur yalnız hâlâ işaretli kalanları
    gönderir. Kalan yazıyı üretimde OCR yakalar (yazi.py)."""
    if not (ilk := yazi_tasiyanlar(sc.dunya, sc.gorseller)):
        return
    sorun = ilk
    for _ in range(GORSEL_TUR):
        f = cf.sohbet(
            GORSEL_ONARIM_ISTEM.format(
                dunya=sc.dunya,
                sahneler="\n".join(f"scene {i}: {g}" for i, g in enumerate(sc.gorseller, 1)),
                sorun="\n".join(f"{'world' if n == 0 else f'scene {n}'}: {r}" for n, r in sorun),
            ),
            GORSEL_ONARIM_SEMA,
        )
        if len(f["world"].split()) >= TARIF_KELIME:
            sc.dunya = f["world"].strip()
        for d in f["scenes"]:
            # S12 (10-12): model sahnelere tarif yerine "SCENE 2" yazdı, kare ana karaktersiz boş sokak çıktı
            if 1 <= d["scene"] <= len(sc.gorseller) and len(d["image"].split()) >= TARIF_KELIME:
                sc.gorseller[d["scene"] - 1] = d["image"].strip()
        if not (sorun := yazi_tasiyanlar(sc.dunya, sc.gorseller)):
            break
    sc.gorsel_onarim = [[[n, r] for n, r in ilk], [[n, r] for n, r in sorun]]


def _numarali(satirlar: list[str]) -> str:
    return "\n".join(f"{i}. {s}" for i, s in enumerate(satirlar, 1))


def yaz(tur: str, baslik: str, kaynak: str, konu: str, kalip: str, moodlar: list[str]) -> Senaryo:
    kisa = kaynak[:6000]
    istem = ISTEM[tur].format(baslik=baslik, metin=kisa, konu=konu, kalip=KALIPLAR[kalip]) + SAHNE_ISTEMI.format(
        gorsel_kurali=GORSEL_KURALI[tur], ilk_kare=ILK_KARE[tur]
    )
    s = cf.sohbet(istem, sema(tur, moodlar))
    sc = Senaryo(
        baslik=s["title"].strip(),
        mood=s["mood"],
        dunya=s["world"],
        oyuncular=s["cast"],
        satirlar=[x["line"].strip() for x in s["scenes"]],
        gorseller=[x["image"] for x in s["scenes"]],
    )
    for tur_no in range(TUR_SAYISI):
        sorun = kod_kontrolu(tur, sc.baslik, sc.satirlar, kaynak)
        h = cf.sohbet(
            HAKEM_ISTEM[tur].format(metin=kisa, baslik=sc.baslik, satirlar=_numarali(sc.satirlar)), SORUN_SEMA
        )
        sorun += [(p["line"], p["reason"]) for p in h["problems"]]
        sc.turlar.append([[n, r[:300]] for n, r in sorun])
        if not sorun:
            gorsel_temizle(sc)
            return sc
        if tur_no == TUR_SAYISI - 1:
            break
        f = cf.sohbet(
            ONARIM_ISTEM.format(
                metin=kisa,
                baslik=sc.baslik,
                satirlar=_numarali(sc.satirlar),
                sorun="\n".join(f"line {n}: {r}" for n, r in sorun),
            ),
            ONARIM_SEMA,
        )
        for d in f["fixes"]:
            if d["line"] == 0:
                sc.baslik = d["text"].strip()
            elif 1 <= d["line"] <= len(sc.satirlar):
                sc.satirlar[d["line"] - 1] = d["text"].strip()
    raise SenaryoHatasi(f"senaryo {TUR_SAYISI} turda hakemden geçmedi", sc.turlar)
