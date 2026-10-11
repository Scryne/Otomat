"""Sahne görselinde yazı denetimi (OCR). flux "no text" istemini tutmuyor: Earth karelerinde tabela, pankart, gazete
anlamsız harflerle çıkıyordu ("BIATER", "Nun of the Abve", "ABOLISHA FOR AUSTRAAUSNANONS"; 10-12 incelemesi).

Ölçüm (2026-10-12, 87 sahne, 13 hikâye; gözle etiketlendi): RapidOCR'ın Latin harfli, en az 3 harfli ve güveni ≥ 0,7
okuması "yazı var" sayılır. Masal karelerinde (37) yanlış alarm 0: model Çince karakter, tek harf ve rakam uyduruyor,
bunlar sayılmaz. Gözle yazı görülen Earth karelerinin çoğunu yakalıyor (Sister Boom Boom 7/8, Wog Rolo 8/8), yazısız
Earth karelerinde (Lincoln, Ténéré) yanlış alarm yok. Kare başına ~1 sn (CPU).

Paket isteğe bağlı (`uv sync --extra gorsel`): yoksa denetim atlanır, video yine çıkar.
"""

import re
from functools import cache
from pathlib import Path

GUVEN = 0.7
HARF = 3
_LATIN = re.compile(r"[A-Za-z]")


def sayilir(metin: str, guven: float) -> bool:
    return guven >= GUVEN and len(_LATIN.findall(metin)) >= HARF


@cache
def _ocr():
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        return None
    return RapidOCR()


def oku(yol: Path) -> list[str] | None:
    """Karede sayılan yazılar (boşsa yazı yok); OCR kurulu değilse None."""
    if (ocr := _ocr()) is None:
        return None
    bulgu, _ = ocr(str(yol))
    return [m for _, m, g in bulgu or [] if sayilir(m, float(g))]
