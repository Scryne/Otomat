"""Senaryo: tek hikâye → 7-8 sahne (söz + görsel tarifi), hakem ve satır onarımı.

S11 dersi: bütün senaryoyu yeniden yazdırmak yakınsamıyor (her turda yeni hata); yalnız hakemin işaretlediği satırlar
onarılır. Kalan sorun varsa senaryo düşer, gunluk sıradaki hikâyeyi dener. Açılış kalıbını haydut seçer (kanca
kalıbının hikâye karşılığı). İki tür var: `tuhaf` (gerçek tuhaf olay) ve `masal` (Ezop, yumuşatılmadan); ikisi de genel
kitle. Masal 10-08'den 10-13'e 3-7 yaş ve MFK'ydı: public 3 video 0 izlenmede kaldı (Earth'ün hikâyeleri 6-81), Scryne
genel kitleye çevirdi (K-24, docs/arastirma/08).
"""

import re
import unicodedata
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
    # spor (sonuc_once ve kisi ortak)
    "an": "Open inside the decisive moment, as if the camera is already rolling: the punch, the shot, the save, the "
    "whistle. The next lines rewind to how it got there.",
    "ihtimal": "Open with how impossible the outcome looked beforehand: who everyone expected to win, and why.",
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
    "spor": """You write scripts for 35-second YouTube Shorts that tell ONE true story from sports history to fans.
Viewers swipe away in one second unless the first line grabs them, so the story must pull them to the end.

Source (Wikipedia article "{baslik}"):
<<<
{metin}
>>>
What it is: {konu}

Write 7-8 scenes, 75-90 words in total. Each scene = one spoken line (5-12 words) + one illustration.
Opening line: {kalip}
If the source covers a whole event or fight card, pick its single most dramatic fight or moment and tell only that
story; mention another fight only if it changed this one.
Then tell it like a storyteller who was in the crowd, not like a match report: who was expected to win and why, the
moment it turned, how it ended, what it changed. Name the fighters, players or teams in every line about them; call
someone "the champion" or "the challenger" only if the source gives them that title for this event, and remember that
a champion who loses no longer holds the title. Every line must
state something that happened: no filler about buzz, anticipation or atmosphere, no "forever", "made history" or "the
rest is history". A line that only lists results or statistics is a wasted line. Use at most two numbers in the whole
script
(a score counts as one): the most striking ones.
After the opening line, tell the rest in time order; a line that goes back in time says so ("Before the bout…").
The script must say how it ended (who won, the final score or how the fight was stopped) before or in the last line.
Last line: the payoff or the consequence, short and memorable, so the viewer wants to watch again.
Rules:
- Spoken, plain English that reads naturally aloud. Past tense. No "did you know", no questions to the viewer, no
  "subscribe", no betting talk. No symbols or abbreviations (write "versus", "percent", "round three").
- EVERY fact, number, name, date and cause must be stated in the source. If the source is unsure, say "reportedly".
  Do not merge different matches or fights. Do not round or change numbers; write a number as digits only if the
  source does.
title: a title under 60 characters that names the people or teams and only uses facts from the source; no clickbait
words.""",
}

GORSEL_KURALI = {
    "tuhaf": "The illustrator cannot draw writing: never describe anything that carries words or numbers (signs, "
    "neon signs, shop names, banners, placards, posters, slogans, newspapers, documents, maps, plaques, labels, "
    "scoreboards, numbered jerseys, license plates, graffiti) and never quote words. Show a protest through faces and "
    "raised fists, a shop as a lit window full of goods, a court through robes and a gavel. Never show dead bodies, "
    "injuries or blood; show the moment before, or the aftermath through objects and faces. Each "
    "scene shows one place at one moment from one camera: never several places, a montage, a split view or a "
    "before-and-after in one picture; a scene that jumps to the present day describes the present-day place fully.",
    "masal": "The illustrator cannot draw writing: never describe anything that carries words. Animals look like real "
    "animals with natural anatomy and expressive faces, not cartoon mascots; no clothes unless the fable says so. "
    "Never show blood, wounds or a dead body; show the moment before, or the aftermath through faces. Each "
    "scene shows one place at one moment from one camera: never several places, a montage, a split view or a "
    "before-and-after in one picture.",
    # K-37: yayın görüntüsü yok, gerçek kişinin benzeri de çizilmez (sporcular adsız figür); marka/logo yok
    "spor": "The illustrator cannot draw writing: never describe anything that carries words or numbers (signs, "
    "banners, scoreboards, numbered shirts, tickets, newspapers, trophies with engravings) and never quote words. "
    "Never try to draw a real, recognizable person: every athlete, coach and referee is an anonymous figure described "
    "only by build, hair, skin tone and the colors of their kit, shorts or gloves, and real names never appear in an "
    "image description, a cast name or a cast look: name the cast by side and kit color (the fighter in red, the "
    "fighter in blue, the striker in white, the keeper in green), never by a title such as champion, challenger or "
    "favorite, and write the real athlete or team only in the cast's person field. Give each figure the real "
    "athlete's skin tone, build and hair at that event; never change them to tell two figures apart: the kit colors "
    "do that. Role names are for the illustrator only; spoken lines always use the real names. Kits are plain "
    "solid colors: no logos, crests, badges, sponsor marks or league branding. Never show blood, cuts, swollen faces "
    "or injuries: show a punch as motion and the crowd's reaction, a fallen fighter from behind, a referee stepping "
    "in. Each scene shows one place at one moment from one camera: "
    "never several places, a montage, a split view or a before-and-after in one picture.",
}

# İlk kare kaydırmayı durdurmalı (Shorts feed'inde küçük resim yok; ilk saniye izlendi/kaydırıldı oranını belirler)
ILK_KARE = {
    "tuhaf": "The first scene's image must stop a scrolling viewer: a close, bold, dramatic composition with one clear "
    "subject that shows what the opening line says.",
    "masal": "The first scene's image must stop a scrolling viewer: a close, dramatic portrait of the main animal in "
    "the moment the opening line describes, one clear subject, strong light.",
    "spor": "The first scene's image must stop a scrolling viewer: the peak of the action in a close, low-angle shot "
    "(a fist in mid-swing, a ball leaving a boot, a keeper at full stretch), hard arena light, one clear subject.",
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
  who (the cast name), from_scene (first scene number showing the new look), look (the complete new look in positive,
  visible words: what the viewer SEES, e.g. "a tailless red fox with a round bare rump"; the illustrator cannot draw
  "gone", "without" or "no"; a second change of the same character repeats what still holds from the first, e.g. "a
  tailless red fox wearing a small golden crown"), question (a yes/no question about one picture that checks it, e.g.
  "Does the red fox have a tail?"; if a later change undoes an earlier one, reuse the earlier question word for word),
  expected (the correct answer from from_scene on). The cast description shows the look at the start and does not
  mention the feature that changes. Empty list if no look changes.
mood: the music mood that fits the story."""

HAKEM_ISTEM = {
    "tuhaf": """You are a strict fact checker. SOURCE (the only truth):
<<<
{metin}
>>>
TITLE: {baslik}
SCRIPT LINES:
{satirlar}
OPENING (line 1 was written to this instruction; do not flag line 1 for following it): {acilis}

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
OPENING (line 1 was written to this instruction; do not flag line 1 for following it): {acilis}

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
# spor: aynı olgu hakemi + sonuç ve unvan denetimi. Ortak istemle Rumble in the Jungle (10-26 denemesi) "Ali won by
# knockout, the champion retained his title" satırını temiz geçti: şampiyon Foreman'dı, unvan el değiştirdi.
HAKEM_ISTEM["spor"] = HAKEM_ISTEM["tuhaf"].replace(
    " Return only real problems.",
    """
Sports results are where scripts go wrong. For every line check who won and who lost, the score, the round or minute,
the method, and who held which title or status before and after the event: a champion who loses no longer holds the
title, and a challenger who wins becomes the champion. Flag "the champion", "the challenger", "the favorite" or "the
underdog" when it points to the wrong person, or when the line does not make clear who it means. Flag the last line
if no line says how it ended (who won, the final score or how the fight was stopped).
First fill "result" from the SOURCE alone (who won, who lost, how it ended, who held the title or status before and
after; "none" if there was no title), then check every line against it.
Return only real problems.""",
)

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
# Bir karede birden çok mekân: klein kareyi panellere bölüyor (Ganesha 10-16, "Three separate temples in different
# settings"). Sayı + "ayrı/farklı" yalnız mekân adıyla işaretlenir: "three distinct dogs" tek sahnedir.
COK_YER = re.compile(
    r"\b(?:two|three|four|five|several|multiple|many)\s+(?:separate|different|distinct)\s+(?:temples|churches|"
    r"cities|towns|villages|countries|places|settings|locations|scenes|rooms|buildings|streets|moments|eras|views)\b|"
    r"\bsplit[- ]?screen\b|\bmontages?\b|\bcollages?\b|\btriptych\b|\bdiptych\b|\bbefore[- ]and[- ]after\b|"
    r"\bin (?:different|various|several) (?:cities|countries|places|settings|locations|temples|towns|rooms)\b",
    re.I,
)
COK_YER_NEDEN = "several places in one picture"
GORSEL_TUR = 2
TARIF_KELIME = 8  # onarımdan dönen tarif bundan kısaysa özgün tarif kalır
# virgülde de biter: "without a hat, holding a protest placard" pankartı da siliyordu (10-13 ikinci denetim)
OLUMSUZ = re.compile(r"\b(?:no|without|never|not any)\b[^.;:,]*", re.I)
# Forma takım adı basılıyor; "jersey" karakter tarifinde durunca onarım ona dokunmuyordu ("tarifi değiştirme"), iki tur
# boşa gitti (Bartman, 10-12). Kodla düz forma yapılır, karakter tarifinde de. Büyük harfli "Jersey" ve "New jersey"
# yer adıdır (New Jersey, Jersey Devil havuzda): dokunulmaz.
GIYSI = [(re.compile(r"\bnumbered\s+", re.I), ""), (re.compile(r"(?<!New )\bjersey(s?)\b"), r"uniform\1")]

GORSEL_ONARIM_ISTEM = """These are illustration descriptions for a short video. The illustrator cannot draw writing:
anything that carries words or numbers comes out as garbled letters. It also splits a picture that shows several
places into comic panels.
WORLD: {dunya}
SCENES:
{sahneler}

FLAGGED (object that would carry writing, or "several places in one picture"):
{sorun}

Rewrite the world and ONLY the flagged scenes so the same moment is shown without the flagged objects. Do not mention
them at all, not even as blank, plain, unmarked or wordless versions: the illustrator writes on any sign, banner or
paper it is given. Show the moment through people, faces, gestures, clothing, light and setting instead (a protest =
a crowd with raised fists; a vote = a hand dropping a folded slip into a wooden box; a shop = a lit window full of
goods; colored light instead of neon signs). Do not quote words. Keep every character description and everything
else unchanged. For each flagged scene return its complete new description (who, doing what, where, camera angle),
never a reference like "same as before" or "SCENE 2". A scene flagged "several places in one picture" shows ONE
place at ONE moment: pick the most telling one (three temples in three countries = one crowd at one temple)."""
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
# spor hakemi önce sonucu kaynaktan yazar, sonra satırları ona göre işaretler: düz şemayla aynı satırı 3 denemenin
# 2'sinde yakaladı (Rumble in the Jungle, 10-26); alan sırası modelin düşünme sırasıdır
SORUN_SEMA_SPOR = {
    "type": "object",
    "properties": {
        "result": {
            "type": "object",
            "properties": {
                "winner": {"type": "string"},
                "loser": {"type": "string"},
                "how": {"type": "string"},
                "title_before": {"type": "string"},
                "title_after": {"type": "string"},
            },
            "required": ["winner", "loser", "how", "title_before", "title_after"],
        },
        **SORUN_SEMA["properties"],
    },
    "required": ["result", "problems"],
}
# Spor hakemi iki kez sorulur, bulgular birleşir: tek çağrı yanlış sonucu 5 denemenin 1'inde kaçırdı (10-26). Yanlış
# skor/kazanan kanalı götürür; fazladan işaret yalnız bir onarım turuna mal olur. Ara turda ikinci çağrı yalnız temiz
# görünen senaryoya gider (bulunan sorun zaten onarıma gidiyor): 10-27/28'in dört spor videosu dört turun hepsini
# kullandı, ikinci çağrılar video başına ~3.100 neuron'un ~500'üydü ve günde 3 video bedava 10.000'e sığmadı.
HAKEM_TEKRAR = {"spor": 2}
# Ertelenen ikinci çağrının bulgusu bir tur sonra onarılır: spor senaryosu bir tur fazla alır (tur yalnız gerekirse
# harcanır; düşen hikâye yenisinin bütün maliyetine mal olur)
EK_TUR = {"spor": 1}
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
SAHNE_SAYISI = {"tuhaf": (7, 8), "masal": (7, 7), "spor": (7, 8)}
KELIME = {"tuhaf": (60, 100), "masal": (50, 95), "spor": (60, 100)}  # toplam kelime; dışı onarıma girer
OLGU_TURLERI = ("tuhaf", "spor")  # gerçek olay: sayı/ad kapısı ve sayı sınırı
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
    # spor: kadro adı → canlandırdığı gerçek kişi/takım (çizere gitmez) ve görünüş denetiminin düzelttikleri
    kisiler: dict[str, str] = field(default_factory=dict)
    kadro_onarim: list[list[str]] = field(default_factory=list)  # [ad, eski görünüş, yeni görünüş]


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
                    "properties": {
                        "name": {"type": "string"},
                        "look": {"type": "string"},
                        **({"person": {"type": "string"}} if tur in KADRO_DENETIMI else {}),
                    },
                    "required": ["name", "look", *(["person"] if tur in KADRO_DENETIMI else [])],
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
    k_duz = _aksansiz(k)
    for m in re.finditer(r"\b[^\W\d_]{3,}\b", metin):
        ad = m.group()
        # büyük harfle başlayıp küçükle süren her kelime (Unicode: "Pérez", "Émile", "McDonald" eskiden hiç
        # denetlenmiyordu); cümle başı ad sayılmaz, unvandan sonrası sayılır ("hired Dr. Grayson")
        if not (ad[0].isupper() and ad[1].islower()) or ad in TAKVIM:  # gün/ay adını hakem denetler
            continue
        once = metin[: m.start()]
        if (not once.strip() or re.search(r"[.!?:\"“”]\s$", once)) and not UNVAN.search(once):
            continue
        # kısa ad tam kelime ("Tom" kaynaktaki "tomorrow"dan geçiyordu), uzun ad kelime başında kök (Londoners →
        # london); aksan iki yanda da düşer: kaynaktaki "Ténéré" için yazılan "Tenere" uydurma sayılıyordu
        kok = _aksansiz(ad.lower() if len(ad) <= 4 else ad.lower()[: max(5, len(ad) - 3)])
        kalip = rf"\b{re.escape(kok)}\b" if len(ad) <= 4 else rf"\b{re.escape(kok)}"
        if not re.search(kalip, k_duz):
            hata.append(f"name not in source: {ad}")
    return hata


UNVAN = re.compile(r"\b(?:Mr|Mrs|Ms|Dr|St|Mt|Ft|Capt|Col|Gen|Gov|Lt|Sgt|Rev|Prof|Sr|Jr)\.\s$")
# Model kaynağın kendi cümlesini taşıyordu: Montauk kartı (10-19) "The article speculated it might be a secret
# experiment" dedi; Wikipedia'daki "The light-hearted article" bir gazete yazısıydı, izleyici hangi makale olduğunu
# bilmiyor. Hakem bunu olgu olarak doğru buldu. "the article" ancak önce bir yazı anıldıysa serbest.
KAYNAK_ADI = re.compile(r"\b(?:wikipedia|this (?:article|entry)|the (?:wiki|source) (?:says|states|notes)|"
                        r"according to the (?:source|article))\b", re.I)  # fmt: skip
# "the story"/"the piece" anlatımın kendisinde geçiyor ("The story spread", "a piece of wood"), yazı sayılmaz
ASILI_YAZI = re.compile(r"\bthe (?:article|report)\b", re.I)
YAZI_ANILDI = re.compile(
    r"\b(?:an?|newspaper|magazine|news|local|its|his|her|their)\s+(?:[\w'-]+\s+)?(?:article|report)\b", re.I
)


def kaynak_gondermesi(satirlar: list[str]) -> list[tuple[int, str]]:
    """(satır sırası, sorun): metin kaynak belgeye ya da hiç anılmamış bir yazıya gönderme yapıyor."""
    sorun = []
    for i, s in enumerate(satirlar):
        if m := KAYNAK_ADI.search(s):
            sorun.append((i, f'do not refer to the source document ("{m.group()}"); tell the story itself'))
        elif (m := ASILI_YAZI.search(s)) and not YAZI_ANILDI.search(" ".join([*satirlar[:i], s[: m.start()]])):
            sorun.append((i, f'"{m.group()}" was never introduced; say whose it was (e.g. "a local newspaper")'))
    return sorun


def _aksansiz(metin: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", metin) if not unicodedata.combining(c))


def kod_kontrolu(tur: str, baslik: str, satirlar: list[str], kaynak: str) -> list[tuple[int, str]]:
    from otomat.hikaye.kaynaklar import HAKARET

    sorun = []
    if not BASLIK_UZUNLUK[0] <= len(baslik.strip()) <= BASLIK_UZUNLUK[1]:  # onarım başlığı boşaltabiliyor
        sorun.append((0, f"the title must be {BASLIK_UZUNLUK[0]}-{BASLIK_UZUNLUK[1]} characters"))
    # hakaret kabulde render'dan sonra yakalanıyordu: kota harcanmadan onarıma gitsin
    for i, s in enumerate([baslik, *satirlar]):
        if bulunan := HAKARET.findall(s):
            sorun.append((i, f"remove the slur or profanity: {', '.join(bulunan)}"))
    if tur in OLGU_TURLERI:
        sorun += [(i, h) for i, s in enumerate([baslik, *satirlar]) for h in sayi_ad_kapisi(s, kaynak, adlar=i > 0)]
        # sayı yığını hikâyeyi ölçü listesine çeviriyordu (Molasses: "50-foot, 90-foot tank held 2.3 million gallons").
        # Yalnız son sayılı satır işaretlenince onarım öbürlerine dokunmuyordu, sorun 4 turda kapanmadı (Loret, 10-12).
        sayili = [i for i, s in enumerate(satirlar, 1) for _ in re.findall(r"\d[\d,.]*", s)]
        if len(sayili) > SAYI_SINIRI:
            sorun += [(n, f"the script has {len(sayili)} numbers but may hold only {SAYI_HEDEF}; tell this line "
                          "without its number") for n in dict.fromkeys(sayili[SAYI_HEDEF:])]  # fmt: skip
    sorun += kaynak_gondermesi([baslik, *satirlar])
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


def cok_yerliler(gorseller: list[str]) -> list[tuple[int, str]]:
    """(sahne no, neden): tek karede birden çok mekân isteyen tarifler (dünya cümlesi bir mekân/dönem, sayılmaz)."""
    return [(i, COK_YER_NEDEN) for i, g in enumerate(gorseller, 1) if COK_YER.search(g)]


def _gorsel_sorunlari(sc) -> list[tuple[int, str]]:
    sorun = dict(yazi_tasiyanlar(sc.dunya, sc.gorseller))
    for n, r in cok_yerliler(sc.gorseller):
        sorun[n] = f"{sorun[n]}; {r}" if n in sorun else r
    return sorted(sorun.items())


def _yan_cumleler(metin: str) -> list[str]:
    """Ayraçlarıyla birlikte yan cümleler: parantez dışındaki virgül/noktalı virgül ve cümle sonu ("2.3" bölünmez)."""
    parca, derinlik, bas = [], 0, 0
    for i, c in enumerate(metin):
        derinlik += (c == "(") - (c == ")")
        if derinlik == 0 and (c in ",;" or (c == "." and metin[i + 1 : i + 2] in (" ", ""))):
            parca.append(metin[bas : i + 1])
            bas = i + 1
    return [p for p in [*parca, metin[bas:]] if p.strip()]


def yazisiz(metin: str, en_az: int = TARIF_KELIME) -> str:
    """Yazı taşıyan nesne geçen yan cümleler düşer ("…; the scoreboard shows the run tally climbing"). Olumsuz kalıp
    ("no text, no signs") sayılmaz; geriye `en_az` kelimeden kısa tarif kalırsa metin aynen döner."""
    kalan = "".join(p for p in _yan_cumleler(metin) if not YAZI_TASIYAN.search(OLUMSUZ.sub("", p))).strip()
    kalan = kalan.rstrip(",;").rstrip()
    if len(kalan.split()) < en_az:
        return metin
    return kalan if kalan.endswith(".") else kalan + "."


def giysi_duz(metin: str) -> str:
    for desen, yerine in GIYSI:
        metin = desen.sub(yerine, metin)
    return metin


def _kadro_yazisiz(oyuncu: str) -> str:
    """Kadro tarifi karakterin geçtiği her sahne istemine girer ("a newsboy holding a stack of newspapers" her karede
    anlamsız yazı çizdirirdi): yazı taşıyan yan cümle düşer, ad kalır."""
    ad, ayrac, tarif = oyuncu.partition(":")
    return f"{ad}{ayrac} {yazisiz(tarif.strip(), en_az=2)}" if ayrac else oyuncu


def gorsel_temizle(sc: Senaryo) -> None:
    """Tarifte yazı taşıyan nesne ya da birden çok mekân varsa en çok GORSEL_TUR onarım turu; ikinci tur yalnız hâlâ
    işaretli kalanları gönderir. Onarımdan sonra da işaretli kalan tarifin yazı taşıyan yan cümlesi kodla düşer:
    Bartman'da (10-12) iki tur hiçbir şeyi değiştirmedi, skor tabelası anlamsız harflerle çizildi. Kalan yazıyı
    üretimde OCR (yazi.py), kalan paneli piksel denetimi (panel.py) yakalar."""
    sc.dunya, sc.gorseller, sc.oyuncular = (
        giysi_duz(sc.dunya),
        [giysi_duz(g) for g in sc.gorseller],
        [_kadro_yazisiz(giysi_duz(o)) for o in sc.oyuncular],
    )
    if not (ilk := _gorsel_sorunlari(sc)):
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
        if not (sorun := _gorsel_sorunlari(sc)):
            break
    for n, _ in yazi_tasiyanlar(sc.dunya, sc.gorseller):
        if n == 0:
            sc.dunya = yazisiz(sc.dunya)
        else:
            sc.gorseller[n - 1] = yazisiz(sc.gorseller[n - 1])
    sorun = _gorsel_sorunlari(sc)
    sc.gorsel_onarim = [[[n, r] for n, r in ilk], [[n, r] for n, r in sorun]]


def _numarali(satirlar: list[str]) -> str:
    return "\n".join(f"{i}. {s}" for i, s in enumerate(satirlar, 1))


def _hakem(
    tur: str, kisa: str, baslik: str, satirlar: list[str], kalip: str, ara: bool = False, kirli: bool = False
) -> list[tuple[int, str]]:
    """Hakem açılış kalıbını görür: `sonuc_once` sonucu, `ders` dersi baştan söyler; hakem bunu "sonu baştan
    veriyor" diye işaretleyince kanca onarıma gidip kalıbını kaybediyordu. Aralık dışı satır numarası düşer: onarım
    onu hiç düzeltemez, senaryo boşuna düşerdi. `ara`: ara turda tekrar çağrısı yalnız ilk çağrı (ve `kirli` ise kod
    kontrolü) temiz bulduysa yapılır; kabul edilen senaryo her zaman bütün çağrılardan geçmiş olur."""
    istem = HAKEM_ISTEM[tur].format(metin=kisa, baslik=baslik, satirlar=_numarali(satirlar), acilis=KALIPLAR[kalip])
    sorun: list[tuple[int, str]] = []
    for i in range(HAKEM_TEKRAR.get(tur, 1)):
        if i and ara and (kirli or sorun):
            break
        h = cf.sohbet(istem, SORUN_SEMA_SPOR if tur == "spor" else SORUN_SEMA)
        onceki = {n for n, _ in sorun}
        # ikinci çağrı yalnız ilkinin işaretlemediği satırları ekler: aynı satır iki kez onarıma gitmesin
        sorun += [(p["line"], p["reason"]) for p in h["problems"]
                  if 0 <= p["line"] <= len(satirlar) and (i == 0 or p["line"] not in onceki)]  # fmt: skip
    return sorun


def satir_cikar(tur: str, sc: Senaryo, sorun: list[tuple[int, str]], kaynak: str, kisa: str, kalip: str) -> bool:
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
    yeni = _hakem(tur, kisa, sc.baslik, satirlar, kalip)
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


def kisalt(kaynak: str, tur: str = "tuhaf") -> str:
    """Uzun makalede sonuç/epilog modele görünsün: düz kesim (`[:6000]`) hikâyenin sonunu atıyordu."""
    if len(kaynak) <= KAYNAK_SINIR:
        return kaynak
    if tur == "spor" and (secilen := _olay_bolumleri(kaynak)):
        return secilen
    return f"{kaynak[: KAYNAK_SINIR - KAYNAK_SON]}\n[...]\n{kaynak[-KAYNAK_SON:]}"


# Spor makalesinde olay ortadadır: baş (arka plan) + son (miras) kesimi maçın kendisini atıyordu (1986
# Arjantin-İngiltere, 14.134 karakter: "Hand of God" bölümü modele hiç gitmedi, senaryo uydurdu ve 4 turda düştü;
# 10-24 denemesi)
OLAY_BASLIGI = re.compile(
    r"\b(?:match|fight|bout|game|first half|second half|extra time|penalt\w*|goal\w*|rounds?|final|summary|"
    r"aftermath|incident|controvers\w*|brawl|result|knockout|decision|legacy|reaction)\b",
    re.I,
)


TABLO_BASLIGI = re.compile(
    r"\b(?:details|scorecards?|results|line-?ups?|statistics|records?|viewership|broadcast\w*|bonus|payouts?|"
    r"undercard|fight card|officials|squads?|attendance|purse|ratings|see also)\b",
    re.I,
)


def _olay_bolumleri(kaynak: str) -> str | None:
    """Giriş + ilk olay başlığından (maç, dövüş, raunt…) itibaren sıradaki anlatı bölümleri, tablo/istatistik bölümleri
    atlanarak, KAYNAK_SINIR'a kadar; olay başlığı yoksa None. Olayın alt başlıkları her zaman anahtar kelime taşımaz
    ("The 'Hand of God'"): ilk olay başlığından sonra sıra izlenir. Düz metin özütünde başlıklar kendi satırındadır
    (kaynaklar.metin, exsectionformat=plain): kısa, noktasız satır."""
    satirlar = kaynak.split("\n")
    bolumler: list[tuple[str, list[str]]] = [("", [])]
    for s in satirlar:
        if 0 < len(s) <= 60 and not s.rstrip().endswith((".", ":", '"', "”")) and len(s.split()) <= 8:
            bolumler.append((s, []))
        else:
            bolumler[-1][1].append(s)
    giris = "\n".join(bolumler[0][1]).strip()
    ilk = next((i for i, (b, _) in enumerate(bolumler) if i and OLAY_BASLIGI.search(b) and not TABLO_BASLIGI.search(b)),
               None)  # fmt: skip
    if ilk is None:
        return None
    olay = [(b, "\n".join(g).strip()) for b, g in bolumler[ilk:] if not TABLO_BASLIGI.search(b) and "".join(g).strip()]
    parcalar, toplam = [giris[:1500]], min(len(giris), 1500)
    for b, g in olay:
        if toplam >= KAYNAK_SINIR:
            break
        g = g[: KAYNAK_SINIR - toplam]
        parcalar.append(f"{b}\n{g}")
        toplam += len(g) + len(b) + 1
    return "\n\n".join(parcalar)


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


KADRO_DENETIMI = ("spor",)
KADRO_ISTEM = """These are the recurring figures of an illustrated short video about the real sports event "{baslik}".
The illustrator never sees who a figure stands for, only its look, so the look alone must match the real person.
{kadro}

For every figure: first write how that real athlete, team or official looked at this event (skin tone, build, hair,
age, sex), then whether you clearly know this (certain: false for a lesser-known person or a whole team), then whether
the given look matches on all of these. If it does not, write the complete new look in plain visual words, keeping its
kit colors and everything else that was right, with no names; if it matches, leave the new look empty."""
# alan sırası düşünme sırası: önce gerçek görünüş, sonra kıyas (düz "fixes" listesi beyaz çizilen Foreman'ı 3/3 geçti).
# `certain`: az bilinen kişide model yanılıyor (UFC 193, 10-26: hakem Herb Dean'i açık tenli yaptı), o zaman dokunulmaz
KADRO_SEMA = {
    "type": "object",
    "properties": {
        "figures": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "real_look": {"type": "string"},
                    "certain": {"type": "boolean"},
                    "matches": {"type": "boolean"},
                    "new_look": {"type": "string"},
                },
                "required": ["name", "real_look", "certain", "matches", "new_look"],
            },
        }
    },
    "required": ["figures"],
}


def _kadro_anahtari(ad: str) -> str:
    """Model kadro adını kısaltıp dönebiliyor ("the challenger" → "challenger")."""
    return re.sub(r"^the\s+", "", ad.strip().lower())


def kadro_denetle(sc: Senaryo, baslik: str) -> None:
    """Kadro gerçek kişinin görünüşüne uyuyor mu (Rumble in the Jungle, 10-26: rol adıyla çizilen Foreman beyaz ve kel
    çıktı; model iki figürü ten rengiyle ayırmıştı). Görünüş kaynakta yazmaz, modelin genel bilgisinden gelir.
    Düzeltilen görünüş sahne tariflerine de kopyalanmışsa orada da değişir."""
    if not sc.kisiler:
        return
    kadro = []
    for o in sc.oyuncular:
        ad, _, tarif = o.partition(":")
        if kisi := sc.kisiler.get(ad.strip()):
            kadro.append(f"- {ad.strip()} = {kisi}; look: {tarif.strip()}")
    if not kadro:
        return
    f = cf.sohbet(KADRO_ISTEM.format(baslik=baslik, kadro="\n".join(kadro)), KADRO_SEMA)
    yeni = {_kadro_anahtari(d["name"]): d["new_look"].strip() for d in f["figures"]
            if d.get("certain") and not d["matches"] and len(d["new_look"].split()) >= DEGISIM_KELIME}  # fmt: skip
    for i, o in enumerate(sc.oyuncular):
        ad, _, tarif = o.partition(":")
        if (gorunum := yeni.get(_kadro_anahtari(ad))) and gorunum != tarif.strip():
            sc.oyuncular[i] = f"{ad.strip()}: {gorunum}"
            sc.gorseller = [g.replace(tarif.strip().rstrip("."), gorunum.rstrip(".")) for g in sc.gorseller]
            sc.kadro_onarim.append([ad.strip(), tarif.strip(), gorunum])


RENKLER = ("red", "blue", "white", "black", "green", "yellow", "gold", "orange", "purple", "gray", "grey", "pink",
           "navy", "maroon", "silver", "brown")  # fmt: skip
SIRA = ("first", "second", "third", "fourth")


def _ozel_adlar(metin: str) -> set[str]:
    """Büyük harfle başlayan kelimeler, küçük harfle ("The Liverpool players" kadro adıyla "the"de eşleşmesin)."""
    return {k.lower() for k in re.findall(r"[^\W\d_]{3,}", metin) if k[0].isupper()} - {"the"}


def adsiz_kadro(sc: Senaryo) -> None:
    """Kadro adı gerçek kişinin adını taşıyorsa (UFC 193, 10-26: "Rousey", "Holm", "Dean") forma rengiyle adsız
    etikete çevrilir ("the figure in red"): ad her sahne istemine girer, çizer gerçek kişinin benzerini dener (K-37).
    Model bu kuralı istemde açıkça yazmasına rağmen çiğnedi. Etiket sahne tariflerinde ve değişimlerde de değişir."""
    kullanilan = {o.partition(":")[0].strip().lower() for o in sc.oyuncular}
    for i, o in enumerate(sc.oyuncular):
        ad, _, tarif = o.partition(":")
        ad = ad.strip()
        kisi = sc.kisiler.get(ad, "")
        if not {k.lower() for k in re.findall(r"[^\W\d_]{3,}", ad)} & _ozel_adlar(kisi):
            continue
        renk = next((r for r in RENKLER if re.search(rf"\b{r}\b", tarif, re.I)), None)
        adaylar = ([f"the figure in {renk}"] if renk else []) + [f"the {s} figure" for s in SIRA]
        yeni = next(a for a in adaylar if a not in kullanilan)
        kullanilan.add(yeni)
        desen = re.compile(rf"\b{re.escape(ad)}\b", re.I)
        sc.oyuncular[i] = f"{yeni}: {tarif.strip()}"
        sc.gorseller = [desen.sub(yeni, g) for g in sc.gorseller]
        sc.dunya = desen.sub(yeni, sc.dunya)
        for d in sc.degisimler:
            if d["kim"] == ad:
                d["kim"] = yeni
        sc.kisiler[yeni] = sc.kisiler.pop(ad)


def yaz(tur: str, baslik: str, kaynak: str, konu: str, kalip: str, moodlar: list[str]) -> Senaryo:
    kisa = kisalt(kaynak, tur)
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
    if tur in KADRO_DENETIMI:
        sc.kisiler = {str(o["name"]).replace(":", " ").strip(): str(o.get("person", "")).strip()
                      for o in s["cast"] if isinstance(o, dict) and str(o.get("person", "")).strip()}  # fmt: skip
        adsiz_kadro(sc)
    tur_sayisi = TUR_SAYISI + EK_TUR.get(tur, 0)
    for tur_no in range(tur_sayisi):
        son = tur_no == tur_sayisi - 1
        kod = kod_kontrolu(tur, sc.baslik, sc.satirlar, kaynak)
        sorun = kod + _hakem(tur, kisa, sc.baslik, sc.satirlar, kalip, ara=not son, kirli=bool(kod))
        sc.turlar.append([[n, r[:300]] for n, r in sorun])
        if not sorun or (son and satir_cikar(tur, sc, sorun, kaynak, kisa, kalip)):
            kadro_denetle(sc, baslik)  # yalnız geçen senaryoya: düşecek senaryoya kota harcanmasın
            gorsel_temizle(sc)
            return sc
        if son:
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
    raise SenaryoHatasi(f"senaryo {tur_sayisi} turda hakemden geçmedi", sc.turlar)
