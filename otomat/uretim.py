"""Uçtan uca üretim: olgu paketi → anlatım (kapılar) → ses → görsel + altyazı → mp4 + metadata.

Yükleme yok (Faz 5). Her video `calisma/uretim/<tarih>/<sıra>_<anahtar>/` altına yazılır:
video.mp4, ses.wav, meta.json (başlık, açıklama, etiketler, kapı geçmişi, seçimler).
"""

import argparse
import datetime as dt
import json
import re
import subprocess
import time
from dataclasses import asdict
from pathlib import Path

import imageio_ffmpeg

from otomat import ses
from otomat.anlati import anlatim
from otomat.ayarlar import KOK
from otomat.gorsel import sablonlar
from otomat.veri import OlguPaketi

KUYRUK = 1.2  # anlatım bittikten sonra son kare (sn)


def kaynak_sayfasi(paket: OlguPaketi) -> str:
    if paket.kol == "usgs":
        return "https://earthquake.usgs.gov/earthquakes/search/"
    if paket.kol == "jpl":
        from otomat.veri.jpl import SAYFA

        return SAYFA
    if paket.kol == "otegezegen":
        from otomat.veri.otegezegen import SAYFA

        return SAYFA
    kod = paket.anahtar.split(":")[2]
    if paket.kol == "dunya_bankasi":
        return f"https://data.worldbank.org/indicator/{kod}"
    return f"https://ec.europa.eu/eurostat/databrowser/view/{kod}/default/table"


def _atif(paket: OlguPaketi) -> str:
    """Kaynağın istediği atıf metni (Exoplanet Archive zorunlu tutuyor); yoksa boş."""
    if paket.kol == "otegezegen":
        from otomat.veri.otegezegen import ATIF

        return ATIF + "\n"
    if paket.kol == "jpl":
        return "Sizes are estimated from brightness; distances are nominal closest approach.\n"
    return ""


def aciklama(paket: OlguPaketi, a: anlatim.Anlatim) -> str:
    # kelime başı büyük, gerisi olduğu gibi: "DR Congo" → #DRCongo (title() "#DrCongo" yapıyordu)
    etiket = " ".join(
        "#" + re.sub(r"\W", "", "".join(w[:1].upper() + w[1:] for w in e.split())) for e in paket.etiketler if e
    )
    return (
        f"{a.kanca}\n\n{' '.join(a.cumleler)}\n\n"
        f"Data: {paket.kaynak.ad} ({paket.kaynak.lisans}), retrieved {paket.kaynak.cekildi[:10]}.\n"
        f"Source: {kaynak_sayfasi(paket)}\n"
        f"{_atif(paket)}"
        "Visuals generated from the data; narration is synthetic.\n\n"
        f"#Shorts {etiket}"
    )


def birlestir(video: Path, wav: Path, cikti: Path) -> Path:
    subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-v",
            "error",
            "-y",
            "-i",
            str(video),
            "-i",
            str(wav),
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            # ses KUYRUK kadar kısa: o kadar sessizlik eklenir (yalnız -shortest kapanışı kesiyordu); sınırsız
            # apad -c:v copy ile ffmpeg'i hiç bitirmiyor
            "-af",
            f"apad=pad_dur={KUYRUK}",
            "-shortest",
            str(cikti),
        ],
        check=True,
    )
    return cikti


def uret(paket: OlguPaketi, kalip: str, sablon: str, dizin: Path, tohum: str) -> dict:
    t0 = time.time()
    a = anlatim.olustur(paket, kalip, tohum)
    t_anlati = time.time()
    sure, parcalar = ses.seslendir(a.ses_cumleleri, [a.kanca, *a.cumleler], dizin / "ses.wav")
    t_ses = time.time()
    sessiz = sablonlar.ciz(
        paket,
        dizin / "sessiz.mp4",
        a.baslik,
        kanca=a.kanca,
        sablon=sablon,
        saniye=sure + KUYRUK,
        kanca_sure=parcalar[0].son + 0.2,
        altyazi=ses.altyazi_parcalari(parcalar[1:]),
    )
    video = birlestir(sessiz, dizin / "ses.wav", dizin / "video.mp4")
    sessiz.unlink()
    meta = {
        "baslik": a.baslik,
        "aciklama": aciklama(paket, a),
        "etiketler": paket.etiketler,
        "paket": {"anahtar": paket.anahtar, "hash": paket.hash, "kol": paket.kol, "tur": paket.tur},
        "secim": {"kalip": kalip, "sablon": sablon, "varyant": a.varyant, "kaynak": a.kaynak},
        "kanca": a.kanca,
        "cumleler": a.cumleler,
        "altyazi": [asdict(p) for p in parcalar],
        "sure_sn": round(sure + KUYRUK, 2),
        "denemeler": a.denemeler,
        "zaman_sn": {
            "anlati": round(t_anlati - t0, 1),
            "ses": round(t_ses - t_anlati, 1),
            "gorsel": round(time.time() - t_ses, 1),
        },
        "video": str(video.relative_to(KOK)) if video.is_relative_to(KOK) else str(video),
    }
    (dizin / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta


def main() -> None:
    from otomat.gorsel.ornekler import paket_yukle

    p = argparse.ArgumentParser()
    p.add_argument("--paketler", type=Path, default=KOK / "calisma" / "paketler.json")
    p.add_argument("--adet", type=int, default=10)
    p.add_argument("--dizin", type=Path, default=KOK / "calisma" / "uretim")
    a = p.parse_args()
    paketler = [paket_yukle(d) for d in json.loads(a.paketler.read_text(encoding="utf-8"))]
    bugun = dt.date.today().isoformat()
    kaliplar = list(anlatim.KALIPLAR)
    # Faz 4 sınaması: kol ve tür çeşitliliği için sıralı dağıtım (Faz 6'da haydut seçer)
    turler: dict[str, list[OlguPaketi]] = {}
    for pk in paketler:
        turler.setdefault(f"{pk.kol}:{pk.tur}", []).append(pk)
    secilen = []
    i = 0
    while len(secilen) < a.adet and any(turler.values()):
        for anahtar in sorted(turler):
            if turler[anahtar] and len(secilen) < a.adet:
                secilen.append(turler[anahtar].pop(i % len(turler[anahtar])))
        i += 1
    ozet = []
    for n, pk in enumerate(secilen):
        secenek = sablonlar.secenekler(pk)
        sablon = secenek[n % len(secenek)]
        kalip = kaliplar[n % len(kaliplar)]
        dizin = a.dizin / bugun / f"{n:02d}_{re.sub(r'[^A-Za-z0-9]+', '_', pk.anahtar)[:60]}"
        try:
            meta = uret(pk, kalip, sablon, dizin, bugun)
            ozet.append((pk.anahtar, sablon, kalip, meta["secim"]["kaynak"], meta["sure_sn"], meta["zaman_sn"]))
            print("tamam", dizin.name, meta["baslik"], flush=True)
        except Exception as e:  # noqa: BLE001 — bir video düşerse diğerleri sürsün
            ozet.append((pk.anahtar, sablon, kalip, "HATA", str(e)[:200], None))
            print("HATA", dizin.name, e, flush=True)
    (a.dizin / bugun / "ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
