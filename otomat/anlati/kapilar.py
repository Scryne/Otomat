"""Doğrulama kapıları (K-3): kapıyı geçemeyen metin yayınlanmaz.

1. Tutucu kapısı: LLM metninde bilinmeyen {yer_tutucu}, çıplak rakam ya da yazıyla sayı yok.
2. Politika kapısı: yasak ifade listesi (abone ol çağrısı, tıbbi/siyasi yargı, felaket abartısı...).
3. Anlamsal hakem: doldurulmuş cümle olgularla destekleniyor mu (yerel LLM, evet/hayır + gerekçe).
"""

import json
import re

from otomat.anlati.llm import json_uret
from otomat.veri import OlguPaketi

SAYI_KELIME = re.compile(
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fifteen|twenty|thirty|forty|fifty|"
    r"sixty|seventy|eighty|ninety|hundred|thousand|million|billion|dozen|half|double|triple|twice|thrice)s?\b",
    re.I,
)
YASAK = re.compile(
    r"\b(subscribe|like and|follow for|link in bio|comment below|smash|shocking|terrifying|apocalyp\w*|doomed|"
    r"deadly|death toll|killed|victims?|catastroph\w*|cure|vaccine|election|corrupt\w*|regime|dictator\w*|"
    r"best country|worst country|you won't believe|nobody|everyone|always|never|proves?|because of)\b",
    re.I,
)
TUTUCU = re.compile(r"\{(\w+)\}")


def izinli_sayilar(paket: OlguPaketi) -> set[str]:
    """Paketin yapısından gelen, olgu olmayan sayılar ('Top 10' listesindeki 10 gibi)."""
    return {"10"} if paket.tur.endswith("_10") else set()


def olgusuz_soru(metin: str) -> bool:
    """Tutucu ve rakam içermeyen soru: doğrulanacak iddia taşımaz, hakeme gitmez."""
    return metin.rstrip().endswith("?") and not TUTUCU.search(metin) and not re.search(r"\d", metin)


def tutucu_kapisi(metin: str, paket: OlguPaketi) -> list[str]:
    hatalar = [f"bilinmeyen tutucu {{{k}}}" for k in TUTUCU.findall(metin) if k not in paket.olgular]
    ciplak = TUTUCU.sub("", metin)
    if [x for x in re.findall(r"\d+(?:\.\d+)?", ciplak) if x not in izinli_sayilar(paket)]:
        hatalar.append("çıplak rakam")
    if m := SAYI_KELIME.findall(ciplak):
        hatalar.append("yazıyla sayı: " + ", ".join(sorted(set(x.lower() for x in m))))
    return hatalar


def politika_kapisi(metin: str) -> list[str]:
    return [f"yasak ifade: {m.lower()}" for m in sorted(set(YASAK.findall(metin)))]


def deger_yazisi(deger, birim: str, ondalik: int | None = None) -> str:
    """Değeri birimiyle yaz: 34.5 + '% of GDP' -> '34.5% of GDP'; 129000 + 'US$' -> '$129,000'."""
    from otomat.gorsel.kimlik import sayi

    if not isinstance(deger, int | float) or isinstance(deger, bool):
        return str(deger)
    d = sayi(deger, ondalik)
    if not birim or birim in ("days",):
        return d
    if birim == "US$":
        return f"${d}"
    if birim == "€":
        return f"€{d}"
    if birim.startswith("%"):
        return f"{d}{birim}"
    return f"{d} {birim}"


def doldur(metin: str, paket: OlguPaketi) -> str:
    def deger(m: re.Match) -> str:
        o = paket.olgular[m.group(1)]
        return deger_yazisi(o.deger, o.birim)

    return TUTUCU.sub(deger, metin)


KUCUK_KELIME = {"a", "an", "the", "of", "in", "on", "at", "by", "for", "to", "with", "and", "or", "as", "per", "vs"}


def baslik_duzeni(metin: str) -> str:
    """Title Case: küçük bağlaçlar küçük (ilk kelime hariç); rakam ya da büyük harf içeren kelimeye dokunma."""
    kelimeler = metin.split()
    sonuc = []
    for i, k in enumerate(kelimeler):
        if any(c.isdigit() for c in k) or any(c.isupper() for c in k[1:]):
            sonuc.append(k)
        elif i > 0 and k.lower() in KUCUK_KELIME:
            sonuc.append(k.lower())
        else:
            sonuc.append(k[:1].upper() + k[1:])
    return " ".join(sonuc)


HAKEM_SEMA = {
    "type": "object",
    "properties": {"supported": {"type": "boolean"}, "reason": {"type": "string"}},
    "required": ["supported", "reason"],
}

HAKEM_ISTEMLERI = {
    "v1": (
        "Is every claim in the sentence directly supported by the facts? Rules: a claim not stated in the facts is "
        "unsupported; wrong quantities, wrong comparisons, linking a number to the wrong place, or adding causes, "
        "consequences, damage or emotions that the facts do not state are unsupported. Rhetorical questions and "
        "invitations to watch are fine if they make no factual claim. Answer in JSON."
    ),
    "v2": (
        "Decide if the sentence is SUPPORTED by the facts.\n"
        "SUPPORTED: every number, place, date and ranking in the sentence matches the facts; paraphrases and "
        "synonyms are fine (e.g. 'young graduates' for '25-34 year olds with a degree', 'a single year' for "
        "'365 days'); rounding is fine; questions and invitations to watch are fine; vague wording that is not "
        "false is fine.\n"
        "NOT SUPPORTED: a number attached to the wrong place or category; a wrong number; a wrong ranking or "
        "comparison; a superlative the facts do not establish (e.g. 'most in the world' when the facts only cover "
        "one region); causes, damage, casualties, tsunamis or other consequences that the facts do not state.\n"
        "First check each number and name against the facts, then answer in JSON."
    ),
}
HAKEM_SURUM = "v2"


def hakem(cumle: str, paket: OlguPaketi, surum: str = HAKEM_SURUM) -> tuple[bool, str]:
    """Cümledeki her iddia olgularla destekleniyor mu? Belirsizse 'hayır' (yayın yok tarafına hata yap)."""
    olgular = {k: {"value": v.deger, "meaning": v.anlam, "unit": v.birim} for k, v in paket.olgular.items()}
    istem = (
        "You are a strict fact checker for a data video. FACTS (the only truth):\n"
        f"{json.dumps(olgular, ensure_ascii=False)}\n\n"
        f'SENTENCE: "{cumle}"\n\n' + HAKEM_ISTEMLERI[surum]
    )
    yanit = json_uret(istem, HAKEM_SEMA, sicaklik=0.0, tohum=0)
    return bool(yanit.get("supported")), str(yanit.get("reason", ""))[:300]
