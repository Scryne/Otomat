"""Bir üretim klasörünü yayına hazırla: İngilizce + çeviri altyazıları (.srt) ve yerelleştirme (yerel.json)."""

import hashlib
import json
from pathlib import Path

from otomat import kanal
from otomat.ses import Parca, altyazi_parcalari
from otomat.yayin import ceviri
from otomat.yayin.srt import srt


def _kaynak_ozeti(meta: dict) -> str:
    """Çevrilen metnin özeti: yerel.json yalnız aynı başlık/açıklama/cümleler için yeniden kullanılır."""
    metin = json.dumps([meta["baslik"], meta["aciklama"], [p["metin"] for p in meta["altyazi"]]], ensure_ascii=False)
    return hashlib.sha256(metin.encode()).hexdigest()[:16]


def _onceki(dizin: Path, ozet: str) -> dict:
    """Aynı metnin önceki çevirileri (hazır üretim, yeniden deneme): dil → yerelleştirme; srt'si duranlar."""
    try:
        d = json.loads((dizin / "yerel.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if d.get("kaynak") != ozet:
        return {}
    return {dil: v for dil, v in d.get("yerel", {}).items() if (dizin / f"{dil}.srt").exists()}


def hazirla(dizin: Path, deneme: int = 3) -> dict:
    """Cümleler bütün olarak çevrilir (parça parça çeviri satır birleştiriyordu), sonra aynı zamanlarla parçalanır.
    Aynı metnin önceki çevirisi duruyorsa o dil yeniden çevrilmez (hikâye kanallarında çeviri Cloudflare kotası
    harcar; hazır üretim yayına ikinci kez geldiğinde kota boşa gidiyordu). Önceki koşuda atlanan dil yeniden
    denenir."""
    meta = json.loads((dizin / "meta.json").read_text(encoding="utf-8"))
    ozet = _kaynak_ozeti(meta)
    cumle_parcalari = [Parca(**p) for p in meta["altyazi"]]
    (dizin / "en.srt").write_text(srt(altyazi_parcalari(cumle_parcalari)), encoding="utf-8")
    cumleler = [p.metin for p in cumle_parcalari]
    onceki = _onceki(dizin, ozet)
    yerel, atlanan, kota = {}, [], False
    for dil in kanal.aktif().diller:
        if dil in onceki:
            yerel[dil] = onceki[dil]
            continue
        sonuc = None
        for tohum in range(0 if kota else deneme):
            try:
                sonuc = ceviri.cevir(dil, meta["baslik"], meta["aciklama"], cumleler, tohum=tohum)
            except ceviri.CeviriKotasi:
                kota = True  # kalan diller denenmez; yerel.json'da "kota" işaretlenir, sonraki deneme yeniden çevirir
                break
            if sonuc:
                break
        if sonuc is None:
            atlanan.append(dil)
            (dizin / f"{dil}.srt").unlink(missing_ok=True)
            continue
        yerel[dil] = {"title": sonuc["title"], "description": sonuc["description"]}
        cevrilmis = [Parca(p.bas, p.son, c) for p, c in zip(cumle_parcalari, sonuc["captions"], strict=True)]
        (dizin / f"{dil}.srt").write_text(srt(altyazi_parcalari(cevrilmis)), encoding="utf-8")
    (dizin / "yerel.json").write_text(
        json.dumps({"yerel": yerel, "atlanan": atlanan, "kota": kota, "kaynak": ozet}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return {"yerel": yerel, "atlanan": atlanan, "kota": kota}


if __name__ == "__main__":
    import sys

    for d in sys.argv[1:]:
        s = hazirla(Path(d))
        print(Path(d).name, "diller:", list(s["yerel"]), "atlanan:", s["atlanan"])
