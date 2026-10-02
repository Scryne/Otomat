"""Başlık, açıklama ve altyazı çevirisi (yerel LLM). Kapı: çeviride rakamlar kaynakla aynı olmalı.

Rakam kümesi tutmayan dil yayınlanmaz (o dilde yerelleştirme atlanır); İngilizce her zaman vardır.
"""

import re

from otomat.anlati.llm import LLMHatasi, json_uret

DILLER = {"es": "Spanish", "pt": "Portuguese (Brazil)", "de": "German", "fr": "French"}


SAYI = re.compile(r"\d+(?:[.,   ](?=\d{3}(?!\d))\d{3})*(?:[.,]\d+)?")


def rakamlar(metin: str) -> list[str]:
    """Ayraçtan bağımsız rakam dizileri: '1,047' / '1.047' / '1 047' -> '1047'; '4.5' / '4,5' -> '45'.

    Binlik ayracı yalnız ardından tam 3 hane gelirse sayılır: 'August 14, 2026' iki sayıdır (14 ve 2026).
    """
    return sorted(re.sub(r"\D", "", m) for m in SAYI.findall(metin))


def cevir(dil: str, baslik: str, aciklama: str, altyazilar: list[str], tohum: int = 0) -> dict | None:
    sema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "captions": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["title", "description", "captions"],
    }
    numarali = "\n".join(f"{i + 1}. {m}" for i, m in enumerate(altyazilar))
    istem = (
        f"Translate this YouTube Shorts metadata from English to {DILLER[dil]}. Keep every number, place name and "
        "hashtag exactly as written (do not convert number formats). Keep the meaning exact; add nothing.\n\n"
        f"TITLE: {baslik}\n\nDESCRIPTION:\n{aciklama}\n\n"
        f"SENTENCES (translate each separately, return exactly {len(altyazilar)} items):\n{numarali}\n\n"
        "Return JSON with title, description and captions (array of strings, no numbering)."
    )
    try:
        y = json_uret(istem, sema, sicaklik=0.2, tohum=tohum, zaman_asimi=600)
    except LLMHatasi:
        return None
    caps = [re.sub(r"^\d+\.\s*", "", c).strip() for c in y.get("captions", [])]
    if len(caps) != len(altyazilar):
        return None
    if rakamlar(y.get("title", "")) != rakamlar(baslik) or rakamlar(" ".join(caps)) != rakamlar(" ".join(altyazilar)):
        return None
    if rakamlar(y.get("description", "")) != rakamlar(aciklama):
        return None
    return {"title": y["title"][:100], "description": y["description"][:5000], "captions": caps}
