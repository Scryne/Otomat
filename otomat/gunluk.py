"""Günlük koşu: veri topla → taze paket seç → üret → çevir → yayınla (API) ya da teslim paketine koy (Plan B).

Ortam:
- OTOMAT_YAYIN = "api" | "teslim" (varsayılan teslim; audit gelene kadar API yüklemesi private'a kilitlenir)
- YT_ISTEMCI_JSON, YT_TOKEN_JSON (yalnız api modunda)
Seçim şimdilik tohumlu rastgele; Faz 6'da haydut (analitik geri beslemesi) devralır.
"""

import datetime as dt
import json
import os
import random
import re
import shutil
from pathlib import Path

from otomat import durum
from otomat.anlati import anlatim
from otomat.ayarlar import KOK
from otomat.gorsel import sablonlar
from otomat.uretim import uret
from otomat.veri import OlguPaketi
from otomat.veri.toplayici import topla
from otomat.yayin.hazirla import hazirla

YAYIN_SAATI_UTC = 14  # ABD sabahı / Avrupa öğleden sonrası
RAPOR = KOK / "raporlar" / "gunluk.jsonl"


def sec(paketler: list[OlguPaketi], db, bugun: dt.date) -> tuple[OlguPaketi, str, str]:
    taze = [p for p in paketler if durum.taze_mi(db, p, bugun)]
    if not taze:
        raise RuntimeError("taze paket kalmadı (tekrar engeli 60 gün)")
    r = random.Random(bugun.isoformat())
    kollar = sorted({p.kol for p in taze})
    kol = kollar[bugun.toordinal() % len(kollar)]  # kolları sırayla dolaş
    paket = r.choice([p for p in taze if p.kol == kol])
    return paket, r.choice(list(anlatim.KALIPLAR)), r.choice(sablonlar.secenekler(paket))


def yayinla_api(dizin: Path, yayin_ani: dt.datetime) -> str:
    from otomat.yayin import youtube

    meta = json.loads((dizin / "meta.json").read_text(encoding="utf-8"))
    yerel = json.loads((dizin / "yerel.json").read_text(encoding="utf-8"))["yerel"]
    yt = youtube.servis()
    video_id = youtube.yukle(
        dizin / "video.mp4", meta["baslik"], meta["aciklama"], meta["etiketler"], yayin_ani, yerel, yt=yt
    )
    for srt in sorted(dizin.glob("*.srt")):
        youtube.altyazi_ekle(video_id, srt.stem, srt.read_text(encoding="utf-8"), yt=yt)
    return video_id


def teslime_koy(dizin: Path, bugun: dt.date, yayin_ani: dt.datetime) -> Path:
    """Dosyalar tarih önekiyle düz bir klasöre: Actions bunları haftanın GitHub Release'ine ekler."""
    hedef = KOK / "teslim"
    hedef.mkdir(parents=True, exist_ok=True)
    on = bugun.isoformat()
    for ad in ["video.mp4", *[p.name for p in dizin.glob("*.srt")]]:
        shutil.copy(dizin / ad, hedef / f"{on}_{ad}")
    meta = json.loads((dizin / "meta.json").read_text(encoding="utf-8"))
    (hedef / f"{on}_YUKLE.md").write_text(
        f"# {bugun.isoformat()}: yayın {yayin_ani.strftime('%Y-%m-%d %H:%M')} UTC\n\n"
        f"**Başlık:** {meta['baslik']}\n\n**Açıklama:**\n\n```\n{meta['aciklama']}\n```\n\n"
        f"**Etiketler:** {', '.join(meta['etiketler'])}\n",
        encoding="utf-8",
    )
    return hedef


def main() -> None:
    bugun = dt.datetime.now(dt.UTC).date()
    mod = os.environ.get("OTOMAT_YAYIN", "teslim")
    kayit: dict = {"tarih": bugun.isoformat(), "mod": mod}
    db = durum.baglan()
    try:
        paketler, hatalar = topla()
        kayit.update(paket_sayisi=len(paketler), kaynak_hatalari=hatalar)
        paket, kalip, sablon = sec(paketler, db, bugun)
        dizin = KOK / "calisma" / "gunluk" / bugun.isoformat() / re.sub(r"[^A-Za-z0-9]+", "_", paket.anahtar)[:60]
        meta = uret(paket, kalip, sablon, dizin, bugun.isoformat())
        diller = hazirla(dizin)
        yayin_ani = dt.datetime.combine(bugun + dt.timedelta(days=1), dt.time(YAYIN_SAATI_UTC), dt.UTC)
        video_id = yayinla_api(dizin, yayin_ani) if mod == "api" else None
        if mod != "api":
            kayit["teslim"] = str(teslime_koy(dizin, bugun, yayin_ani).relative_to(KOK))
        durum.kaydet(db, paket, bugun, video_id)
        kayit.update(
            durum="tamam",
            anahtar=paket.anahtar,
            hash=paket.hash,
            kalip=kalip,
            sablon=sablon,
            baslik=meta["baslik"],
            kaynak=meta["secim"]["kaynak"],
            diller=list(diller["yerel"]),
            video_id=video_id,
            yayin_ani=yayin_ani.isoformat(),
            sure_sn=meta["sure_sn"],
        )
    except Exception as e:
        kayit.update(durum="hata", hata=f"{type(e).__name__}: {e}"[:500])
        raise
    finally:
        RAPOR.parent.mkdir(parents=True, exist_ok=True)
        with open(RAPOR, "a", encoding="utf-8") as f:
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
        print(json.dumps(kayit, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
