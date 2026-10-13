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


HIKAYE = _K.tur == "hikaye"  # Earth ve Orbit 2026-10-08'den beri hikâye motorunda (otomat/hikaye)
HIKAYE_TEKRAR_GUN = 3650  # bir hikâye kanalda bir kez anlatılır
HIKAYE_DENEME = 3  # senaryo hakemden geçmezse o hikâye düşer, sıradaki denenir
HAVUZ_ESIK = 21  # anlatılmamış hikâye bunun altına inince alarm (havuz genişletme işi ~3 hafta önceden görünsün)
EN_COK = 2  # buffer/api: bir koşuda en çok video (~2.000 neuron/video; iki kanal günlük 10.000'lik kotayı paylaşır)


def sec(paketler: list[OlguPaketi], db, bugun: dt.date, deneme: int = 0) -> tuple[OlguPaketi, str, str, dict]:
    """Konu (kol) ve kanca kalıbını haydut seçer; paket ve görsel şablon kol içinde tohumlu rastgele."""
    gun = HIKAYE_TEKRAR_GUN if HIKAYE else durum.TEKRAR_GUN
    taze = [p for p in paketler if durum.taze_mi(db, p, bugun, gun)]
    if not taze:
        raise RuntimeError(f"taze paket kalmadı (tekrar engeli {gun} gün)")
    r = random.Random(bugun.isoformat() + (f":{deneme}" if deneme else ""))
    kaliplar = list(_K.kaliplar) if HIKAYE else list(anlatim.KALIPLAR)
    kol, kalip, log = haydut.sec(db, bugun, sorted({p.kol for p in taze}), kaliplar, r)
    paket = r.choice([p for p in taze if p.kol == kol])
    return paket, kalip, r.choice(sablonlar.secenekler(paket)), log


def _klasor(bugun: dt.date, anahtar: str) -> Path:
    return KOK / "calisma" / "gunluk" / bugun.isoformat() / re.sub(r"[^A-Za-z0-9]+", "_", anahtar)[:60]


def uretim_dosyalari(ad: str) -> list[Path]:
    """Bu koşunun (calisma/gunluk/<gün>/<anahtar>/) ve önceki koşuların (calisma/onceki/<koşu>/<gün>/<anahtar>/;
    gunluk.yml son koşuların artifact'ını koşu başına ayrı klasöre indirir) üretim klasörlerindeki `ad` dosyaları,
    önce bu koşu, sonra en yeni koşu. Önceki koşular artifact'a yeniden yüklenmez (artifact'lar her koşuda öncekileri
    de taşıyıp 44 → 73 MB büyüyordu, 2026-10-09)."""
    calisma = KOK / "calisma"
    bu = sorted((calisma / "gunluk").glob(f"*/*/{ad}"))
    return bu + sorted((calisma / "onceki").glob(f"*/*/*/{ad}"), reverse=True)


def hazir_uretim(paketler: list[OlguPaketi], db, bugun: dt.date):
    """Önceki koşudan kalan, yayın kabulünden geçmiş ama kanala çıkmamış üretim. Kota harcamadan kullanılır: 10-09'da
    ffprobe hatası 5 hazır videoyu ve günün kotasını yaktı. Yoksa None."""
    from otomat.hikaye import kabul

    taze = {p.anahtar: p for p in paketler if durum.taze_mi(db, p, bugun, HIKAYE_TEKRAR_GUN)}
    for meta_yolu in uretim_dosyalari("meta.json"):
        try:
            meta = json.loads(meta_yolu.read_text(encoding="utf-8"))
            paket = taze.get(meta["paket"]["anahtar"])
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if paket is None or meta["paket"].get("hash") != paket.hash or kabul.denetle(meta_yolu):
            continue
        dizin = _klasor(bugun, paket.anahtar)
        if dizin != meta_yolu.parent:
            shutil.copytree(meta_yolu.parent, dizin, dirs_exist_ok=True)
        secim_logu = {"hazir": str(meta_yolu.parent.relative_to(KOK).as_posix()), "degisti": [], "odul_sayisi": 0}
        return paket, meta["secim"]["kalip"], meta["secim"]["sablon"], secim_logu, dizin, meta
    return None


def yarim_uretimi_getir(paket: OlguPaketi, dizin: Path) -> str | None:
    """Kotaya takılıp yarım kalmış üretimin hakemden geçmiş senaryosu ve biten sahne görselleri `dizin`e kopyalanır
    (hikaye/uretim.senaryo_al kullanır, kota ikinci kez harcanmaz). Kopyalanan klasör ya da None."""
    from otomat.hikaye.uretim import SENARYO

    if (dizin / SENARYO).exists():
        return None
    for yol in uretim_dosyalari(SENARYO):
        try:
            d = json.loads(yol.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if yol.parent == dizin or (d.get("anahtar"), d.get("hash")) != (paket.anahtar, paket.hash):
            continue
        dizin.mkdir(parents=True, exist_ok=True)
        for dosya in [yol, *yol.parent.glob("sahne_*.jpg")]:
            shutil.copy2(dosya, dizin / dosya.name)
        return str(yol.parent.relative_to(KOK).as_posix())
    return None


class HikayeDustu(RuntimeError):
    """Denenen hikâyelerin hiçbiri hakemden ya da yayın kabulünden geçmedi."""


def hikaye_uret(paketler: list[OlguPaketi], db, bugun: dt.date, kayit: dict):
    """Senaryosu hakemden ve videosu yayın kabulünden (hikaye/kabul.py) geçen ilk hikâye; geçmeyen bir daha
    seçilmesin diye kaydedilir (video yok). Önce hazır üretim aranır, sonra yarım kalmış üretim sürdürülür."""
    from otomat.hikaye import cf, kabul
    from otomat.hikaye.kaynaklar import KaynakHatasi
    from otomat.hikaye.senaryo import SenaryoHatasi
    from otomat.hikaye.uretim import DurumHatasi
    from otomat.hikaye.uretim import uret as h_uret

    if hazir := hazir_uretim(paketler, db, bugun):
        kayit["hazir"] = hazir[3]["hazir"]
        return hazir
    dusen = []
    for deneme in range(HIKAYE_DENEME):
        paket, kalip, sablon, secim_logu = sec(paketler, db, bugun, deneme)
        dizin = _klasor(bugun, paket.anahtar)
        if yarim := yarim_uretimi_getir(paket, dizin):
            kayit["devam"] = yarim
        try:
            meta = h_uret(paket, kalip, sablon, dizin, bugun.isoformat())
        except SenaryoHatasi as e:
            sorunlar = e.sorunlar[-1][:5]
        # sahne görseli güvenlik filtresinde (Earth, 10-09); makale yok; değişen görünüş karede tutmadı (Orbit, 10-13)
        except (cf.FiltreHatasi, KaynakHatasi, DurumHatasi) as e:
            sorunlar = [str(e)[:200]]
        else:
            if not (sorunlar := kabul.denetle(dizin / "meta.json")):
                # senaryo önceki koşudan sürdüyse kalıp onunki (haydut doğru kalıbı öğrensin)
                return paket, (meta.get("secim") or {}).get("kalip", kalip), sablon, secim_logu, dizin, meta
        durum.kaydet(db, paket, bugun, None)
        # düşen hikâyenin harcadığı kota da raporda görünsün (uret sayacı her hikâyede sıfırlar)
        dusen.append({"anahtar": paket.anahtar, "sorunlar": sorunlar, "neuron": round(cf.NEURON["toplam"])})
        kayit["dusen_hikayeler"] = dusen
    raise HikayeDustu(
        f"{HIKAYE_DENEME} hikâye de hakemden ya da yayın kabulünden geçmedi: "
        + "; ".join(f"{d['anahtar']}: {d['sorunlar']}" for d in dusen)[:800]
    )


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
    return durum.yayin_slotu(db, simdi, YAYIN_SAATI_UTC)


def yayinla_buffer(dizin: Path, yayin_ani: dt.datetime | None, ad: str, alarmlar: list[str]) -> str:
    """Buffer private yükler; planlı yayın, etiket, yerelleştirme ve altyazı bizim API'mizle. Video kanala çıktıktan
    sonraki hata yayını geri almaz: alarm yazılır, video id yine döner (seçim kaydı ve analitik için)."""
    from otomat.yayin import buffer, youtube

    meta = json.loads((dizin / "meta.json").read_text(encoding="utf-8"))
    yerel_yol = dizin / "yerel.json"
    yerel = json.loads(yerel_yol.read_text(encoding="utf-8"))["yerel"] if yerel_yol.exists() else None
    dosya = f"{_K.id}-{ad}.mp4"  # iki kanal aynı site reposunu ve aynı slot gününü paylaşıyor (10-09 çakıştı)
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


def marka_adimi(yt, kayit: dict, alarmlar: list[str]) -> None:
    """Kanal yeni adını aldıysa kimliği bir kez uygular (Faz 15); düşerse üretim sürer."""
    from otomat.yayin import marka

    try:
        kayit["marka"] = marka.kontrol(yt)
    except Exception as e:  # noqa: BLE001
        kayit["marka"] = f"hata: {type(e).__name__}"
        alarmlar.append("**Kanal kimliği uygulanamadı** (üretim sürdü):\n\n" + _hata(e))


def rapor_adimi(db, bugun: dt.date, yt, ya, kayit: dict, alarmlar: list[str]) -> None:
    """Biten son haftanın raporu yoksa yazılır (pazartesi koşusu pist dolu diye atlanırsa ertesi koşuda)."""
    if (bekleyen := rapor.bekleyen(bugun)) is None:
        return
    try:
        hata = None if yt else kayit.get("analitik", {}).get("hata")
        kayit["rapor"] = str(rapor.yaz(db, *bekleyen, yt, ya, hata).relative_to(KOK))
    except Exception as e:  # noqa: BLE001
        alarmlar.append("**Haftalık rapor yazılamadı:**\n\n" + _hata(e))


def havuz_adimi(paketler: list[OlguPaketi], db, bugun: dt.date, kayit: dict, alarmlar: list[str]) -> None:
    """Hikâye havuzunda anlatılmamış kaç hikâye kaldı; azalınca alarm (havuz sessizce bitip kanal durmasın)."""
    kalan = sum(durum.taze_mi(db, p, bugun, HIKAYE_TEKRAR_GUN) for p in paketler)
    kayit["havuz_kalan"] = kalan
    if kalan < HAVUZ_ESIK:
        alarmlar.append(
            f"**Hikâye havuzu azalıyor:** {kalan} anlatılmamış hikâye kaldı (günde 1 videoyla ~{kalan} gün). "
            f"Havuz genişletilmeli (`{_K.veri.relative_to(KOK).as_posix()}`, süzgeç: otomat/hikaye/kaynaklar.py)."
        )


def alarm_yaz(bugun: dt.date, alarmlar: list[str]) -> None:
    ALARM.unlink(missing_ok=True)
    if alarmlar:
        ALARM.parent.mkdir(parents=True, exist_ok=True)
        ALARM.write_text(f"Günlük koşu {bugun.isoformat()}:\n\n" + "\n\n---\n\n".join(alarmlar) + "\n", "utf-8")


def bir_video(paketler, db, gun: dt.date, yayin_ani: dt.datetime, mod: str, kayit: dict, alarmlar: list[str]):
    """`gun` slotunun videosu: seç → üret → çevir → yayınla (ya da teslim paketi) → kaydet."""
    if HIKAYE:
        paket, kalip, sablon, secim_logu, dizin, meta = hikaye_uret(paketler, db, gun, kayit)
    else:
        paket, kalip, sablon, secim_logu = sec(paketler, db, gun)
        dizin = _klasor(gun, paket.anahtar)
        meta = uret(paket, kalip, sablon, dizin, gun.isoformat())
    if HIKAYE:
        from otomat.hikaye import cf

        cf.NEURON["toplam"] = 0.0
    diller = hazirla(dizin)
    video_id = None
    if mod == "api":
        video_id = yayinla_api(dizin, yayin_ani)
    elif mod == "buffer":
        try:
            video_id = yayinla_buffer(dizin, yayin_ani, gun.isoformat(), alarmlar)
        except Exception as e:  # noqa: BLE001
            alarmlar.append("**Buffer yayını düştü**, video Plan B paketine kondu:\n\n" + _hata(e))
    if video_id is None:
        kayit["teslim"] = str(teslime_koy(dizin, gun).relative_to(KOK))
    durum.kaydet(db, paket, gun, video_id)
    durum.secim_kaydet(db, gun, paket, kalip, sablon, meta["baslik"], yayin_ani, video_id, secim_logu)
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
        # neuron: bu koşunun harcaması; hazır üretimin kotası onu üreten koşunun kaydında (çift sayılmasın)
        **(
            {
                "neuron": (0 if "hazir" in kayit else meta["neuron"]) + round(cf.NEURON["toplam"]),
                "ceviri_neuron": round(cf.NEURON["toplam"]),
                "zaman_sn": meta["zaman_sn"],
            }
            if HIKAYE
            else {}
        ),
        haydut={"degisti": secim_logu["degisti"], "odul_sayisi": secim_logu["odul_sayisi"]},
    )


def main() -> None:
    """buffer/api: pistte boş slot oldukça (en çok EN_COK) video üretir; teslim: günde bir. Her video günlük rapora
    ayrı satır yazar (`tarih` = videonun slot günü, `kosu` = koşu günü). Pist doluysa yalnız bekleyen haftalık rapor
    yazılır (o da yoksa koşu hiçbir şey yapmadan biter)."""
    from otomat.hikaye.cf import KotaHatasi

    simdi = dt.datetime.now(dt.UTC)
    bugun = simdi.date()
    mod = os.environ.get("OTOMAT_YAYIN", "teslim")
    pist = mod in ("api", "buffer")
    genel: dict = {"tarih": bugun.isoformat(), "mod": mod}
    kayitlar: list[dict] = []
    alarmlar: list[str] = []
    db = durum.baglan()
    durum.gecmisi_doldur(db, RAPOR)
    if durum.pist_dolu(db, simdi, mod):
        print(f"{bugun.isoformat()}: " + ("pist dolu" if pist else "bugün zaten üretildi") + "; üretim yok.")
        if rapor.bekleyen(bugun) is not None:  # yalnız rapor: üretim kaydı (gunluk.jsonl) yazılmaz
            yt, ya = analitik_adimi(db, bugun, genel, alarmlar)
            rapor_adimi(db, bugun, yt, ya, genel, alarmlar)
            alarm_yaz(bugun, alarmlar)
            print(json.dumps(genel, ensure_ascii=False, indent=1))
        return
    yt, ya = analitik_adimi(db, bugun, genel, alarmlar)
    if HIKAYE and yt is not None:
        marka_adimi(yt, genel, alarmlar)
    try:
        if HIKAYE:
            from otomat.hikaye import kaynaklar as hikaye_kaynaklari

            paketler, hatalar = hikaye_kaynaklari.topla()
            havuz_adimi(paketler, db, bugun, genel, alarmlar)
        else:
            paketler, hatalar = topla()
        genel.update(paket_sayisi=len(paketler), kaynak_hatalari=hatalar)
        if hatalar:
            alarmlar.append(
                "**Veri kaynağı hatası** (o kol bugün dışarıda kaldı):\n\n" + "\n".join(f"- {h}" for h in hatalar)
            )
        for _ in range(EN_COK if pist else 1):
            if pist:
                yayin_ani = yayin_slotu(db, dt.datetime.now(dt.UTC))
                if yayin_ani.date() > bugun + dt.timedelta(days=durum.PIST_GUN):
                    break
            else:
                yayin_ani = dt.datetime.combine(bugun + dt.timedelta(days=1), dt.time(YAYIN_SAATI_UTC), dt.UTC)
            gun = yayin_ani.date() if pist else bugun
            kayit = {**genel, "tarih": gun.isoformat(), "kosu": bugun.isoformat()}
            kayitlar.append(kayit)
            try:
                bir_video(paketler, db, gun, yayin_ani, mod, kayit, alarmlar)
            except (KotaHatasi, HikayeDustu) as e:
                kota = isinstance(e, KotaHatasi)
                kayit.update(
                    durum="kota" if kota else "hata", hata=f"{'' if kota else type(e).__name__ + ': '}{e}"[:500]
                )
                if pist and gun > bugun + dt.timedelta(days=1):
                    # yarının videosu kanalda planlı: sonraki koşu bu slotu yeniden dener, alarm gerekmez (10-11'de
                    # 3. pist gününün hikâyeleri düştü, alarm çaldı, akşam koşusu slotu doldurdu)
                    break
                raise
            if kayit["video_id"] is None:
                break  # kanala çıkmadı (Plan B): slot boş kalır, aynı slota ikinci video üretilmez
    except Exception as e:
        son = kayitlar[-1] if kayitlar else genel
        if son.get("durum") != "kota":  # kota raporda ayrı sayılır (alarm yine yazılır: yarının slotu boş)
            son.update(durum="hata", hata=f"{type(e).__name__}: {e}"[:500])
        alarmlar.append("**Günün videosu üretilemedi:**\n\n" + _hata(e))
        raise
    finally:
        if mod == "buffer":
            from otomat.yayin import buffer

            (kayitlar[-1] if kayitlar else genel)["buffer_istek"] = buffer.ISTEK["sayi"]
        rapor_adimi(db, bugun, yt, ya, genel, alarmlar)
        alarm_yaz(bugun, alarmlar)
        RAPOR.parent.mkdir(parents=True, exist_ok=True)
        with open(RAPOR, "a", encoding="utf-8") as f:
            for k in kayitlar or [genel]:
                f.write(json.dumps(k, ensure_ascii=False) + "\n")
        print(json.dumps(kayitlar or [genel], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
