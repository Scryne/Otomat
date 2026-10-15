"""Günlük koşu: analitik → veri topla → haydut seçer → üret → çevir → yayınla (API) ya da teslim paketine koy (Plan B).

Ortam:
- OTOMAT_YAYIN = "buffer" | "api" | "teslim" (varsayılan teslim). buffer: Buffer yükler, planlama ve altyazı bizim
  API'mizle (audit gerektirmez, docs/arastirma/06); api: audit gelince doğrudan yükleme; teslim: Plan B Release
  paketi. Buffer yayını düşerse video kanala çıkmaz ve hikâye harcanmaz: sonraki koşu aynı videoyu hazır üretimden
  (artifact) kota harcamadan yeniden gönderir; alarm yazılır.
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
from otomat.ayarlar import KOK
from otomat.veri import OlguPaketi
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


# Arşiv veri motoru (kanallar/veri-*): hikâye kanalları onu hiç çalıştırmaz. Modül düzeyinde import edilince her
# koşu 28 modülü ve matplotlib'i yüklüyordu; arşivdeki bir kırılma canlı kanalları açılışta düşürürdü.
def topla():
    from otomat.veri.toplayici import topla as veri_topla

    return veri_topla()


def uret(*args):
    from otomat.uretim import uret as veri_uret

    return veri_uret(*args)


def sec(paketler: list[OlguPaketi], db, bugun: dt.date, deneme: int = 0) -> tuple[OlguPaketi, str, str, dict]:
    """Konu (kol) ve kanca kalıbını haydut seçer; paket ve görsel şablon kol içinde tohumlu rastgele."""
    gun = HIKAYE_TEKRAR_GUN if HIKAYE else durum.TEKRAR_GUN
    taze = [p for p in paketler if durum.taze_mi(db, p, bugun, gun)]
    if not taze:
        raise RuntimeError(f"taze paket kalmadı (tekrar engeli {gun} gün)")
    r = random.Random(bugun.isoformat() + (f":{deneme}" if deneme else ""))
    if HIKAYE:
        kaliplar = list(_K.kaliplar)
    else:
        from otomat.anlati import anlatim

        kaliplar = list(anlatim.KALIPLAR)
    kol, kalip, log = haydut.sec(db, bugun, sorted({p.kol for p in taze}), kaliplar, r)
    paket = r.choice([p for p in taze if p.kol == kol])
    if HIKAYE:
        return paket, kalip, paket.gorsel["sablon"], log
    from otomat.gorsel import sablonlar

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


def yarim_aday(paketler: list[OlguPaketi], db, bugun: dt.date) -> tuple[OlguPaketi, str] | None:
    """Kotaya takılıp yarım kalmış (senaryosu hakemden geçmiş, videosu yok), hâlâ anlatılmamış hikâye ve kalıbı.
    Haydut seçimi koşudan koşuya değişebiliyor (yeni ölçüm, farklı gün tohumu): yarım üretim yalnız aynı hikâye yeniden
    seçilirse sürüyordu, öbür durumda senaryonun ve görsellerin kotası boşa gidiyordu."""
    from otomat.hikaye.uretim import SENARYO

    taze = {(p.anahtar, p.hash): p for p in paketler if durum.taze_mi(db, p, bugun, HIKAYE_TEKRAR_GUN)}
    for yol in uretim_dosyalari(SENARYO):
        if (yol.parent / "meta.json").exists():
            continue  # bitmiş üretim: hazır üretim ya da kabulden düşmüş (onu hazir_uretim/kabul eler)
        try:
            d = json.loads(yol.read_text(encoding="utf-8"))
            paket = taze.get((d["anahtar"], d["hash"]))
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if paket is not None and d.get("kalip") in _K.kaliplar:
            return paket, d["kalip"]
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
    yarim_paket = yarim_aday(paketler, db, bugun)
    for deneme in range(HIKAYE_DENEME):
        if deneme == 0 and yarim_paket:
            paket, kalip = yarim_paket
            sablon, secim_logu = paket.gorsel["sablon"], {"degisti": [], "odul_sayisi": 0, "yarim": True}
        else:
            paket, kalip, sablon, secim_logu = sec(paketler, db, bugun, deneme)
        dizin = _klasor(bugun, paket.anahtar)
        if yarim := yarim_uretimi_getir(paket, dizin):
            kayit["devam"] = yarim
        harca = True
        try:
            meta = h_uret(paket, kalip, sablon, dizin, bugun.isoformat())
        except cf.KotaHatasi:
            raise  # kota hikâyenin suçu değil: sonraki koşu senaryoyu ve görselleri sürdürür
        except SenaryoHatasi as e:
            sorunlar = e.sorunlar[-1][:5]
        # sahne görseli güvenlik filtresinde (Earth, 10-09); makale yok; değişen görünüş karede tutmadı (Orbit, 10-13)
        except (cf.FiltreHatasi, KaynakHatasi, DurumHatasi) as e:
            sorunlar = [str(e)[:200]]
        except cf.CFHatasi as e:
            # Cloudflare dört denemede de yanıt vermedi (kesinti ya da bu isteğe özgü model hatası): bütün koşu
            # düşmesin, sıradaki hikâye denensin; ama kesintide hikâye havuzdan yanmasın (harcanmaz)
            sorunlar, harca = [f"Cloudflare: {str(e)[:200]}"], False
        else:
            if not (sorunlar := kabul.denetle(dizin / "meta.json")):
                # senaryo önceki koşudan sürdüyse kalıp onunki (haydut doğru kalıbı öğrensin)
                return paket, (meta.get("secim") or {}).get("kalip", kalip), sablon, secim_logu, dizin, meta
        if harca:
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
    # video kanala çıktı: altyazı hatası video id'yi kaybettirmesin (hazır üretim aynı videoyu yeniden yüklerdi)
    for srt in sorted(dizin.glob("*.srt")):
        try:
            youtube.altyazi_ekle(video_id, srt.stem.split("_")[-1], srt.read_text(encoding="utf-8"), yt=yt)
        except Exception as e:  # noqa: BLE001
            print(f"altyazı yüklenemedi ({video_id}, {srt.stem}): {type(e).__name__}: {e}")
    return video_id


def yayin_slotu(db, simdi: dt.datetime) -> dt.datetime:
    return durum.yayin_slotu(db, simdi, YAYIN_SAATI_UTC)


def yayinla_buffer(dizin: Path, yayin_ani: dt.datetime | None, ad: str, alarmlar: list[str], db=None) -> str:
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
    except Exception as e:  # noqa: BLE001
        if db is not None:
            durum.planlanamadi(db, video_id, yayin_ani)
        alarmlar.append(
            f"**Video yüklendi ama planlanamadı** (`{video_id}`; sonraki koşunun pist denetimi yeniden planlar):\n\n"
            + _hata(e)
        )
        return video_id
    # altyazılar dil başına: biri (kota, geçici hata) düşünce öbürleri sürsün (400 birim/dil; eskiden ilk hata kalanı
    # atlıyordu)
    dusen = []
    for srt in sorted(dizin.glob("*.srt")):
        try:
            youtube.altyazi_ekle(video_id, srt.stem.split("_")[-1], srt.read_text(encoding="utf-8"), yt=yt)
        except Exception as e:  # noqa: BLE001
            dusen.append(f"{srt.stem}: {type(e).__name__}: {e}"[:200])
    if dusen:
        liste = "\n".join(f"- {d}" for d in dusen)
        alarmlar.append(f"**Altyazı yüklenemedi** (`{video_id}`, video planlı):\n\n{liste}")
    return video_id


def teslime_koy(dizin: Path, bugun: dt.date, anahtar: str = "") -> Path:
    """Dosyalar tarih (ve hikâye) önekiyle düz bir klasöre: Actions bunları haftanın GitHub Release'ine ekler ve o
    haftanın YUKLE.md'lerinden yayın saatli HAFTA.md'yi üretir (yayin/hafta.py). Hikâye öneki: aynı slota ikinci
    video düşerse Release'teki ilki `--clobber` ile eziliyordu."""
    hedef = KOK / "teslim"
    hedef.mkdir(parents=True, exist_ok=True)
    ek = re.sub(r"[^A-Za-z0-9]+", "-", anahtar.partition(":")[2])[:40].strip("-")
    on = bugun.isoformat() + (f"_{ek}" if ek else "")
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
    """Eşleştir + ölç; düşerse üretim yine sürer. (yt, ya) döner; servis kurulamadıysa (token) (None, None). Yalnız
    toplama düştüyse (Analytics 5xx, kota) servisler yine döner: eskiden pist denetimi ve çeviri onarımı da atlanıyor,
    bakım koşusunda planı düşmüş video slotunu kaçırıyordu."""
    try:
        yt, ya = analitik.servisler()
    except Exception as e:  # noqa: BLE001
        kayit["analitik"] = {"hata": f"{type(e).__name__}: {e}"[:300]}
        alarmlar.append("**Analitik toplanamadı** (üretim sürdü, haydut eski veriyle seçti):\n\n" + _hata(e))
        return None, None
    try:
        sonuc = analitik.topla(db, bugun, yt, ya)
        kayit["analitik"] = {"eslesen": len(sonuc["eslesen"]), "olculen": len(sonuc["olculen"])}
        if os.environ.get("OTOMAT_YAYIN", "teslim") in ("api", "buffer"):
            yetimleri_planla(db, sonuc["eslesen"])
    except Exception as e:  # noqa: BLE001
        kayit["analitik"] = {"hata": f"{type(e).__name__}: {e}"[:300]}
        alarmlar.append("**Analitik toplanamadı** (üretim sürdü, haydut eski veriyle seçti):\n\n" + _hata(e))
    return yt, ya


def yetimleri_planla(db, eslesen: list[tuple[str, str]]) -> None:
    """buffer/api'de başlıkla eşleşen video, sonucu okunamamış (GonderiBelirsiz) Buffer gönderisinin yetimidir: Buffer
    yüklemiş ama planlama hiç yapılmamış, private duruyor. Eşleşme slotu dolu saydırdığı için pist denetimi onu
    planlasın (metadata artifact'tan); eskiden slot sessizce kayboluyordu."""
    for tarih, video_id in eslesen:
        satir = db.execute("SELECT yayin_ani FROM secimler WHERE tarih = ?", (tarih,)).fetchone()
        if satir:
            durum.planlanamadi(db, video_id, dt.datetime.fromisoformat(satir[0]))


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


def uretim_klasoru(anahtar: str) -> Path | None:
    """Hikâyenin bu ya da önceki koşulardaki (artifact) üretim klasörü, en yenisi."""
    for meta_yolu in uretim_dosyalari("meta.json"):
        try:
            if json.loads(meta_yolu.read_text(encoding="utf-8"))["paket"]["anahtar"] == anahtar:
                return meta_yolu.parent
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return None


def _yeniden_yayinla(video_id: str, yayin_ani: dt.datetime, dizin: Path | None, yt) -> list[str]:
    """Planlaması düşen videonun metadata'sı, planı (geçmişse hemen public), yerelleştirmesi ve altyazıları; üretim
    klasörü yoksa yalnız plan (başlık ve açıklamayı Buffer yazmıştı). Yüklenemeyen altyazılar döner."""
    from otomat.yayin import youtube

    if dizin is None:
        youtube.planla(video_id, yayin_ani, yt=yt)
        return []
    meta = json.loads((dizin / "meta.json").read_text(encoding="utf-8"))
    yerel_yol = dizin / "yerel.json"
    yerel = json.loads(yerel_yol.read_text(encoding="utf-8"))["yerel"] if yerel_yol.exists() else None
    youtube.duzenle(video_id, meta["baslik"], meta["aciklama"], meta["etiketler"], yayin_ani, yerel, yt=yt)
    dusen = []
    for srt in sorted(dizin.glob("*.srt")):
        try:
            youtube.altyazi_ekle(video_id, srt.stem.split("_")[-1], srt.read_text(encoding="utf-8"), yt=yt)
        except Exception as e:  # noqa: BLE001
            dusen.append(f"{srt.stem}: {type(e).__name__}"[:120])
    return dusen


def pist_denetimi(db, yt, simdi: dt.datetime, kayit: dict, alarmlar: list[str]) -> None:
    """Planlı videolar kanalda gerçekten planlı mı? Buffer yükleyip `duzenle` düştüğünde video private ve plansız
    kalıyordu, slot dolu sayıldığı için hiçbir koşu onarmıyordu (yayın günü kaybolurdu).
    - Planlaması düştüğü kaydedilen (`planlanamayan`) video, yayın anı geçmiş olsa da onarılır: üretim klasörü
      artifact'ta duruyorsa metadata, plan, yerelleştirme ve altyazıyla; yoksa yalnız planla. Geçmiş an hemen public.
      Kanalda planlı/public bulunan kayıt çözülmüş sayılır.
    - Başka bir plansız private video elle çekilmiş olabilir: ona dokunulmaz, alarm olur. Kaybolan video alarm olur.
    Maliyet: 50 video başına 1 kota birimi (onarımda videos.update 50 + altyazı başına 400)."""
    from otomat.yayin import youtube

    cekilen = {v for (v,) in db.execute("SELECT video_id FROM geri_cekilen")}
    planli = {
        v: dt.datetime.fromisoformat(y).astimezone(dt.UTC)
        for v, y in db.execute("SELECT video_id, yayin_ani FROM secimler WHERE video_id IS NOT NULL")
        if v not in cekilen
    }
    yakin = {v: y for v, y in planli.items() if y > simdi}
    bekleyen = {
        v: dt.datetime.fromisoformat(y).astimezone(dt.UTC)
        for v, y in db.execute("SELECT video_id, yayin_ani FROM planlanamayan")
        if v not in cekilen
    }
    if not yakin and not bekleyen:
        return
    try:
        durumlar = youtube.durumlar(sorted(set(yakin) | set(bekleyen)), yt)
        anahtar = dict(db.execute("SELECT video_id, anahtar FROM secimler WHERE video_id IS NOT NULL"))
        onarilan, kayip, plansiz, eksik_altyazi, dusen = [], [], [], [], []

        def coz(v: str) -> None:
            # video başına hemen: döngünün ortasında düşen bir video öncekileri ertesi koşuda yeniden onartmasın
            # (altyazılar ikinci kez eklenirdi)
            db.execute("DELETE FROM planlanamayan WHERE video_id = ?", (v,))
            db.commit()

        for v, y in sorted(bekleyen.items()):
            if (st := durumlar.get(v)) is None:
                kayip.append(v)
                coz(v)  # kanalda yok: her koşu yeniden bakım koşusu açıp alarm yazmasın (bir kez söylenir)
            elif st.get("privacyStatus") == "private" and not st.get("publishAt"):
                try:
                    eksik_altyazi += _yeniden_yayinla(v, planli.get(v, y), uretim_klasoru(anahtar.get(v, "")), yt)
                except Exception as e:  # noqa: BLE001 — bir videonun kalıcı hatası (geçersiz başlık) öbürlerini durdurmasın
                    if durum.planlama_denemesi(db, v) >= PLAN_DENEME:
                        coz(v)
                        dusen.append(
                            f"`{v}`: {PLAN_DENEME} koşuda planlanamadı, denetimden çıktı (elle bak): " + _hata(e)
                        )
                    else:
                        dusen.append(f"`{v}`: {_hata(e)}")
                    continue
                onarilan.append(v)
                coz(v)
            else:
                coz(v)  # planlı ya da public: başka bir yoldan çözülmüş
        for v in yakin:
            if v in bekleyen:
                continue
            if (st := durumlar.get(v)) is None:
                kayip.append(v)
            elif st.get("privacyStatus") == "private" and not st.get("publishAt"):
                plansiz.append(v)
        kayit["pist"] = {"denetlenen": len(set(yakin) | set(bekleyen)), "onarilan": onarilan, "kayip": kayip,
                         "plansiz": plansiz}  # fmt: skip
        if dusen:
            alarmlar.append("**Plansız video yeniden yayına konamadı:**\n\n" + "\n".join(f"- {d}" for d in dusen))
        if onarilan:
            alarmlar.append(f"**Plansız kalmış video yeniden yayına kondu** (bilgi): {', '.join(onarilan)}")
        if eksik_altyazi:
            alarmlar.append("**Onarılan videoda altyazı yüklenemedi:** " + "; ".join(eksik_altyazi))
        if plansiz:
            alarmlar.append(
                f"**Planlı görünen video kanalda private ve plansız:** {', '.join(plansiz)}. Elle çekildiyse "
                '`python -m otomat.yayin.youtube geri <id> "<neden>"` ile kaydet (slot yeniden dolar).'
            )
        if kayip:
            alarmlar.append(f"**Planlı video kanalda yok** (silinmiş olabilir; slot boş kalır): {', '.join(kayip)}")
    except Exception as e:  # noqa: BLE001
        alarmlar.append("**Pist denetimi yapılamadı** (üretim sürdü):\n\n" + _hata(e))


PLAN_DENEME = 3  # planlaması düşmüş video bu kadar koşuda onarılamazsa denetimden çıkar (alarmla)
CEVIRI_ONARIM = 1  # koşu başına en çok bu kadar video denenir (Cloudflare çevirisi + 400 birim/dil)


def ceviri_onarimi(db, yt, kayit: dict, alarmlar: list[str]) -> None:
    """Çevirisi atlanmış (kota, bozuk çıktı) ve hâlâ planlı videonun eksik dillerini tamamlar: üretim klasörü bu ya da
    önceki koşuların artifact'ında durur; hazirla yalnız eksik dilleri çevirir, yeni diller YouTube'a eklenir. 10-15
    Earth videosu dört dilin dördü kotaya takılıp çevirisiz planlanmıştı ve hiçbir koşu tamamlamıyordu. Onarılan
    video `ceviri_onarim`'a yazılır: artifact'taki eski yerel.json yine "atlanan" dese de ikinci kez onarılmaz.
    Çeviri bu koşuda tutmasa da deneme sayılır (kota doluyken her koşu bütün videoları denemesin). Sıra yayın anına
    göre: en yakın yayın önce (eskiden bu koşunun, kotaya yeni takılmış videosu hakkı her koşuda alıyordu). Bakım
    koşusunda da çalışır (pist dolu günlerde onarım hiç yapılmıyordu)."""
    from otomat.hikaye import cf
    from otomat.yayin import youtube

    simdi = dt.datetime.now(dt.UTC)  # üretimden sonra çalışır: koşunun başındaki an 45 dk eskimiş olabilir
    yapilan = {v for (v,) in db.execute("SELECT video_id FROM ceviri_onarim")}
    planli = {
        a: (v, dt.datetime.fromisoformat(y).astimezone(dt.UTC))
        for a, v, y in db.execute(
            "SELECT anahtar, video_id, yayin_ani FROM secimler WHERE video_id IS NOT NULL"
            " AND video_id NOT IN (SELECT video_id FROM geri_cekilen)"
        )
        if v not in yapilan and dt.datetime.fromisoformat(y).astimezone(dt.UTC) > simdi + dt.timedelta(minutes=30)
    }
    adaylar = {}
    for yerel_yol in uretim_dosyalari("yerel.json"):  # aynı hikâyenin en yeni klasörü önce gelir
        try:
            yerel = json.loads(yerel_yol.read_text(encoding="utf-8"))
            anahtar = json.loads((yerel_yol.parent / "meta.json").read_text(encoding="utf-8"))["paket"]["anahtar"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if yerel.get("atlanan") and anahtar in planli and anahtar not in adaylar:
            adaylar[anahtar] = (*planli[anahtar], yerel_yol, yerel["atlanan"])
    onarilan = []
    neuron = cf.NEURON["toplam"]
    for video_id, _, yerel_yol, atlanan in sorted(adaylar.values(), key=lambda a: a[1])[:CEVIRI_ONARIM]:
        try:
            sonuc = hazirla(yerel_yol.parent)
            yeni = [d for d in atlanan if d in sonuc["yerel"]]
            if not yeni:
                continue
            youtube.yerellestir(video_id, sonuc["yerel"], yt=yt)
            # yerelleştirme yazıldı: altyazı düşse de bir daha çevrilmesin (yeniden çeviri kota yakar, yeniden altyazı
            # çift iz açar)
            db.execute("INSERT OR REPLACE INTO ceviri_onarim VALUES (?, ?)", (video_id, simdi.date().isoformat()))
            db.commit()
            dusen = []
            # altyazısız kartta (K-25) en.srt yazılmaz, çeviri srt'si de yok: her dil "yüklenemedi" alarmı çalardı
            for dil in yeni if (yerel_yol.parent / "en.srt").exists() else []:
                try:
                    srt = yerel_yol.parent / f"{dil}.srt"
                    youtube.altyazi_ekle(video_id, dil, srt.read_text(encoding="utf-8"), yt=yt)
                except Exception as e:  # noqa: BLE001
                    dusen.append(f"{dil}: {type(e).__name__}: {e}"[:200])
            if dusen:
                alarmlar.append(f"**Tamamlanan çeviride altyazı yüklenemedi** (`{video_id}`): " + "; ".join(dusen))
            onarilan.append({"video_id": video_id, "diller": yeni})
        except Exception as e:  # noqa: BLE001
            alarmlar.append(f"**Eksik çeviri tamamlanamadı** (`{video_id}`, üretim sürdü):\n\n" + _hata(e))
    if onarilan:
        kayit["ceviri_onarimi"] = onarilan
    if harcanan := round(cf.NEURON["toplam"] - neuron):
        kayit["onarim_neuron"] = kayit.get("onarim_neuron", 0) + harcanan  # raporun neuron toplamına girer


BUFFER_SINIR = 3000  # istek / 30 gün, anahtar başına; tüm kanallar paylaşır
BUFFER_ESIK = 2500


def buffer_istekleri(bugun: dt.date) -> int:
    """Son 30 günde tüm kanalların Buffer isteği (günlük raporlardan). Sınır aşılırsa Buffer yayını durur."""
    sinir = (bugun - dt.timedelta(days=29)).isoformat()
    toplam = 0
    for kimlik in kanal.hepsi():
        try:
            yol = kanal.yukle(kimlik).raporlar / "gunluk.jsonl"
            satirlar = yol.read_text(encoding="utf-8").splitlines() if yol.exists() else []
        except (OSError, ValueError):
            continue
        for s in satirlar:
            try:
                k = json.loads(s)
            except ValueError:
                continue
            if k.get("kosu", k.get("tarih", "")) >= sinir:
                toplam += k.get("buffer_istek", 0)
    return toplam


def son_kayit() -> dict | None:
    """Bu kanalın günlük raporundaki son satır (bu koşudan önceki)."""
    try:
        satirlar = RAPOR.read_text(encoding="utf-8").splitlines()
        return json.loads(satirlar[-1]) if satirlar else None
    except (OSError, ValueError):
        return None


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
    belirsiz = False
    if mod == "api":
        video_id = yayinla_api(dizin, yayin_ani)
    elif mod == "buffer":
        from otomat.yayin import buffer

        try:
            video_id = yayinla_buffer(dizin, yayin_ani, gun.isoformat(), alarmlar, db=db)
        except buffer.GonderiBelirsiz as e:
            belirsiz = True
            alarmlar.append(
                "**Buffer gönderisi açıldı ama sonucu okunamadı**: video kanala yine de yüklenmiş olabilir. Aynı video "
                "ikinci kez gönderilmesin diye hikâye harcandı. Buffer yüklediyse sonraki koşunun analitiği videoyu "
                "başlıkla bulur ve pist denetimi planlar; yüklemediyse slot yeni bir hikâyeyle dolar:\n\n" + _hata(e)
            )
        except Exception as e:  # noqa: BLE001
            alarmlar.append(
                "**Buffer yayını düştü** (gönderi açılmadı): sonraki koşu aynı videoyu kota harcamadan yeniden "
                "yayınlamayı dener:\n\n" + _hata(e)
            )
    if video_id is None and mod == "teslim":
        kayit["teslim"] = str(teslime_koy(dizin, gun, paket.anahtar).relative_to(KOK))
    # buffer/api'de kanala çıkamayan hikâye harcanmaz: sonraki koşunun hazır üretimi (artifact) aynı videoyu kota
    # harcamadan yeniden yayınlar (eskiden slot yeni bir hikâyeyle yeniden üretiliyordu); Plan B paketine de konmaz,
    # elle yüklenip otomatik de yayınlanırsa iki kez çıkardı. Gönderi belirsizse video kanalda olabilir: harcanır.
    if video_id is not None or mod == "teslim" or belirsiz:
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
        # atlanan dil raporda görünsün: 10-15 Earth videosu dört dilin dördü de kotaya takılıp sessizce çevirisiz çıktı
        **({"ceviri_atlanan": diller["atlanan"]} if diller["atlanan"] else {}),
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
    genel: dict = {"tarih": bugun.isoformat(), "mod": mod, "kosu_ani": simdi.isoformat(timespec="minutes")}
    kayitlar: list[dict] = []
    alarmlar: list[str] = []
    db = durum.baglan()
    durum.gecmisi_doldur(db, RAPOR)
    if durum.pist_dolu(db, simdi, mod):
        print(f"{bugun.isoformat()}: " + ("pist dolu" if pist else "bugün zaten üretildi") + "; üretim yok.")
        # yalnız bakım: bekleyen rapor, planlaması düşmüş video (yayın anı geçse de onarılır) ya da çevirisi eksik
        # planlı video; üretim kaydı (gunluk.jsonl) yazılmaz
        bakim = pist and durum.planlanamayan_var(db)
        ceviri = pist and HIKAYE and durum.ceviri_bekliyor(db, RAPOR, simdi)
        if rapor.bekleyen(bugun) is not None or bakim or ceviri:
            yt, ya = analitik_adimi(db, bugun, genel, alarmlar)
            if pist and yt is not None:
                pist_denetimi(db, yt, simdi, genel, alarmlar)
                if ceviri:
                    ceviri_onarimi(db, yt, genel, alarmlar)
            rapor_adimi(db, bugun, yt, ya, genel, alarmlar)
            alarm_yaz(bugun, alarmlar)
            print(json.dumps(genel, ensure_ascii=False, indent=1))
        return
    yt, ya = analitik_adimi(db, bugun, genel, alarmlar)
    if HIKAYE and yt is not None:
        marka_adimi(yt, genel, alarmlar)
    if pist and yt is not None:
        pist_denetimi(db, yt, simdi, genel, alarmlar)
    onceki = son_kayit()
    kota_doldu = False
    try:
        if pist and yt is None:
            # token düşmüşse üretme: Buffer videoyu private yükler, planlama düşer, slot dolu sayılır ve hikâye
            # harcanır.
            # YetkiHatasi burada alarm olur (çözüm adımlarıyla); başka bir analitik hatasında servis yine kurulur.
            from otomat.yayin import youtube

            youtube.servis()
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
                kota_doldu |= kota
                kayit.update(
                    durum="kota" if kota else "hata", hata=f"{'' if kota else type(e).__name__ + ': '}{e}"[:500]
                )
                if kota and HIKAYE:  # kotaya takılan üretimin harcadığı da raporun neuron toplamına girsin
                    from otomat.hikaye import cf

                    kayit["neuron"] = round(cf.NEURON["toplam"])
                if pist and gun > bugun + dt.timedelta(days=1):
                    # yarının videosu kanalda planlı: sonraki koşu bu slotu yeniden dener, alarm gerekmez (10-11'de
                    # 3. pist gününün hikâyeleri düştü, alarm çaldı, akşam koşusu slotu doldurdu). Ama üst üste iki
                    # koşu düşerse sistemik bir sorun havuzu sessizce yakıyor olabilir (her koşu 3 hikâye harcar).
                    if not kota and (onceki or {}).get("durum") == "hata" and "HikayeDustu" in onceki.get("hata", ""):
                        alarmlar.append(
                            "**Pistin uzak slotu üst üste iki koşuda düştü** (her koşu 3 hikâyeyi havuzdan "
                            "harcıyor; kalıcı bir kapı sorunu olabilir):\n\n" + f"{type(e).__name__}: {e}"[:800]
                        )
                    break
                raise
            if kayit["video_id"] is None:
                break  # kanala çıkmadı (Plan B): slot boş kalır, aynı slota ikinci video üretilmez
        # üretimden sonra: kota önce yeni videonun. Kota bu koşuda dolduysa boşuna istek atılmaz
        if HIKAYE and pist and yt is not None and not kota_doldu:
            ceviri_onarimi(db, yt, kayitlar[-1] if kayitlar else genel, alarmlar)
    except Exception as e:
        from otomat.yayin.youtube import YetkiHatasi

        son = kayitlar[-1] if kayitlar else genel
        if son.get("durum") != "kota":  # kota raporda ayrı sayılır (alarm yine yazılır: yarının slotu boş)
            son.update(durum="hata", hata=f"{type(e).__name__}: {e}"[:500])
        # token düşükse analitik adımı aynı çözümü zaten yazdı: ikinci kopya gürültü
        if not (isinstance(e, YetkiHatasi) and any(YETKI_COZUMU in a for a in alarmlar)):
            alarmlar.append("**Günün videosu üretilemedi:**\n\n" + _hata(e))
        raise
    finally:
        if mod == "buffer":
            from otomat.yayin import buffer

            (kayitlar[-1] if kayitlar else genel)["buffer_istek"] = buffer.ISTEK["sayi"]
            if (toplam := buffer_istekleri(bugun) + buffer.ISTEK["sayi"]) > BUFFER_ESIK:
                alarmlar.append(
                    f"**Buffer API sınırına yaklaşıldı:** son 30 günde {toplam} / {BUFFER_SINIR} istek (tüm kanallar). "
                    "Aşılırsa Buffer yayını durur (video kanala çıkmaz; pist tamponu biter, slot boş kalır)."
                )
        rapor_adimi(db, bugun, yt, ya, genel, alarmlar)
        alarm_yaz(bugun, alarmlar)
        if not kayitlar:
            # üretim döngüsü hiç girmedi (slot hesabı ile pist denetimi arasında saat döndü): satırın durumu olsun
            genel.setdefault("durum", "bos")
        RAPOR.parent.mkdir(parents=True, exist_ok=True)
        with open(RAPOR, "a", encoding="utf-8") as f:
            for k in kayitlar or [genel]:
                f.write(json.dumps(k, ensure_ascii=False) + "\n")
        print(json.dumps(kayitlar or [genel], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
