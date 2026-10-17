"""Film senaryosu: bölüm → blok (bir anlatım parçası) → sahne (bir çekim). JSON'dan okunur ve üretimden önce denetlenir;
kusurlu senaryo GPU saatini yakmadan düşer."""

import json
from dataclasses import dataclass, field
from pathlib import Path

HAREKETLER = {"iceri", "disari", "sol", "sag", "yukari", "i2v"}
EN_COK_REFERANS = 3  # FLUX.2 klein 4 referans alır; biri ileride stil kartına ayrılsın
MOODLAR = {"tragic", "mysterious", "epic", "funny"}
# Karakter tasarımı istemde dururken model nesnelere de yüz çiziyor: gemi, pervane, mum, buzdağı, saat (pilot, 10-17).
# "Yüzsüz" cümlesi tek başına yetmedi (baca, lamba, mum yine yüzlü); insansız sahneye tasarım hiç gönderilmez.
YUZSUZ = "Ships, objects, machines, animals, plants, buildings and landscapes have no faces, no eyes and no mouths"


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

    def bloklar(self) -> list[tuple[int, Blok]]:
        return [(i, b) for i, bo in enumerate(self.bolumler) for b in bo.bloklar]

    def sahneler(self) -> list[Sahne]:
        return [s for _, b in self.bloklar() for s in b.sahneler]

    def kelime(self) -> int:
        return sum(len(b.anlatim.split()) for _, b in self.bloklar())


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
    return Film(
        slug=d["slug"], baslik=d["baslik"], kapak_yazi=d["kapak_yazi"], kapak_sahne=d["kapak_sahne"],
        kapak_kim=kapak_kim, stil=d["stil"], insan=d["insan"], ses=d.get("ses", "bm_george"),
        hiz=float(d.get("hiz", 1.0)),
        karakterler=karakterler, bolumler=tuple(bolumler), kaynaklar=tuple(d.get("kaynaklar", ())),
    )  # fmt: skip


def karakter_istemi(film: Film, ad: str) -> str:
    return (
        f"{film.stil}. {film.insan}. Character reference sheet: {film.karakterler[ad]}. Standing full body, "
        "front view, centered, on a plain flat dark charcoal background. Neutral calm expression."
    )


def sahne_istemi(film: Film, s: Sahne) -> str:
    if s.kisi:
        return f"{film.stil}. {film.insan}. {YUZSUZ}. {s.tarif}"
    return f"{film.stil}. An empty scene with no people and no characters. {YUZSUZ}. {s.tarif}"
