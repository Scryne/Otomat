"""İngilizce altyazı izi (senaryodan, kelime zamanlarıyla) ve başlık/açıklama çevirileri (YouTube `localizations`).

Neden (2026-11-27 ders, Onur Naci Öztürk dizi kanalı): İngilizce altyazı + altı dilde başlık/açıklama ile video başka
dillerde de bulundu, yorumlarda yeni dil istendi. Bizde:
- Altyazı YouTube'un otomatik tanımasından değil senaryodan çıkar: özel adlar (RZA, Ghostface Killah) ve rakamlar
  kelimesi kelimesine doğru, izleyicinin otomatik çevirisi de bu izden yapılır. Tek iz 400 kota birimi.
- Başlık/açıklama çevirisi ucuzdur (videos.update 50 birim); açıklamanın kaynak ve lisans kısmı İngilizce kalır.
  Rakam kümesi tutmayan ya da çevrilmemiş dil atlanır (yayin.ceviri kapısı).
"""

from __future__ import annotations

import json
import re

from otomat.trend.llm import Oturum
from otomat.yayin.ceviri import kes, rakamlar

DILLER = {"es": "Spanish", "pt": "Portuguese (Brazil)", "fr": "French", "de": "German", "it": "Italian",
          "hi": "Hindi", "ar": "Arabic", "id": "Indonesian"}  # fmt: skip
MODEL = "glm-5.3"
SATIR = 42  # altyazı satırı (karakter); iki satır, en çok 6 sn
IPUCU_SURE = 6.0


def _sozcukler(sahne_metni: str, kelimeler: list[dict]) -> list[tuple[str, float, float]]:
    """Senaryo sözcükleri + Whisper zamanları. Sayılar tutarsa senaryonun yazımı (noktalama, özel ad) kullanılır,
    tutmazsa Whisper'ın sözcükleri."""
    metin = sahne_metni.split()
    if len(metin) == len(kelimeler):
        return [(m, float(k["s"]), float(k["e"])) for m, k in zip(metin, kelimeler, strict=True)]
    return [(str(k["w"]).strip(), float(k["s"]), float(k["e"])) for k in kelimeler if str(k["w"]).strip()]


def ipuclari(sahneler: list[dict], zaman: dict) -> list[tuple[float, float, str]]:
    """(başlangıç, bitiş, metin): en çok iki satır × SATIR karakter, IPUCU_SURE saniye; cümle sonunda kesilir. Sığmayan
    parça son virgülden bölünür ("...Chad Smith of the Red / Hot Chili Peppers." gibi ad ortasından kesilmesin)."""
    out: list[tuple[float, float, str]] = []

    def bosalt(parca: list[tuple[str, float, float]], bas: float) -> None:
        out.append((bas + parca[0][1], bas + parca[-1][2], _satirla(" ".join(x[0] for x in parca))))

    for sh, z in zip(sahneler, zaman["sahneler"], strict=False):
        bas = float(z["bas"])
        parca: list[tuple[str, float, float]] = []
        for w, s, e in _sozcukler(sh.get("anlatim", ""), z.get("kelimeler") or []):
            aday = " ".join(x[0] for x in [*parca, (w, s, e)])
            if parca and (len(aday) > 2 * SATIR or e - parca[0][1] > IPUCU_SURE):
                virgul = [j for j, x in enumerate(parca[:-1]) if x[0].endswith((",", ";", ":")) and j >= 2]
                kes_ = virgul[-1] + 1 if virgul else len(parca)
                bosalt(parca[:kes_], bas)
                parca = parca[kes_:]
            parca.append((w, s, e))
            if re.search(r"[.?!]['\"]?$", w) and len(" ".join(x[0] for x in parca)) >= 15:
                bosalt(parca, bas)
                parca = []
        if parca:
            bosalt(parca, bas)
    return out


def _satirla(metin: str) -> str:
    """SATIR'dan uzunsa iki satıra böler: iki satırın da SATIR'a sığdığı virgül sonrası boşluk, yoksa ortaya en yakın
    boşluk."""
    if len(metin) <= SATIR:
        return metin
    bosluk = [m.start() for m in re.finditer(" ", metin)]
    sigan = [i for i in bosluk if i <= SATIR and len(metin) - i - 1 <= SATIR]
    virgul = [i for i in sigan if metin[i - 1] in ",;:"]
    adaylar = virgul or sigan or bosluk
    i = min(adaylar, key=lambda x: abs(x - len(metin) / 2))
    return metin[:i] + "\n" + metin[i + 1 :]


def _zaman(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3_600_000:02d}:{ms // 60_000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def srt(ipuclari_: list[tuple[float, float, str]]) -> str:
    satirlar = []
    for n, (a, b, m) in enumerate(ipuclari_, 1):
        b = max(b, a + 0.8)
        if n < len(ipuclari_):
            b = min(b, ipuclari_[n][0] - 0.02)
        satirlar.append(f"{n}\n{_zaman(a)} --> {_zaman(b)}\n{m}\n")
    return "\n".join(satirlar)


SISTEM = """You translate YouTube metadata for an English-language explainer channel. For each language asked, translate
the TITLE and the DESCRIPTION. Keep every number, timestamp (like 1:05), name and title of a work exactly as written
(Western digits, do not convert number formats). Translate everything else naturally for that language's YouTube
audience; keep the meaning exact and add nothing. Titles stay under 100 characters.
Return ONLY JSON: {"<language code>": {"title": "...", "description": "..."}, ...}"""


def yerellestir(oturum: Oturum, baslik: str, aciklama: str, diller: dict[str, str] = DILLER) -> dict[str, dict]:
    """Dil kodu → {title, description}. Açıklamanın "Sources:" ve sonrası İngilizce kalır."""
    bas, ayrac, kuyruk = aciklama.partition("\n\nSources:")
    istem = (f"LANGUAGES: {json.dumps(diller)}\n\nTITLE: {baslik}\n\nDESCRIPTION:\n{bas}")  # fmt: skip
    y = oturum.json_sor(SISTEM, istem, model=MODEL, en_cok=12000, sicaklik=0.2, dusun=False)
    out: dict[str, dict] = {}
    for dil in diller:
        v = y.get(dil) if isinstance(y, dict) else None
        if not isinstance(v, dict):
            continue
        t, d = str(v.get("title") or "").strip(), str(v.get("description") or "").strip()
        if not t or not d or rakamlar(t) != rakamlar(baslik) or rakamlar(d) != rakamlar(bas):
            continue
        if _norm(t) == _norm(baslik):  # çevrilmemiş
            continue
        out[dil] = {"title": t[:100], "description": kes(d + ayrac + kuyruk, 5000)}
    return out


def _norm(metin: str) -> str:
    return re.sub(r"\W+", " ", metin).strip().casefold()
