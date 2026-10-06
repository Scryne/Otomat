"""Günlük koşu: analitik → veri topla → haydut seçer → üret → çevir → yayınla (API) ya da teslim paketine koy (Plan B).

Ortam:
- OTOMAT_YAYIN = "buffer" | "api" | "teslim" (varsayılan teslim). buffer: Buffer yükler, planlama ve altyazı bizim
  API'mizle (audit gerektirmez, docs/arastirma/06); api: audit gelince doğrudan yükleme; teslim: Plan B Release
  paketi. Buffer yayını düşerse video teslim paketine düşer, alarm yazılır.
- OTOMAT_KANAL: kanal profili (kanallar/<id>/kanal.toml, varsayılan earth).
- YT_ISTEMCI_JSON (tüm kanallar), YT_TOKEN_JSON<sir_eki> (kanalın token'ı; yükleme ve analitik); buffer ayrıca
  BUFFER_API_KEY ve OTOMAT_SITE_ANAHTAR (otomat-site deploy key) ister.
Gün zaten üretildiyse (yedek cron, elle tetikleme) hiçbir şey yapmadan çıkar.
Pazartesi bir önceki haftanın raporunu yazar. Bir şey ters giderse `calisma/alarm.md` yazılır; Actions bunu
GitHub issue'suna çevirir (gunluk.yml), sonraki temiz koşu issue'yu kapatır.
"""

import datetime as dt
import json
import os
import random
import re
import shutil
from pathlib import Path

from otomat import analitik, durum, haydut, kanal, rapor
from otomat.anlati import anlatim
from otomat.ayarlar import KOK
from otomat.gorsel import sablonlar
from otomat.uretim import uret
from otomat.veri import OlguPaketi
from otomat.veri.toplayici import topla
from otomat.yayin.hazirla import hazirla

RAPOR = kanal.aktif().raporlar / "gunluk.jsonl"
YAYIN_SAATI_UTC = kanal.aktif().yayin_saati_utc
ALARM = KOK / "calisma" / "alarm.md"
_K = kanal.aktif()
YETKI_COZUMU = (
    f"Token düşmüş (invalid_grant). Yerelde `OTOMAT_KANAL={_K.id} uv run python -m otomat.yayin.youtube yetki` "
    f"(izin ekranında **{_K.ad}** kanalını seç), sonra "
    f"`gh secret set {_K.token_degiskeni} < sirlar/{_K.token_dosyasi.name}`."
)


def sec(paketler: list[OlguPaketi], db, bugun: dt.date) -> tuple[OlguPaketi, str, str, dict]:
    """Konu (kol) ve kanca kalıbını haydut seçer; paket ve görsel şablon kol içinde tohumlu rastgele."""
    taze = [p for p in paketler if durum.taze_mi(db, p, bugun)]
    if not taze:
        raise RuntimeError("taze paket kalmadı (tekrar engeli 60 gün)")
    r = random.Random(bugun.isoformat())
    kol, kalip, log = haydut.sec(db, bugun, sorted({p.kol for p in taze}), list(anlatim.KALIPLAR), r)
    paket = r.choice([p for p in taze if p.kol == kol])
    return paket, kalip, r.choice(sablonlar.secenekler(paket)), log


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


def yayin_slotu(db, simdi: dt.datetime) -> dt.datetime:
    """Günde tek yayın, YAYIN_SAATI_UTC'de: en erken bir saat sonrası, kanala yüklenmiş son videonun ertesi günü."""
    aday = simdi.replace(hour=YAYIN_SAATI_UTC, minute=0, second=0, microsecond=0)
    if aday < simdi + dt.timedelta(hours=1):
        aday += dt.timedelta(days=1)
    son = db.execute("SELECT max(yayin_ani) FROM secimler WHERE video_id IS NOT NULL").fetchone()[0]
    if son:
        ertesi = dt.datetime.fromisoformat(son).astimezone(dt.UTC) + dt.timedelta(days=1)
        aday = max(aday, ertesi.replace(hour=YAYIN_SAATI_UTC, minute=0, second=0, microsecond=0))
    return aday


def yayinla_buffer(dizin: Path, yayin_ani: dt.datetime | None, ad: str, alarmlar: list[str]) -> str:
    """Buffer private yükler; planlı yayın, etiket, yerelleştirme ve altyazı bizim API'mizle. Video kanala çıktıktan
    sonraki hata yayını geri almaz: alarm yazılır, video id yine döner (seçim kaydı ve analitik için)."""
    from otomat.yayin import buffer, youtube

    meta = json.loads((dizin / "meta.json").read_text(encoding="utf-8"))
    yerel_yol = dizin / "yerel.json"
    yerel = json.loads(yerel_yol.read_text(encoding="utf-8"))["yerel"] if yerel_yol.exists() else None
    dosya = f"{ad}.mp4"
    url = buffer.medya_koy(dizin / "video.mp4", dosya)
    try:
        video_id = buffer.gonder(url, meta["baslik"], meta["aciklama"])
    finally:
        try:
            buffer.medya_kaldir(dosya)
        except Exception as e:  # noqa: BLE001
            alarmlar.append(f"**Site reposundan medya silinemedi** (`media/{dosya}`, zararsız): {e}"[:500])
    try:
        yt = youtube.servis()
        youtube.duzenle(video_id, meta["baslik"], meta["aciklama"], meta["etiketler"], yayin_ani, yerel, yt=yt)
        for srt in sorted(dizin.glob("*.srt")):
            youtube.altyazi_ekle(video_id, srt.stem.split("_")[-1], srt.read_text(encoding="utf-8"), yt=yt)
    except Exception as e:  # noqa: BLE001
        alarmlar.append(f"**Video yüklendi ama planlanamadı** (`{video_id}` private kalmış olabilir):\n\n" + _hata(e))
    return video_id


def teslime_koy(dizin: Path, bugun: dt.date) -> Path:
    """Dosyalar tarih önekiyle düz bir klasöre: Actions bunları haftanın GitHub Release'ine ekler ve o haftanın
    YUKLE.md'lerinden yayın saatli HAFTA.md'yi üretir (yayin/hafta.py)."""
    hedef = KOK / "teslim"
    hedef.mkdir(parents=True, exist_ok=True)
    on = bugun.isoformat()
    for ad in ["video.mp4", *[p.name for p in dizin.glob("*.srt")]]:
        shutil.copy(dizin / ad, hedef / f"{on}_{ad}")
    meta = json.loads((dizin / "meta.json").read_text(encoding="utf-8"))
    (hedef / f"{on}_YUKLE.md").write_text(
        f"# {bugun.isoformat()}\n\nYayın saati ve sıra: bu haftanın HAFTA.md dosyası.\n\n"
        f"**Başlık:** {meta['baslik']}\n\n**Açıklama:**\n\n```\n{meta['aciklama']}\n```\n\n"
        f"**Etiketler:** {', '.join(meta['etiketler'])}\n",
        encoding="utf-8",
    )
    return hedef


def _hata(e: Exception) -> str:
    from otomat.yayin.youtube import YetkiHatasi

    metin = f"{type(e).__name__}: {e}"[:500]
    return f"{metin}\n\n{YETKI_COZUMU}" if isinstance(e, YetkiHatasi) else metin


def analitik_adimi(db, bugun: dt.date, kayit: dict, alarmlar: list[str]):
    """Eşleştir + ölç; düşerse üretim yine sürer. (yt, ya) ya da (None, None) döner."""
    try:
        yt, ya = analitik.servisler()
        sonuc = analitik.topla(db, bugun, yt, ya)
        kayit["analitik"] = {"eslesen": len(sonuc["eslesen"]), "olculen": len(sonuc["olculen"])}
        return yt, ya
    except Exception as e:  # noqa: BLE001
        kayit["analitik"] = {"hata": f"{type(e).__name__}: {e}"[:300]}
        alarmlar.append("**Analitik toplanamadı** (üretim sürdü, haydut eski veriyle seçti):\n\n" + _hata(e))
        return None, None


def rapor_adimi(db, bugun: dt.date, yt, ya, kayit: dict, alarmlar: list[str]) -> None:
    """Pazartesi: geçen haftanın raporu (yoksa)."""
    if bugun.isoweekday() != 1:
        return
    yil, hafta, _ = (bugun - dt.timedelta(days=7)).isocalendar()
    if rapor.dosya(yil, hafta).exists():
        return
    try:
        hata = None if yt else kayit.get("analitik", {}).get("hata")
        kayit["rapor"] = str(rapor.yaz(db, yil, hafta, yt, ya, hata).relative_to(KOK))
    except Exception as e:  # noqa: BLE001
        alarmlar.append("**Haftalık rapor yazılamadı:**\n\n" + _hata(e))


def alarm_yaz(bugun: dt.date, alarmlar: list[str]) -> None:
    ALARM.unlink(missing_ok=True)
    if alarmlar:
        ALARM.parent.mkdir(parents=True, exist_ok=True)
        ALARM.write_text(f"Günlük koşu {bugun.isoformat()}:\n\n" + "\n\n---\n\n".join(alarmlar) + "\n", "utf-8")


def main() -> None:
    bugun = dt.datetime.now(dt.UTC).date()
    mod = os.environ.get("OTOMAT_YAYIN", "teslim")
    kayit: dict = {"tarih": bugun.isoformat(), "mod": mod}
    alarmlar: list[str] = []
    db = durum.baglan()
    durum.gecmisi_doldur(db, RAPOR)
    if durum.bugun_secildi_mi(db, bugun):
        print(f"{bugun.isoformat()} zaten üretildi; koşu atlandı.")
        return
    yt, ya = analitik_adimi(db, bugun, kayit, alarmlar)
    try:
        paketler, hatalar = topla()
        kayit.update(paket_sayisi=len(paketler), kaynak_hatalari=hatalar)
        if hatalar:
            alarmlar.append(
                "**Veri kaynağı hatası** (o kol bugün dışarıda kaldı):\n\n" + "\n".join(f"- {h}" for h in hatalar)
            )
        paket, kalip, sablon, secim_logu = sec(paketler, db, bugun)
        dizin = KOK / "calisma" / "gunluk" / bugun.isoformat() / re.sub(r"[^A-Za-z0-9]+", "_", paket.anahtar)[:60]
        meta = uret(paket, kalip, sablon, dizin, bugun.isoformat())
        diller = hazirla(dizin)
        if mod in ("api", "buffer"):
            yayin_ani = yayin_slotu(db, dt.datetime.now(dt.UTC))
        else:
            yayin_ani = dt.datetime.combine(bugun + dt.timedelta(days=1), dt.time(YAYIN_SAATI_UTC), dt.UTC)
        video_id = None
        if mod == "api":
            video_id = yayinla_api(dizin, yayin_ani)
        elif mod == "buffer":
            try:
                video_id = yayinla_buffer(dizin, yayin_ani, bugun.isoformat(), alarmlar)
            except Exception as e:  # noqa: BLE001
                alarmlar.append("**Buffer yayını düştü**, video Plan B paketine kondu:\n\n" + _hata(e))
        if video_id is None:
            kayit["teslim"] = str(teslime_koy(dizin, bugun).relative_to(KOK))
        durum.kaydet(db, paket, bugun, video_id)
        durum.secim_kaydet(db, bugun, paket, kalip, sablon, meta["baslik"], yayin_ani, video_id, secim_logu)
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
            haydut={"degisti": secim_logu["degisti"], "odul_sayisi": secim_logu["odul_sayisi"]},
        )
    except Exception as e:
        kayit.update(durum="hata", hata=f"{type(e).__name__}: {e}"[:500])
        alarmlar.append("**Günün videosu üretilemedi:**\n\n" + _hata(e))
        raise
    finally:
        rapor_adimi(db, bugun, yt, ya, kayit, alarmlar)
        alarm_yaz(bugun, alarmlar)
        RAPOR.parent.mkdir(parents=True, exist_ok=True)
        with open(RAPOR, "a", encoding="utf-8") as f:
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
        print(json.dumps(kayit, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
