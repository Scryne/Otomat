"""Çeviri kapısı neden reddediyor? Tek dil için ham çıktı ve rakam farkları."""

import json
import sys
from pathlib import Path

from otomat.anlati.llm import json_uret
from otomat.ses import Parca, altyazi_parcalari
from otomat.yayin import ceviri

dizin = Path(sys.argv[1])
dil = sys.argv[2] if len(sys.argv) > 2 else "es"
meta = json.loads((dizin / "meta.json").read_text(encoding="utf-8"))
metinler = [p.metin for p in altyazi_parcalari([Parca(**p) for p in meta["altyazi"]])]
sema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "captions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "description", "captions"],
}
numarali = "\n".join(f"{i + 1}. {m}" for i, m in enumerate(metinler))
istem = (
    f"Translate this YouTube Shorts metadata from English to {ceviri.DILLER[dil]}. Keep every number, place name and "
    "hashtag exactly as written (do not convert number formats). Keep the meaning exact; add nothing.\n\n"
    f"TITLE: {meta['baslik']}\n\nDESCRIPTION:\n{meta['aciklama']}\n\n"
    f"CAPTIONS (translate each line separately, return exactly {len(metinler)} lines):\n{numarali}\n\n"
    "Return JSON with title, description and captions (array of strings, no numbering)."
)
y = json_uret(istem, sema, sicaklik=0.2, tohum=0, zaman_asimi=600)
print("satır:", len(y["captions"]), "/", len(metinler))
for ad, kaynak, hedef in (
    ("title", meta["baslik"], y["title"]),
    ("desc", meta["aciklama"], y["description"]),
    ("caps", " ".join(metinler), " ".join(y["captions"])),
):
    a, b = ceviri.rakamlar(kaynak), ceviri.rakamlar(hedef)
    print(ad, "OK" if a == b else f"FARK kaynak-hedef={sorted(set(a) - set(b))} hedef-kaynak={sorted(set(b) - set(a))}")
print(json.dumps(y, ensure_ascii=False)[:1500])
