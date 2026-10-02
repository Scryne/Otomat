"""Altyazı parçalarından SRT metni."""

from collections.abc import Sequence


def _zaman(sn: float) -> str:
    ms = int(round(sn * 1000))
    s, ms = divmod(ms, 1000)
    d, s = divmod(s, 60)
    sa, d = divmod(d, 60)
    return f"{sa:02d}:{d:02d}:{s:02d},{ms:03d}"


def srt(parcalar: Sequence, metinler: Sequence[str] | None = None) -> str:
    """parcalar: bas/son/metin taşıyan nesneler veya sözlükler; metinler verilirse (çeviri) onlar yazılır."""
    satirlar = []
    for i, p in enumerate(parcalar):
        bas, son, metin = (p["bas"], p["son"], p["metin"]) if isinstance(p, dict) else (p.bas, p.son, p.metin)
        satirlar.append(f"{i + 1}\n{_zaman(bas)} --> {_zaman(son)}\n{metinler[i] if metinler else metin}\n")
    return "\n".join(satirlar)
