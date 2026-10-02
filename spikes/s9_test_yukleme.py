"""Faz 5 doğrulaması: bir videoyu planlamasız, gizli yükle; altyazı ve yerelleştirmeyi ekle; durumunu oku."""

import json
import sys
from pathlib import Path

from otomat.yayin import youtube

dizin = Path(sys.argv[1])
meta = json.loads((dizin / "meta.json").read_text(encoding="utf-8"))
yerel = json.loads((dizin / "yerel.json").read_text(encoding="utf-8"))["yerel"]
yt = youtube.servis()
vid = youtube.yukle(dizin / "video.mp4", meta["baslik"], meta["aciklama"], meta["etiketler"], None, yerel, yt=yt)
print("yüklendi:", vid)
for srt in sorted(dizin.glob("*.srt")):
    youtube.altyazi_ekle(vid, srt.stem, srt.read_text(encoding="utf-8"), yt=yt)
    print("altyazı:", srt.stem)
v = yt.videos().list(part="status,snippet,localizations", id=vid).execute()["items"][0]
print("durum:", json.dumps(v["status"], ensure_ascii=False))
print("başlık:", v["snippet"]["title"], "| diller:", sorted(v.get("localizations", {})))
caps = yt.captions().list(part="snippet", videoId=vid).execute()["items"]
print("altyazı izleri:", sorted(c["snippet"]["language"] for c in caps))
