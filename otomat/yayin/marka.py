"""Kanal kimliği (Faz 15): banner, filigran, açıklama (EN + 4 dil), anahtar kelime ve kanal düzeyinde made for kids
API ile uygulanır; adı beklemez, ad değişince çevirili adlar için bir kez daha.
Günlük koşu her gün `kontrol` eder (1 kota birimi; uygulama
günü ~100 birim + banner yüklemesi). Ad, @tanıtıcı ve profil resmi API ile değişmez, Scryne Studio'dan yapar.

Metinler `kanallar/<id>/marka.toml`'da. Elle: `OTOMAT_KANAL=earth uv run python -m otomat.yayin.marka`.
"""

import tomllib

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from otomat import kanal
from otomat.ayarlar import KOK

YEREL = {"es": "es_ES", "pt": "pt_BR", "de": "de_DE", "fr": "fr_FR"}  # önceki kanallardaki biçim


def ayarlar() -> dict | None:
    yol = KOK / "kanallar" / kanal.aktif().id / "marka.toml"
    if not yol.exists():
        return None
    with open(yol, "rb") as f:
        return tomllib.load(f)


def uygula(yt, kanal_ogesi: dict, m: dict) -> None:
    k = kanal.aktif()
    kimlik = kanal_ogesi["id"]
    banner = yt.channelBanners().insert(media_body=MediaFileUpload(str(KOK / m["banner"]), mimetype="image/png"))
    marka = kanal_ogesi["brandingSettings"]
    marka.setdefault("channel", {}).update(
        {"description": m["aciklama"]["en"], "keywords": m["anahtar"], "defaultLanguage": "en"}
    )
    marka.setdefault("image", {})["bannerExternalUrl"] = banner.execute()["url"]
    yt.channels().update(part="brandingSettings", body={"id": kimlik, "brandingSettings": marka}).execute()
    yerel_adi_yaz(yt, kanal_ogesi, m)
    yt.channels().update(part="status", body={"id": kimlik, "status": {"selfDeclaredMadeForKids": k.mfk}}).execute()
    if k.mfk:
        eski_videolari_ayir(yt)
    try:
        yt.watermarks().set(
            channelId=kimlik,
            body={
                "timing": {"type": "offsetFromStart", "offsetMs": 0},
                "position": {"type": "corner", "cornerPosition": "topRight"},
            },
            media_body=MediaFileUpload(str(KOK / m["filigran"]), mimetype="image/png"),
        ).execute()
    except HttpError:
        raise  # yetki ya da kota: kimlik "uygulandı" sayılmasın, alarm olsun
    except Exception:  # noqa: BLE001 — 10-06'da yanıt kütüphane hatasıyla okunamadı ama ayar uygulanmıştı
        pass


def yerel_adi_yaz(yt, kanal_ogesi: dict, m: dict) -> bool:
    """Çevirili kanal adı ve açıklamaları o anki adla. Ad değiştirme kilidinde 429 (Earth, 2026-10-09): False döner,
    kimliğin geri kalanı sürer, ad değişince kontrol farkı görüp yeniden dener."""
    ad = kanal_ogesi["snippet"]["title"]  # Scryne'ın Studio'da seçebildiği ad (`ad` ya da bir yedek)
    yerel = {"en_US": {"title": ad, "description": m["aciklama"]["en"]}}
    yerel |= {YEREL[d]: {"title": ad, "description": m["aciklama"][d]} for d in YEREL if d in m["aciklama"]}
    try:
        yt.channels().update(part="localizations", body={"id": kanal_ogesi["id"], "localizations": yerel}).execute()
        return True
    except HttpError as e:
        if e.resp.status != 429:
            raise
        return False


def eski_videolari_ayir(yt) -> list[str]:
    """Kanal düzeyi MFK var olan videolara da uygulanır (support.google.com/youtube/answer/9527654). Geri çekilen eski
    videolar çocuk içeriği değil (Orbit'in uzay videoları): video düzeyinde "çocuklara özel değil" ve private kalır;
    video ayarı kanalınkini ezer. Silmek yerine bu (geri alınabilir, docs/arastirma/09)."""
    from otomat import durum

    # yalnız format değişiminin veri videoları; kalite yüzünden geri çekilen masal çocuk içeriği kalır (10-12)
    sorgu = "SELECT video_id FROM geri_cekilen WHERE neden LIKE 'format değişimi%' ORDER BY video_id"
    idler = [v for (v,) in durum.baglan().execute(sorgu)]
    from otomat.yayin import youtube

    for vid in idler:
        # tam gövde: kısmi status embeddable/publicStatsViewable/license alanlarını varsayılana çekiyordu
        yt.videos().update(part="status", body=youtube.tam_durum(yt, vid, mfk=False)).execute()
    return idler


def kontrol(yt) -> str:
    """'tamam' | 'uygulandı' (+ ' (ad bekleniyor)') | 'profil yok'.

    Kimlik adı beklemez: Studio'daki ad 14 günde 2 değişiklik sınırına takıldı (2026-10-09, 12 gün), videolar eski adla
    çıkarken banner, açıklama ve MFK yeni içeriğe uysun. Çevirili kanal adı o anki adla yazılır; ad değişince fark
    görülür ve kimlik bir kez daha uygulanır."""
    m = ayarlar()
    if m is None:
        return "profil yok"
    k = kanal.aktif()
    oge = yt.channels().list(part="id,snippet,brandingSettings,status,localizations", mine=True).execute()["items"][0]
    ad = oge["snippet"]["title"]
    ek = "" if ad in k.yeni_adlar else " (ad bekleniyor)"
    kanal_ayari = oge["brandingSettings"].get("channel", {})
    yerel_ad = (oge.get("localizations") or {}).get("en_US", {}).get("title")
    if kanal_ayari.get("description") == m["aciklama"]["en"] and oge["status"].get("selfDeclaredMadeForKids") == k.mfk:
        if yerel_ad == ad:
            return "tamam" + ek
        # yalnız çevirili ad eskimiş: bütün kimliği (banner, 3 güncelleme, filigran ~250 birim) her koşuda yeniden
        # uygulamak yerine yalnız yerelleştirme (50 birim); ad kilidinde (429) her koşu tam kimliği yeniden yüklüyordu
        return ("yerel ad güncellendi" if yerel_adi_yaz(yt, oge, m) else "yerel ad kilitli") + ek
    uygula(yt, oge, m)
    return "uygulandı" + ek


def main() -> None:
    from otomat.yayin import youtube

    print(kanal.aktif().id, kontrol(youtube.servis()))


if __name__ == "__main__":
    main()
