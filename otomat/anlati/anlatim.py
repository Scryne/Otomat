"""Anlatım: kanca + başlık (LLM, yer tutuculu) ve olgu cümleleri (kod) → kapılardan geçmiş metin."""

import re
import zlib
from dataclasses import dataclass, field

from otomat import kanal
from otomat.anlati import kapilar, olgu_cumleleri, yedek
from otomat.anlati.llm import LLMHatasi, json_uret
from otomat.veri import OlguPaketi

TUM_KALIPLAR = {
    "soru": "a curiosity question the viewer wants answered (do not answer it)",
    "senin_ulken": "a personal angle that makes viewers look for their own country or region",
    "duygusal": "a vivid but calm emotional angle (wonder, surprise), no fear or sensational words",
    "olcek": "a scale angle: how big, how often or how uneven it is",
    "kiyas": "compare the subject with something familiar that the facts name (the Moon, Earth, Jupiter)",
}
# Kanalın kanca kalıpları (haydudun kanca kolu): profilde `kaliplar`; yoksa Earth'ün dördü. Hikâye kanallarının
# kalıpları otomat/hikaye/senaryo.py'de; o kanallarda bu sözlük boş kalır.
KALIPLAR = {k: TUM_KALIPLAR[k] for k in kanal.aktif().kaliplar if k in TUM_KALIPLAR}
SEMA = {
    "type": "object",
    "properties": {"hook": {"type": "string"}, "title": {"type": "string"}},
    "required": ["hook", "title"],
}
DENEME = 3
GIZLI = {"days", "from_year", "to_year", "year", "scope", "countries_compared"}  # LLM'e doğal düşmeyen tutucular


def _ornekler() -> str:
    """Üslup örnekleri kanal profilinden (kanallar/<id>/kanal.toml)."""
    return f"Examples of the style (different topics, do not copy):\n{kanal.aktif().ornekler}\n"


@dataclass
class Anlatim:
    kanca: str  # doldurulmuş, ekranda
    baslik: str  # doldurulmuş, video başlığı ve ekran başlığı
    cumleler: list[str]  # olgu cümleleri, ekranda (altyazı)
    kalip: str
    varyant: int
    denemeler: list[dict] = field(default_factory=list)  # kapı geçmişi (rapor için)
    kaynak: dict[str, str] = field(default_factory=dict)  # {"hook": "llm"|"yedek", "title": ...}

    @property
    def ses_cumleleri(self) -> list[str]:
        return [seslendir(c) for c in [self.kanca, *self.cumleler]]


# Kokoro'nun yanlış okuduğu yer adları; ekranda asıl ad kalır. 175 adın TTS → Whisper taramasıyla bulundu (2026-10-04):
# "Türkiye" → "Tuakii", "Timor-Leste" → "T-MoreLest", "Nauru" → "Now who", "Palau" → "Palo", "U.S." → durak.
OKUNUS = {
    "Türkiye": "Tur-kee-yay",
    "Timor-Leste": "Timor Lesh-tay",
    "Nauru": "Na-oo-roo",
    "Palau": "Pa-lau",
    "U.S.": "US",
}


def seslendir(metin: str) -> str:
    """Ekran metnini TTS'in kararsız okuduğu kalıplardan arındır (ekranda '1.6', seste '1 point 6')."""
    m = metin
    for ad, okunus in OKUNUS.items():
        m = re.sub(rf"(?<!\w){re.escape(ad)}(?!\w)", okunus, m)
    m = m.replace("km²", "square kilometers").replace("per km2", "per square kilometer")
    m = m.replace("°C", " degrees Celsius").replace("km/s", "kilometers per second")
    m = re.sub(r"(?<![\w-])-(\d)", r"minus \1", m)  # "-20 degrees": eksi okunmadan düşmesin
    m = re.sub(r"\$(\d[\d,]*)", r"\1 dollars", m)
    m = re.sub(r"€(\d[\d,]*)", r"\1 euros", m)
    m = re.sub(r"(\d)\.(\d+)", r"\1 point \2", m)
    return m


def _istem(paket: OlguPaketi, kalip: str, gecmis: list[dict]) -> str:
    tutucular = "\n".join(
        f"- {{{k}}}: {v.anlam} (renders as: {kapilar.deger_yazisi(v.deger, v.birim)})"
        for k, v in paket.olgular.items()
        if k not in GIZLI
    )
    ret = ""
    if gecmis:
        ret = "\nYour previous attempt was rejected: " + "; ".join(gecmis[-1]["hatalar"]) + ". Fix that.\n"
    return (
        "You write the opening hook and the YouTube title for a 30-second vertical video on a channel with "
        f"{kanal.aktif().tanim}.\n"
        f"Video topic: {paket.konu}.\n"
        f"Angle for the hook: {KALIPLAR[kalip]}.\n"
        "Never write digits or number words (no 'one', 'ten', 'thousands'). Prefer names over numbers. To use a fact, "
        "insert its placeholder exactly as written:\n"
        f"{tutucular}\n"
        "Rules: the hook is one short sentence (max 12 words), spoken first; it may be a question. The title is max "
        "60 characters, Title Case, no hashtags, no emojis, no clickbait, no calls to subscribe or like, and it must "
        "describe the whole video topic, not a single detail. Make no claim beyond the facts.\n"
        f"{_ornekler()}{ret}\nReturn JSON with keys hook and title."
    )


def _tutucuya_cevir(metin: str, paket: OlguPaketi) -> str:
    """Model rakam içeren bir adı (asteroit "2026 TP2", gezegen "TOI-700 d") tutucu yerine aynen yazdıysa tutucuya
    çevir: değer olgunun kendisi, uydurma değil. Uzun ad önce (bir ad öbürünün parçası olabilir)."""
    adlar = [(k, o.deger) for k, o in paket.olgular.items() if isinstance(o.deger, str) and re.search(r"\d", o.deger)]
    for k, deger in sorted(adlar, key=lambda x: -len(x[1])):
        metin = re.sub(rf"(?<![\w{{]){re.escape(deger)}(?![\w}}])", "{" + k + "}", metin)
    return metin


def _denetle(ad: str, metin: str, paket: OlguPaketi, hakem_kullan: bool) -> list[str]:
    hatalar = [f"{ad}: {h}" for h in kapilar.tutucu_kapisi(metin, paket) + kapilar.politika_kapisi(metin)]
    if ad == "hook" and len(metin.split()) > 14:
        hatalar.append("hook: çok uzun")
    if ad == "title" and not hatalar and len(kapilar.doldur(metin, paket)) > 70:
        hatalar.append("title: çok uzun")
    if not metin:
        hatalar.append(f"{ad}: boş")
    if not hatalar and hakem_kullan and not kapilar.olgusuz_soru(metin):
        destek, neden = kapilar.hakem(kapilar.doldur(metin, paket), paket)
        if not destek:
            hatalar.append(f"{ad}: hakem reddetti ({neden})")
    return hatalar


def olustur(paket: OlguPaketi, kalip: str, tohum: str, hakem_kullan: bool = True) -> Anlatim:
    """Kanca ve başlık ayrı ayrı kapıdan geçer; DENEME sonunda geçemeyen parça yedekten gelir."""
    cumleler, varyant = olgu_cumleleri.cumleler(paket, tohum)
    gecmis: list[dict] = []
    kabul: dict[str, str] = {}
    for deneme in range(DENEME):
        try:
            yanit = json_uret(
                _istem(paket, kalip, gecmis), SEMA, tohum=zlib.crc32(f"{tohum}:{deneme}".encode()) % 10_000
            )
        except LLMHatasi as e:
            gecmis.append({"deneme": deneme, "hatalar": [str(e)]})
            continue
        kayit: dict = {"deneme": deneme, "hatalar": []}
        for ad in ("hook", "title"):
            metin = _tutucuya_cevir(yanit.get(ad, "").strip().strip('"'), paket)
            kayit[ad] = metin
            if ad in kabul:
                continue
            hatalar = _denetle(ad, metin, paket, hakem_kullan)
            kayit["hatalar"] += hatalar
            if not hatalar:
                kabul[ad] = metin
        gecmis.append(kayit)
        if len(kabul) == 2:
            break
    kaynak = {ad: ("llm" if ad in kabul else "yedek") for ad in ("hook", "title")}
    kanca = kapilar.doldur(kabul["hook"], paket) if "hook" in kabul else yedek.kanca(kalip, tohum)
    if kanca.endswith("?") and cumleler and cumleler[0].endswith("?"):
        cumleler = cumleler[1:]  # iki soru üst üste okunmasın
    return Anlatim(
        kanca=kanca,
        baslik=kapilar.baslik_duzeni(
            kapilar.doldur(kabul["title"], paket) if "title" in kabul else yedek.baslik(paket),
            # yalnız rakamlı özel adlar (gezegen/asteroit); Earth'ün gösterge adları eskisi gibi Title Case olur
            tuple(
                o.deger
                for o in paket.olgular.values()
                if isinstance(o.deger, str) and any(c.isdigit() for c in o.deger)
            ),
        ),
        cumleler=cumleler,
        kalip=kalip,
        varyant=varyant,
        denemeler=gecmis,
        kaynak=kaynak,
    )
