"""Senaryo: tek hikâye → 7-8 sahne (söz + görsel tarifi), hakem ve satır onarımı.

S11 dersi: bütün senaryoyu yeniden yazdırmak yakınsamıyor (her turda yeni hata); yalnız hakemin işaretlediği satırlar
onarılır. Kalan sorun varsa senaryo düşer, gunluk sıradaki hikâyeyi dener. Açılış kalıbını haydut seçer (kanca
kalıbının hikâye karşılığı). İki tür var: `tuhaf` (gerçek tuhaf olay) ve `masal` (Ezop, yumuşatılmadan); ikisi de genel
kitle. Masal 10-08'den 10-13'e 3-7 yaş ve MFK'ydı: public 3 video 0 izlenmede kaldı (Earth'ün hikâyeleri 6-81), Scryne
genel kitleye çevirdi (K-24, docs/arastirma/08).
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
    # masal (zitlik ortak)
    "karakter": "Open with the main animal in the middle of what it wants, with one telling detail about its nature.",
    "sorun": "Open with the problem or temptation the main animal faces, stated plainly.",
    "ders": "Open with the uncomfortable truth the fable proves, stated as a flat rule of life; the story then shows "
    "it.",
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
    "masal": """You write scripts for 35-second YouTube Shorts for adults: one Aesop fable, told straight by a dry,
quick-witted storyteller. Aesop wrote these about people; the viewer should recognize someone they know.
Viewers swipe away in one second unless the first line grabs them, so the story must pull them to the end.

The fable ("{baslik}"):
<<<
{metin}
>>>

Write 7 scenes, 60-90 words in total. Each scene = one spoken line (5-12 words) + one illustration.
Opening line: {kalip}
Then tell the fable's events in order, sharply, every line moving the story. Keep the original ending as Aesop wrote
it, without softening; state any death or harm plainly and briefly, never in gory detail. The last line is the moral
in one short, memorable sentence that is as true for people as for animals.
Rules:
- Spoken, plain English that reads naturally aloud. Past tense. Wry, not cute: no baby talk, no sound words, no
  questions to the viewer, no "kids" or "little ones".
- Keep the fable's plot, characters and moral; add no new events, characters or modern objects.
- No "subscribe", "like", "comment" or links. No brand names. No "Once upon a time".
title: a curiosity title under 55 characters that names the main animals and hints at the twist, not the moral.""",
}

GORSEL_KURALI = {
    "tuhaf": "The illustrator cannot draw writing: never describe anything that carries words or numbers (signs, "
    "neon signs, shop names, banners, placards, posters, slogans, newspapers, documents, maps, plaques, labels, "
    "scoreboards, numbered jerseys, license plates, graffiti) and never quote words. Show a protest through faces and "
    "raised fists, a shop as a lit window full of goods, a court through robes and a gavel. Never show dead bodies, "
    "injuries or blood; show the moment before, or the aftermath through objects and faces.",
    "masal": "The illustrator cannot draw writing: never describe anything that carries words. Animals look like real "
    "animals with natural anatomy and expressive faces, not cartoon mascots; no clothes unless the fable says so. "
    "Never show blood, wounds or a dead body; show the moment before, or the aftermath through faces.",
}

# İlk kare kaydırmayı durdurmalı (Shorts feed'inde küçük resim yok; ilk saniye izlendi/kaydırıldı oranını belirler)
ILK_KARE = {
    "tuhaf": "The first scene's image must stop a scrolling viewer: a close, bold, dramatic composition with one clear "
    "subject that shows what the opening line says.",
    "masal": "The first scene's image must stop a scrolling viewer: a close, dramatic portrait of the main animal in "
    "the moment the opening line describes, one clear subject, strong light.",
}

SAHNE_ISTEMI = """
world: one sentence describing era, place, clothing and palette for the illustrator (same in every scene).
cast: 0-3 recurring characters, each with a short name (exactly as you will write it in every scene) and a fixed
  look (species or age, clothes, colors) reused verbatim.
scenes[].image: a concrete visual description of that scene for an illustrator who knows nothing about the story
  (who, doing what, where, camera angle). Name every object unambiguously ("a huge steel storage tank", never just
  "the tank"). Copy cast descriptions verbatim when a character appears. {ilk_kare} {gorsel_kurali}
  No image may contradict the lines so far: a character who lost something is never shown with it again.
changes: when a cast member's look changes during the story (loses its tail, gets a crown, turns muddy), one entry:
  who (the cast name), from_scene (first scene number showing the new look), look (the new look in positive, visible
  words: what the viewer SEES, e.g. "a tailless fox with a round bare rump and a small pink bandage"; the illustrator
  cannot draw "gone", "without" or "no"), question (a yes/no question about one picture that checks it, e.g. "Does the
  orange fox in the red scarf have a tail?"), expected (the correct answer from from_scene on). The cast description
  shows the look at the start and does not mention the feature that changes. Empty list if no look changes.
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
when the facts underneath are correct. An event the source calls legend or doubtful is fine when the line marks it
("reportedly", "legend says"). Return only real problems.""",
    "masal": """You review a short video script against the original Aesop fable it retells.
FABLE:
<<<
{metin}
>>>
TITLE: {baslik}
SCRIPT LINES:
{satirlar}

Flag a line (title = line 0) only if it:
- contradicts the fable: changes who does what, the outcome, or the moral; adds an event, character or modern object
  the fable does not have; softens the ending into something Aesop did not write;
- describes harm in gory or graphic detail (stating plainly that someone was killed or eaten is fine);
- is the last line and does not state the fable's moral in one clear sentence;
- cannot be followed from the lines before it: unclear who speaks or acts, a line of dialogue that makes no sense
  in the story, events out of order, or the ending given away before the story gets there;
- the title gives away the moral or names an animal that is not in the fable.
Do not flag wry wording, small added details that fit the fable, or style choices. Return only real problems.""",
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

Rewrite ONLY the flagged lines (line 0 = title) so every problem is fixed; if unsure, say less. Use only what the
source states: add no new detail, purpose, cause or number. Common fixes:
- a word or adjective the source does not support: delete it, keep the rest of the line;
- an event the source calls legend, tradition, rumor or possibly exaggerated: keep it, but mark it ("reportedly",
  "legend says", "the story goes");
- a repeated event: tell the next step of the story instead.
Keep each line 4-12 words, spoken, and keep the story flowing with the lines around it. Return the fixed lines."""

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
# Forma takım adı basılıyor; "jersey" karakter tarifinde durunca onarım ona dokunmuyordu ("tarifi değiştirme"), iki tur
# boşa gitti (Bartman, 10-12). Kodla düz forma yapılır, karakter tarifinde de.
GIYSI = [(re.compile(r"\bnumbered\s+", re.I), ""), (re.compile(r"\bjersey(s?)\b", re.I), r"uniform\1")]

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
SAYI_HEDEF = 2  # sınır aşılınca ilk ikisinden sonraki sayıları taşıyan her satır onarıma gider
# Son tur kalanı ara satırlardaysa (ilk ve son satır değil) en çok bu kadar satır çıkarılıp hakeme bir kez daha
# sorulur; kabul 6 satırın altını reddeder (kabul.SATIR)
CIKAR_EN_COK = 2
CIKAR_EN_AZ = 6
# Oran ("1:4-million" anlatıcıda "1, 4 million" oldu, Tree of Ténéré 10-09). Saat ("12:30") doğru okunuyor.
ORAN = r"\b\d+:(?!\d{2}(?![\d,-]))\d"
SEMBOL = re.compile(rf"[°%&$€£#@/+=<>~^*|]|{ORAN}|\b(?:mph|km/h|ft|lbs?|approx|etc)\b\.?", re.I)
TUR_SAYISI = 4
TAKVIM = {
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "January", "February", "March",
    "April", "June", "July", "August", "September", "October", "November", "December",
}  # fmt: skip
BASLIK_UZUNLUK = (10, 100)  # YouTube sınırı 100; kabul de bunu ister


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
    cikarilan: list[str] = field(default_factory=list)  # son çare: onarılamayıp çıkarılan ara satırlar
    # hikâyede değişen görünüş (Fox Without A Tail, 10-13: kuyruk 2. satırda koptu, 3 karede yerindeydi):
    # {"kim", "sahne" (1'den), "gorunum", "soru", "beklenen"}; istem kodla eklenir, kare görme modeliyle denetlenir
    degisimler: list[dict] = field(default_factory=list)


def sema(tur: str, moodlar: list[str]) -> dict:
    en_az, en_cok = SAHNE_SAYISI[tur]
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "mood": {"type": "string", "enum": moodlar},
            "world": {"type": "string"},
            # nesne: düz metin cast "Ad, tarif" biçiminde geliyordu, `Ad: tarif` ayrılamayınca Earth'te tarif hiçbir
            # sahne istemine girmiyordu (Heraclitus, 10-13 denetimi)
            "cast": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "look": {"type": "string"}},
                    "required": ["name", "look"],
                },
            },
            "changes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "who": {"type": "string"},
                        "from_scene": {"type": "integer"},
                        "look": {"type": "string"},
                        "question": {"type": "string"},
                        "expected": {"type": "boolean"},
                    },
                    "required": ["who", "from_scene", "look", "question", "expected"],
                },
            },
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
        "required": ["title", "mood", "world", "cast", "changes", "scenes"],
    }


DEGISIM_KELIME = 4


def degisimler(ham: list[dict], oyuncular: list[str], sahne_sayisi: int) -> list[dict]:
    """Model çıktısındaki `changes` süzülür: kişi kadroda olmalı, sahne aralıkta, görünüş tarif edilmiş, soru soru.
    Görünüş olumsuz kalıpla yazıldıysa ("his tail gone") alınmaz: klein olumsuzu çizemiyor (S13, 2/2 kuyruklu)."""
    adlar = {o.partition(":")[0].strip().lower(): o.partition(":")[0].strip() for o in oyuncular}
    sonuc = []
    for d in ham or []:
        kim = adlar.get(str(d.get("who", "")).strip().lower())
        gorunum, soru = str(d.get("look", "")).strip(), str(d.get("question", "")).strip()
        sahne = d.get("from_scene")
        if (
            kim
            and isinstance(sahne, int)
            and 1 < sahne <= sahne_sayisi
            and len(gorunum.split()) >= DEGISIM_KELIME
            and not re.search(r"\b(?:gone|without|no|not|missing)\b", gorunum, re.I)
            and soru.endswith("?")
        ):
            sonuc.append({"kim": kim, "sahne": sahne, "gorunum": gorunum.rstrip("."), "soru": soru,
                          "beklenen": bool(d.get("expected"))})  # fmt: skip
    return sonuc


def sayi_ad_kapisi(metin: str, kaynak: str, adlar: bool = True) -> list[str]:
    """Metindeki her sayı ve cümle ortasındaki her özel ad kaynakta geçmeli (K-4'ün hikâye karşılığı). `adlar=False`:
    başlık "Title Case" yazılır, her kelimesi büyük harfle başlar ("…Curse Haunts the Tigers"); ad sanılıp onarıma
    gidiyordu (10-09, bir hakem turu boşa). Başlıktaki adları hakem denetler."""
    hata = []
    k = kaynak.lower().replace(",", "")
    for n in re.findall(r"\d[\d,.]*", metin):
        # tam sayı olarak geçmeli: alt dize eşlemesinde "19" kaynaktaki "1950"den geçiyordu (10-13 denetimi)
        if not re.search(rf"(?<![\d.]){re.escape(n.strip('.,').replace(',', ''))}(?![\d]|\.\d)", k):
            hata.append(f"number not in source: {n}")
    if not adlar:
        return hata
    for ad in re.findall(r"(?<![.!?:\"]\s)(?<!^)\b[A-Z][a-z]{2,}\b", metin):
        if ad in TAKVIM:  # "Monday" kaynakta yazmasa da uydurma ad değil; tarihi hakem denetler
            continue
        # kısa ad tam kelime ("Tom" kaynaktaki "tomorrow"dan geçiyordu), uzun ad kelime başında kök (Londoners → london)
        kok = ad.lower() if len(ad) <= 4 else ad.lower()[: max(5, len(ad) - 3)]
        kalip = rf"\b{re.escape(kok)}\b" if len(ad) <= 4 else rf"\b{re.escape(kok)}"
        if not re.search(kalip, k):
            hata.append(f"name not in source: {ad}")
    return hata


def kod_kontrolu(tur: str, baslik: str, satirlar: list[str], kaynak: str) -> list[tuple[int, str]]:
    from otomat.hikaye.kaynaklar import HAKARET

    sorun = []
    if not BASLIK_UZUNLUK[0] <= len(baslik.strip()) <= BASLIK_UZUNLUK[1]:  # onarım başlığı boşaltabiliyor
        sorun.append((0, f"the title must be {BASLIK_UZUNLUK[0]}-{BASLIK_UZUNLUK[1]} characters"))
    # hakaret kabulde render'dan sonra yakalanıyordu: kota harcanmadan onarıma gitsin
    for i, s in enumerate([baslik, *satirlar]):
        if bulunan := HAKARET.findall(s):
            sorun.append((i, f"remove the slur or profanity: {', '.join(bulunan)}"))
    if tur == "tuhaf":
        sorun += [(i, h) for i, s in enumerate([baslik, *satirlar]) for h in sayi_ad_kapisi(s, kaynak, adlar=i > 0)]
        # sayı yığını hikâyeyi ölçü listesine çeviriyordu (Molasses: "50-foot, 90-foot tank held 2.3 million gallons").
        # Yalnız son sayılı satır işaretlenince onarım öbürlerine dokunmuyordu, sorun 4 turda kapanmadı (Loret, 10-12).
        sayili = [i for i, s in enumerate(satirlar, 1) for _ in re.findall(r"\d[\d,.]*", s)]
        if len(sayili) > SAYI_SINIRI:
            sorun += [(n, f"the script has {len(sayili)} numbers but may hold only {SAYI_HEDEF}; tell this line "
                          "without its number") for n in dict.fromkeys(sayili[SAYI_HEDEF:])]  # fmt: skip
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


def _yan_cumleler(metin: str) -> list[str]:
    """Ayraçlarıyla birlikte yan cümleler: parantez dışındaki virgül/noktalı virgül ve cümle sonu ("2.3" bölünmez)."""
    parca, derinlik, bas = [], 0, 0
    for i, c in enumerate(metin):
        derinlik += (c == "(") - (c == ")")
        if derinlik == 0 and (c in ",;" or (c == "." and metin[i + 1 : i + 2] in (" ", ""))):
            parca.append(metin[bas : i + 1])
            bas = i + 1
    return [p for p in [*parca, metin[bas:]] if p.strip()]


def yazisiz(metin: str) -> str:
    """Yazı taşıyan nesne geçen yan cümleler düşer ("…; the scoreboard shows the run tally climbing"). Olumsuz kalıp
    ("no text, no signs") sayılmaz; geriye anlamlı tarif kalmazsa metin aynen döner."""
    kalan = "".join(p for p in _yan_cumleler(metin) if not YAZI_TASIYAN.search(OLUMSUZ.sub("", p))).strip()
    kalan = kalan.rstrip(",;").rstrip()
    if len(kalan.split()) < TARIF_KELIME:
        return metin
    return kalan if kalan.endswith(".") else kalan + "."


def giysi_duz(metin: str) -> str:
    for desen, yerine in GIYSI:
        metin = desen.sub(yerine, metin)
    return metin


def gorsel_temizle(sc: Senaryo) -> None:
    """Tarifte yazı taşıyan nesne varsa en çok GORSEL_TUR onarım turu; ikinci tur yalnız hâlâ işaretli kalanları
    gönderir. Onarımdan sonra da işaretli kalan tarifin o yan cümlesi kodla düşer: Bartman'da (10-12) iki tur hiçbir
    şeyi değiştirmedi, skor tabelası anlamsız harflerle çizildi. Kalan yazıyı üretimde OCR yakalar (yazi.py)."""
    sc.dunya, sc.gorseller, sc.oyuncular = (
        giysi_duz(sc.dunya),
        [giysi_duz(g) for g in sc.gorseller],
        [giysi_duz(o) for o in sc.oyuncular],
    )
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
    for n, _ in sorun:
        if n == 0:
            sc.dunya = yazisiz(sc.dunya)
        else:
            sc.gorseller[n - 1] = yazisiz(sc.gorseller[n - 1])
    sorun = yazi_tasiyanlar(sc.dunya, sc.gorseller)
    sc.gorsel_onarim = [[[n, r] for n, r in ilk], [[n, r] for n, r in sorun]]


def _numarali(satirlar: list[str]) -> str:
    return "\n".join(f"{i}. {s}" for i, s in enumerate(satirlar, 1))


def _hakem(tur: str, kisa: str, baslik: str, satirlar: list[str]) -> list[tuple[int, str]]:
    h = cf.sohbet(HAKEM_ISTEM[tur].format(metin=kisa, baslik=baslik, satirlar=_numarali(satirlar)), SORUN_SEMA)
    return [(p["line"], p["reason"]) for p in h["problems"]]


def satir_cikar(tur: str, sc: Senaryo, sorun: list[tuple[int, str]], kaynak: str, kisa: str) -> bool:
    """Son çare: son turda kalan sorunlar yalnız ara satırlardaysa o satırlar (ve sahneleri) çıkarılır; kalan senaryo
    kod kontrolünden ve bir hakem turundan daha temiz geçerse kabul. "Emin değilsen az söyle"nin satır karşılığı:
    10-11/12'de Earth'te düşen 8 hikâyenin 5'i son turda tek sorunla düştü (kaynakta olmayan ayrıntı, tekrar)."""
    nolar = {n for n, _ in sorun}
    if (
        not nolar
        or len(nolar) > CIKAR_EN_COK
        or min(nolar) < 2  # başlık ve kanca çıkarılmaz
        or max(nolar) >= len(sc.satirlar)  # son satır (vurgu) ya da toplam kelime sorunu
        or len(sc.satirlar) - len(nolar) < CIKAR_EN_AZ
    ):
        return False
    kalan = [i for i in range(len(sc.satirlar)) if i + 1 not in nolar]
    satirlar = [sc.satirlar[i] for i in kalan]
    if kod_kontrolu(tur, sc.baslik, satirlar, kaynak):
        return False
    yeni = _hakem(tur, kisa, sc.baslik, satirlar)
    sc.turlar.append([[n, r[:300]] for n, r in yeni])
    if yeni:
        return False
    sc.cikarilan = [sc.satirlar[n - 1] for n in sorted(nolar)]
    sc.satirlar, sc.gorseller = satirlar, [sc.gorseller[i] for i in kalan]
    for d in sc.degisimler:  # çıkarılan sahne değişimin ilk sahnesiyse yeni görünüş sonraki kalan sahneden başlar
        d["sahne"] = 1 + sum(1 for i in kalan if i < d["sahne"] - 1)
    return True


KAYNAK_SINIR = 6000  # model ve hakeme giden kaynak; uzun makalede baş ve son korunur
KAYNAK_SON = 1500


def kisalt(kaynak: str) -> str:
    """Uzun makalede sonuç/epilog modele görünsün: düz kesim (`[:6000]`) hikâyenin sonunu atıyordu."""
    if len(kaynak) <= KAYNAK_SINIR:
        return kaynak
    return f"{kaynak[: KAYNAK_SINIR - KAYNAK_SON]}\n[...]\n{kaynak[-KAYNAK_SON:]}"


def oyuncular(ham: list) -> list[str]:
    """Cast `Ad: tarif` dizesine çevrilir (uretim ve degisimler bu biçimi okur); adda iki nokta olmasın."""
    sonuc = []
    for o in ham or []:
        if isinstance(o, dict):
            ad, tarif = str(o.get("name", "")).replace(":", " ").strip(), str(o.get("look", "")).strip()
            if ad and tarif:
                sonuc.append(f"{ad}: {tarif}")
        elif str(o).strip():
            sonuc.append(str(o).strip())
    return sonuc


def yaz(tur: str, baslik: str, kaynak: str, konu: str, kalip: str, moodlar: list[str]) -> Senaryo:
    kisa = kisalt(kaynak)
    istem = ISTEM[tur].format(baslik=baslik, metin=kisa, konu=konu, kalip=KALIPLAR[kalip]) + SAHNE_ISTEMI.format(
        gorsel_kurali=GORSEL_KURALI[tur], ilk_kare=ILK_KARE[tur]
    )
    s = cf.sohbet(istem, sema(tur, moodlar))
    sc = Senaryo(
        baslik=s["title"].strip(),
        mood=s["mood"],
        dunya=s["world"],
        oyuncular=oyuncular(s["cast"]),
        satirlar=[x["line"].strip() for x in s["scenes"]],
        gorseller=[x["image"] for x in s["scenes"]],
    )
    sc.degisimler = degisimler(s.get("changes"), sc.oyuncular, len(sc.gorseller))
    for tur_no in range(TUR_SAYISI):
        sorun = kod_kontrolu(tur, sc.baslik, sc.satirlar, kaynak) + _hakem(tur, kisa, sc.baslik, sc.satirlar)
        sc.turlar.append([[n, r[:300]] for n, r in sorun])
        if not sorun or (tur_no == TUR_SAYISI - 1 and satir_cikar(tur, sc, sorun, kaynak, kisa)):
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
