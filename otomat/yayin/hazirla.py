"""Bir üretim klasörünü yayına hazırla: İngilizce + çeviri altyazıları (.srt) ve yerelleştirme (yerel.json)."""

import json
from pathlib import Path

from otomat import kanal
from otomat.ses import Parca, altyazi_parcalari
from otomat.yayin import ceviri
from otomat.yayin.srt import srt


def hazirla(dizin: Path, deneme: int = 3) -> dict:
    """Cümleler bütün olarak çevrilir (parça parça çeviri satır birleştiriyordu), sonra aynı zamanlarla parçalanır."""
    meta = json.loads((dizin / "meta.json").read_text(encoding="utf-8"))
    cumle_parcalari = [Parca(**p) for p in meta["altyazi"]]
    (dizin / "en.srt").write_text(srt(altyazi_parcalari(cumle_parcalari)), encoding="utf-8")
    cumleler = [p.metin for p in cumle_parcalari]
    yerel, atlanan = {}, []
    for dil in kanal.aktif().diller:
        sonuc = None
        for tohum in range(deneme):
            sonuc = ceviri.cevir(dil, meta["baslik"], meta["aciklama"], cumleler, tohum=tohum)
            if sonuc:
                break
        if sonuc is None:
            atlanan.append(dil)
            continue
        yerel[dil] = {"title": sonuc["title"], "description": sonuc["description"]}
        cevrilmis = [Parca(p.bas, p.son, c) for p, c in zip(cumle_parcalari, sonuc["captions"], strict=True)]
        (dizin / f"{dil}.srt").write_text(srt(altyazi_parcalari(cevrilmis)), encoding="utf-8")
    (dizin / "yerel.json").write_text(
        json.dumps({"yerel": yerel, "atlanan": atlanan}, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return {"yerel": yerel, "atlanan": atlanan}


if __name__ == "__main__":
    import sys

    for d in sys.argv[1:]:
        s = hazirla(Path(d))
        print(Path(d).name, "diller:", list(s["yerel"]), "atlanan:", s["atlanan"])
