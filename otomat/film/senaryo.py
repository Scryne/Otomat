"""Film senaryosu: bölüm → blok (bir anlatım parçası) → sahne (bir çekim). JSON'dan okunur ve üretimden önce denetlenir;
kusurlu senaryo GPU saatini yakmadan düşer."""

import json
import re
from dataclasses import dataclass, field, replace
from pathlib import Path

HAREKETLER = {"iceri", "disari", "sol", "sag", "yukari", "i2v"}
EN_COK_REFERANS = 3  # FLUX.2 klein 4 referans alır; biri ileride stil kartına ayrılsın
MOODLAR = {"tragic", "mysterious", "epic", "funny"}
# Karakter tasarımı istemde dururken model nesnelere de yüz çiziyor: gemi, pervane, mum, buzdağı, saat (pilot, 10-17).
# "Yüzsüz" cümlesi tek başına yetmedi (baca, lamba, mum yine yüzlü); insansız sahneye tasarım hiç gönderilmez.
YUZSUZ = "Ships, objects, machines, animals, plants, buildings and landscapes have no faces, no eyes and no mouths"
# Wan'a yüz hareketi (göz, kaş, gülümseme) istenince nokta gözler siliniyor (10-18 A/B): hareket bedende ve ortamda olur
YUZ_HAREKETI = re.compile(
    r"\b(eyes?|eyebrows?|blink\w*|wink\w*|frown\w*|smil\w*|winc\w*|grin\w*|mouth|lips|expression|swallow\w*)\b", re.I
)


class SenaryoHatasi(ValueError):
    pass


@dataclass(frozen=True)
class Sahne:
    tarif: str
    hareket: str
    kim: tuple[str, ...] = ()
    i2v: str = ""
    yazi: str = ""
    kisi: bool = False  # referanssız ama insan içeren sahne (kalabalık, doktor): karakter tasarımı istemine girer


@dataclass(frozen=True)
class Blok:
    anlatim: str
    sahneler: tuple[Sahne, ...]


@dataclass(frozen=True)
class Bolum:
    ad: str
    mood: str
    bloklar: tuple[Blok, ...]


@dataclass(frozen=True)
class Film:
    slug: str
    baslik: str
    kapak_yazi: str
    kapak_sahne: str
    kapak_kim: tuple[str, ...]
    stil: str  # dünyanın çizimi
    insan: str  # yalnız insanlara uygulanan karakter tasarımı
    ses: str
    hiz: float
    karakterler: dict[str, str]
    bolumler: tuple[Bolum, ...]
    kaynaklar: tuple[dict, ...] = field(default_factory=tuple)
    ozet: str = ""  # açıklamanın ilk satırları (aramada görünen kısım); yoksa başlık
    etiketler: tuple[str, ...] = ()  # YouTube etiketleri (yükleme)
    kesitler: tuple["Kesit", ...] = ()  # filmden dikey Shorts

    def bloklar(self) -> list[tuple[int, Blok]]:
        return [(i, b) for i, bo in enumerate(self.bolumler) for b in bo.bloklar]

    def sahneler(self) -> list[Sahne]:
        return [s for _, b in self.bloklar() for s in b.sahneler]

    def kelime(self) -> int:
        return sum(len(b.anlatim.split()) for _, b in self.bloklar())


@dataclass(frozen=True)
class Kesit:
    baslik: str  # Shorts başlığı ve ekrandaki üst yazı
    ilk: int  # film.bloklar() içindeki ilk ve son blok (dahil)
    son: int


def _kesitler(ham: list[dict], bloklar: list[tuple[int, Blok]]) -> tuple[Kesit, ...]:
    """Kesit tek bölümün ardışık bloklarıdır: bölüm geçişi araya kart sokar, Shorts'ta boş ekran olur."""
    sonuc = []
    for i, k in enumerate(ham):
        ilk, son = k["bloklar"]
        if not (0 <= ilk <= son < len(bloklar)):
            raise SenaryoHatasi(f"kesit {i}: blok aralığı {ilk}-{son} geçersiz ({len(bloklar)} blok)")
        if bloklar[ilk][0] != bloklar[son][0]:
            raise SenaryoHatasi(f"kesit {i}: bloklar {ilk}-{son} iki bölüme yayılıyor")
        if not k.get("baslik", "").strip():
            raise SenaryoHatasi(f"kesit {i}: başlık yok")
        sonuc.append(Kesit(k["baslik"].strip(), ilk, son))
    return tuple(sonuc)


def _sahne(s: dict, karakterler: dict, yer: str) -> Sahne:
    hareket = s.get("hareket", "iceri")
    if hareket not in HAREKETLER:
        raise SenaryoHatasi(f"{yer}: bilinmeyen hareket '{hareket}'")
    kim = tuple(s.get("kim", ()))
    if bilinmeyen := [k for k in kim if k not in karakterler]:
        raise SenaryoHatasi(f"{yer}: tanımsız karakter {bilinmeyen}")
    if len(kim) > EN_COK_REFERANS:
        raise SenaryoHatasi(f"{yer}: en çok {EN_COK_REFERANS} karakter referansı")
    if hareket == "i2v" and not s.get("i2v", "").strip():
        raise SenaryoHatasi(f"{yer}: i2v sahnesinin hareket istemi yok")
    if hareket == "i2v" and (m := YUZ_HAREKETI.search(s["i2v"])):
        raise SenaryoHatasi(f"{yer}: i2v istemi yüz hareketi istiyor ({m.group(0)}); hareketi bedene ver")
    if kim and "reference image" not in s["tarif"]:
        # model referansı ancak istemde anılınca karaktere bağlıyor (spike 10-17)
        raise SenaryoHatasi(f"{yer}: referanslı sahnenin tarifi 'reference image' demiyor")
    return Sahne(
        s["tarif"].strip(),
        hareket,
        kim,
        s.get("i2v", "").strip(),
        s.get("yazi", "").strip(),
        bool(kim or s.get("kisi")),
    )


def oku(yol: Path) -> Film:
    d = json.loads(Path(yol).read_text(encoding="utf-8"))
    karakterler = d["karakterler"]
    bolumler = []
    for i, bo in enumerate(d["bolumler"]):
        if bo.get("mood") not in MOODLAR:
            raise SenaryoHatasi(f"bölüm {i}: mood '{bo.get('mood')}' {sorted(MOODLAR)} içinde değil")
        bloklar = []
        for j, b in enumerate(bo["bloklar"]):
            if not b.get("anlatim", "").strip():
                raise SenaryoHatasi(f"bölüm {i} blok {j}: anlatım boş")
            if not b.get("sahneler"):
                raise SenaryoHatasi(f"bölüm {i} blok {j}: sahne yok")
            sahneler = tuple(
                _sahne(s, karakterler, f"bölüm {i} blok {j} sahne {k}") for k, s in enumerate(b["sahneler"])
            )
            bloklar.append(Blok(" ".join(b["anlatim"].split()), sahneler))
        bolumler.append(Bolum(bo["ad"], bo["mood"], tuple(bloklar)))
    kapak_kim = tuple(d.get("kapak_kim", ()))
    if bilinmeyen := [k for k in kapak_kim if k not in karakterler]:
        raise SenaryoHatasi(f"kapak: tanımsız karakter {bilinmeyen}")
    film = Film(
        slug=d["slug"], baslik=d["baslik"], kapak_yazi=d["kapak_yazi"], kapak_sahne=d["kapak_sahne"],
        kapak_kim=kapak_kim, stil=d["stil"], insan=d["insan"], ses=d.get("ses", "bm_george"),
        hiz=float(d.get("hiz", 1.0)),
        karakterler=karakterler, bolumler=tuple(bolumler), kaynaklar=tuple(d.get("kaynaklar", ())),
        ozet=d.get("ozet", "").strip(), etiketler=tuple(d.get("etiketler", ())),
    )  # fmt: skip
    return replace(film, kesitler=_kesitler(d.get("kesitler", []), film.bloklar()))


def karakter_istemi(film: Film, ad: str) -> str:
    return (
        f"{film.stil}. {film.insan}. Character reference sheet: {film.karakterler[ad]}. Standing full body, "
        "front view, centered, on a plain flat dark charcoal background. Neutral calm expression."
    )


def sahne_istemi(film: Film, s: Sahne) -> str:
    if s.kim:
        # referans yalnız kendi karakterini bağlıyor; yanındaki kalabalık ve yan karakterler burunlu, yarı gerçekçi
        # çıktı (pilot 23, 36, 42, 75, 87)
        # kartın tarifi metinde de durmazsa küçük ayrıntılar (gözlük, şapka) düşüyor: Klondike'ta "sen" 103 sahnenin
        # çoğunda gözlüksüz, Dawson'da şapkasız ve kel çıktı
        kartlar = " ".join(f"The reference character is {film.karakterler[k]}." for k in s.kim)
        return (
            f"{film.stil}. {film.insan}. Every other person in the scene is drawn in exactly the same simple style as "
            f"the reference character, with the same round cream-white head, dot eyes and no nose. {YUZSUZ}. "
            f"{kartlar} {s.tarif}"
        )
    if s.kisi:
        return f"{film.stil}. {film.insan}. {YUZSUZ}. {s.tarif}"
    return f"{film.stil}. An empty scene with no people and no characters. {YUZSUZ}. {s.tarif}"


def i2v_istemi(s: Sahne) -> str:
    """Wan göz/kaş hareketi istenince nokta gözleri siliyor (10-18 A/B, sahne 3): yüz sabit, hareket bedende. İnsansız
    sahnede "the second hand ticks" bir insan eli getirdi (pilot 40, 63); kadraja yeni bir şey girmez."""
    if s.kisi:
        ek = " Faces keep the same simple dot eyes and eyebrows. Nothing new enters the frame."
    else:
        ek = " No people and no hands appear. Nothing new enters the frame."
    return f"{s.i2v}{ek} Minimalist flat 2D cartoon animation, clean outlines, consistent character design."
