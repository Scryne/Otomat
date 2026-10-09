"""Kanal kimliği (Faz 15): kanal Studio'da yeni adını alınca banner, filigran, açıklama (EN + 4 dil), anahtar kelime ve
kanal düzeyinde made for kids bir kez API ile uygulanır. Günlük koşu her gün `kontrol` eder (1 kota birimi; uygulama
günü ~100 birim + banner yüklemesi). Ad, @tanıtıcı ve profil resmi API ile değişmez, Scryne Studio'dan yapar.

Metinler `kanallar/<id>/marka.toml`'da. Elle: `OTOMAT_KANAL=earth uv run python -m otomat.yayin.marka`.
"""

import tomllib

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
    ad = kanal_ogesi["snippet"]["title"]  # Scryne'ın Studio'da seçebildiği ad (`ad` ya da bir yedek)
    yerel = {"en_US": {"title": ad, "description": m["aciklama"]["en"]}}
    yerel |= {YEREL[d]: {"title": ad, "description": m["aciklama"][d]} for d in YEREL if d in m["aciklama"]}
    yt.channels().update(part="localizations", body={"id": kimlik, "localizations": yerel}).execute()
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
    except Exception:  # noqa: BLE001 — 10-06'da yanıt kütüphane hatasıyla okunamadı ama ayar uygulanmıştı
        pass


def eski_videolari_ayir(yt) -> list[str]:
    """Kanal düzeyi MFK var olan videolara da uygulanır (support.google.com/youtube/answer/9527654). Geri çekilen eski
    videolar çocuk içeriği değil (Orbit'in uzay videoları): video düzeyinde "çocuklara özel değil" ve private kalır;
    video ayarı kanalınkini ezer. Silmek yerine bu (geri alınabilir, docs/arastirma/09)."""
    from otomat import durum

    idler = [v for (v,) in durum.baglan().execute("SELECT video_id FROM geri_cekilen ORDER BY video_id")]
    for vid in idler:
        govde = {"id": vid, "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False}}
        yt.videos().update(part="status", body=govde).execute()
    return idler


def kontrol(yt) -> str:
    """'ad bekleniyor' (Scryne henüz yeniden adlandırmadı) | 'tamam' | 'uygulandı' | 'profil yok'."""
    m = ayarlar()
    if m is None:
        return "profil yok"
    k = kanal.aktif()
    oge = yt.channels().list(part="id,snippet,brandingSettings,status", mine=True).execute()["items"][0]
    if oge["snippet"]["title"] not in k.yeni_adlar:
        return "ad bekleniyor"
    kanal_ayari = oge["brandingSettings"].get("channel", {})
    if kanal_ayari.get("description") == m["aciklama"]["en"] and oge["status"].get("selfDeclaredMadeForKids") == k.mfk:
        return "tamam"
    uygula(yt, oge, m)
    return "uygulandı"


def main() -> None:
    from otomat.yayin import youtube

    print(kanal.aktif().id, kontrol(youtube.servis()))


if __name__ == "__main__":
    main()
