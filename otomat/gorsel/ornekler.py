"""Faz 3 sınaması: gerçek paketlerden her şablon için örnek video + kontrol kareleri."""

import argparse
import json
import subprocess
from pathlib import Path

import imageio_ffmpeg

from otomat.ayarlar import KOK
from otomat.gorsel import sablonlar
from otomat.veri import Kaynak, Olgu, OlguPaketi

SECIM = {
    "nokta_harita": ["usgs:dunya_30g", "usgs:bolge_yillik:Indonesia", "usgs:bolge_yillik:Tonga"],
    "sirali_cubuk": ["usgs:en_guclu_10", "dunya_bankasi:en_yuksek_10:MS.MIL", "eurostat:en_dusuk_10:sdg_04_20"],
    "koroplet": [
        "dunya_bankasi:en_yuksek_10:SP.DYN.LE00",
        "dunya_bankasi:en_dusuk_10:IT.NET",
        "eurostat:en_yuksek_10:sdg_07_40",
    ],
}


def paket_yukle(d: dict) -> OlguPaketi:
    return OlguPaketi(
        kol=d["kol"],
        tur=d["tur"],
        anahtar=d["anahtar"],
        konu=d["konu"],
        olgular={k: Olgu(**v) for k, v in d["olgular"].items()},
        gorsel=d["gorsel"],
        kaynak=Kaynak(**d["kaynak"]),
        etiketler=d.get("etiketler", []),
    )


def kontrol_kareleri(video: Path, cikti: Path, saniyeler=(0.5, 3, 14, 29.5)) -> None:
    secim = "+".join(f"eq(n\\,{int(s * 30)})" for s in saniyeler)
    subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-v",
            "error",
            "-y",
            "-i",
            str(video),
            "-vf",
            f"select='{secim}',scale=270:-1,tile={len(saniyeler)}x1",
            "-frames:v",
            "1",
            str(cikti),
        ],
        check=True,
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--paketler", type=Path, default=KOK / "calisma" / "paketler.json")
    p.add_argument("--dizin", type=Path, default=KOK / "calisma" / "ornekler")
    p.add_argument("--saniye", type=float, default=30)
    a = p.parse_args()
    paketler = [paket_yukle(d) for d in json.loads(a.paketler.read_text(encoding="utf-8"))]
    for sablon, onekler in SECIM.items():
        for onek in onekler:
            pk = next((x for x in paketler if x.anahtar.startswith(onek)), None)
            if pk is None:
                print("YOK", onek)
                continue
            ad = f"{sablon}_{onek.replace(':', '_')}"
            video = a.dizin / f"{ad}.mp4"
            baslik = pk.konu[:1].upper() + pk.konu[1:]
            sablonlar.ciz(
                pk, video, baslik, kanca=f"Test hook for {onek.split(':')[0]}", sablon=sablon, saniye=a.saniye
            )
            kontrol_kareleri(video, a.dizin / f"{ad}.jpg")
            print("tamam", video.name)


if __name__ == "__main__":
    main()
