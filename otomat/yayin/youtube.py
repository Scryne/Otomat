"""YouTube Data API v3: OAuth (masaüstü uygulaması), yükleme, planlama, yerelleştirme, altyazı.

Sırlar koda ve repoya girmez:
- Yerel: `sirlar/istemci.json` (Google Cloud OAuth istemcisi, tüm kanallar), kanal başına token dosyası
  (earth: `sirlar/token.json`; diğerleri `sirlar/token_<id>.json`, ilk yetkiden sonra yazılır).
- Actions: `YT_ISTEMCI_JSON` ve kanalın `YT_TOKEN_JSON<sir_eki>` ortam değişkeni (GitHub Secrets).

Not: Google'ın denetiminden (audit) geçmemiş projede yüklenen her video private'a kilitlenir (docs/arastirma/03).
`publishAt` yine yazılır; audit gelince aynı kod planlı public yayına geçer.
"""

import datetime as dt
import io
import json
import os
from pathlib import Path

from otomat import kanal
from otomat.ayarlar import KOK

KAPSAMLAR = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",  # altyazı ve yerelleştirme
    "https://www.googleapis.com/auth/yt-analytics.readonly",  # Faz 6 geri besleme
]
SIRLAR = KOK / "sirlar"
KATEGORI = kanal.aktif().kategori  # earth: 28 Science & Technology
# 5xx/429/bağlantı hatasında üstel bekleyerek yeniden dene (10-05 analitik adımı tek seferlik 500 ile düştü).
# Yalnız tekrarı zararsız çağrılarda: okumalar ve devam ettirilebilir yükleme; captions.insert çift iz açabilir.
DENEME = 4


class YetkiHatasi(RuntimeError):
    pass


def _istemci_bilgisi() -> dict:
    if ham := os.environ.get("YT_ISTEMCI_JSON"):
        return json.loads(ham)
    yol = SIRLAR / "istemci.json"
    if not yol.exists():
        raise YetkiHatasi("OAuth istemcisi yok: sirlar/istemci.json (rehber: docs/rehber/youtube-kurulum.md)")
    return json.loads(yol.read_text(encoding="utf-8"))


def kimlik():
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    k_ = kanal.aktif()
    if ham := os.environ.get(k_.token_degiskeni):
        bilgi = json.loads(ham)
    elif k_.token_dosyasi.exists():
        bilgi = json.loads(k_.token_dosyasi.read_text(encoding="utf-8"))
    else:
        raise YetkiHatasi("token yok: önce yerelde `python -m otomat.yayin.youtube yetki` çalıştır")
    k = Credentials.from_authorized_user_info(bilgi, KAPSAMLAR)
    if not k.valid:
        try:
            k.refresh(Request())
        except RefreshError as e:  # 'Testing' durumundaki uygulamada token 7 günde düşer (invalid_grant)
            raise YetkiHatasi(f"token yenilenemedi (invalid_grant?): {e}") from e
    return k


def yetki_al() -> Path:
    """Yerelde kanal başına bir kez (OTOMAT_KANAL): izin ekranında o kanal seçilir, refresh token kanalın dosyasına."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    akis = InstalledAppFlow.from_client_config(_istemci_bilgisi(), KAPSAMLAR)
    k = akis.run_local_server(port=0, prompt="consent", access_type="offline")
    SIRLAR.mkdir(exist_ok=True)
    yol = kanal.aktif().token_dosyasi  # kanal başına ayrı token, aynı OAuth istemcisi
    yol.write_text(k.to_json(), encoding="utf-8")
    return yol


def servis(k=None):
    from googleapiclient.discovery import build

    yt = build("youtube", "v3", credentials=k or kimlik(), cache_discovery=False)
    kanal_dogrula(yt)
    return yt


_DOGRULANDI: set[str] = set()
GERCEK_AD: dict[str, str] = {}  # kanal id → YouTube'daki şimdiki adı (marka.py yeniden adlandırmayı buradan görür)


def kanal_dogrula(yt) -> None:
    """Token gerçekten etkin kanala mı ait? Çok kanalda yanlış token, videoyu öbür kanalda düzenlemeye ve analitiği
    yanlış kanaldan okumaya götürür. Süreç başına bir kez (1 kota birimi)."""
    k = kanal.aktif()
    beklenen = k.ad
    if beklenen in _DOGRULANDI:
        return
    ogeler = yt.channels().list(part="snippet", mine=True).execute(num_retries=DENEME).get("items", [])
    ad = ogeler[0]["snippet"]["title"] if ogeler else None
    # eski ad: kanal Studio'da yeniden adlandırılana kadar (Faz 15) yükleme sürsün
    if ad not in (*k.yeni_adlar, *k.eski_adlar):
        raise YetkiHatasi(f"token '{ad}' kanalına ait, beklenen '{beklenen}' (OTOMAT_KANAL={k.id})")
    GERCEK_AD[k.id] = ad
    _DOGRULANDI.add(beklenen)


def _govde(
    baslik: str,
    aciklama: str,
    etiketler: list[str],
    yayin_ani: dt.datetime | None,
    yerellestirme: dict[str, dict] | None,
) -> tuple[dict, str]:
    govde = {
        "snippet": {
            "title": baslik[:100],
            "description": aciklama[:5000],
            "tags": etiketler[:15],
            "categoryId": KATEGORI,
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": "private",
            # çocuk kanalı (uzay, K-19): içerik çocuklara yönelikse işaret zorunlu, seçmeli değil
            "selfDeclaredMadeForKids": kanal.aktif().mfk,
            # gerçekçi değil: veri animasyonu ya da açıkça illüstrasyon (YouTube yardım 14328491)
            "containsSyntheticMedia": False,
        },
    }
    if yayin_ani:
        govde["status"]["publishAt"] = yayin_ani.astimezone(dt.UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    parcalar = "snippet,status"
    if yerellestirme:
        govde["localizations"] = {
            d: {"title": v["title"][:100], "description": v["description"][:5000]} for d, v in yerellestirme.items()
        }
        parcalar += ",localizations"
    return govde, parcalar


def yukle(
    video: Path,
    baslik: str,
    aciklama: str,
    etiketler: list[str],
    yayin_ani: dt.datetime | None,
    yerellestirme: dict[str, dict] | None = None,
    yt=None,
) -> str:
    from googleapiclient.http import MediaFileUpload

    yt = yt or servis()
    govde, parcalar = _govde(baslik, aciklama, etiketler, yayin_ani, yerellestirme)
    istek = yt.videos().insert(
        part=parcalar, body=govde, media_body=MediaFileUpload(str(video), mimetype="video/mp4", resumable=True)
    )
    yanit = None
    while yanit is None:
        _, yanit = istek.next_chunk(num_retries=DENEME)
    return yanit["id"]


def duzenle(
    video_id: str,
    baslik: str,
    aciklama: str,
    etiketler: list[str],
    yayin_ani: dt.datetime | None,
    yerellestirme: dict[str, dict] | None = None,
    yt=None,
) -> None:
    """Başka bir yoldan (Buffer) yüklenmiş videoya metadata, planlı yayın ve yerelleştirme yazar. Kilit yalnız bizim
    projemizin videos.insert'ünde; update serbest (docs/arastirma/06, 10-05 testi). yayin_ani yoksa hemen public."""
    yt = yt or servis()
    govde, parcalar = _govde(baslik, aciklama, etiketler, yayin_ani, yerellestirme)
    govde["id"] = video_id
    # status güncellemesi verilmeyen alanları varsayılana çeker (publicStatsViewable false oluyordu)
    govde["status"].update(embeddable=True, publicStatsViewable=True, license="youtube")
    if not yayin_ani:
        govde["status"]["privacyStatus"] = "public"
    yt.videos().update(part=parcalar, body=govde).execute(num_retries=DENEME)


def geri_cek(video_id: str, neden: str, yt=None) -> None:
    """Planlı ya da yayındaki videoyu private'a çeker (publishAt düşer), slotu boşaltır (`durum.geri_cekilen`).
    Silmez: geri alınabilir. Elle: `OTOMAT_KANAL=uzay uv run python -m otomat.yayin.youtube geri <id> "<neden>"`."""
    from otomat import durum

    yt = yt or servis()
    # MFK videonun kendi ayarından gelir, kanalınkinden değil: Orbit 10-13'te genel kitleye geçti, eski masal videoları
    # çocuk içeriği kalır; kanal ayarı yazılsaydı geri çekilen çocuk videosu "çocuklara özel değil" olurdu
    ogeler = yt.videos().list(part="status", id=video_id).execute(num_retries=DENEME).get("items", [])
    mfk = ogeler[0]["status"].get("selfDeclaredMadeForKids", ogeler[0]["status"].get("madeForKids")) if ogeler else None
    govde = {
        "id": video_id,
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": kanal.aktif().mfk if mfk is None else mfk,
            "containsSyntheticMedia": False,
            "embeddable": True,
            "publicStatsViewable": True,
            "license": "youtube",
        },
    }
    yt.videos().update(part="status", body=govde).execute(num_retries=DENEME)
    durum.geri_cek(durum.baglan(), [video_id], dt.datetime.now(dt.UTC).date(), neden)


def altyazi_ekle(video_id: str, dil: str, srt_metni: str, yt=None) -> None:
    from googleapiclient.http import MediaIoBaseUpload

    yt = yt or servis()
    yt.captions().insert(
        part="snippet",
        body={"snippet": {"videoId": video_id, "language": dil, "name": "", "isDraft": False}},
        media_body=MediaIoBaseUpload(io.BytesIO(srt_metni.encode("utf-8")), mimetype="application/octet-stream"),
    ).execute()


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    alt = p.add_subparsers(dest="komut", required=True)
    alt.add_parser("yetki", help="tarayıcıda izin ver, token'ı kanalın sirlar/ dosyasına yaz")
    alt.add_parser("kontrol", help="token geçerli mi, kanal adı ne")
    g = alt.add_parser("geri", help="videoyu private'a çek, slotunu boşalt")
    g.add_argument("video_id")
    g.add_argument("neden")
    a = p.parse_args()
    if a.komut == "yetki":
        print("token yazıldı:", yetki_al())
    elif a.komut == "geri":
        geri_cek(a.video_id, a.neden)
        print("geri çekildi:", a.video_id)
    else:
        kanal = (
            servis()
            .channels()
            .list(part="snippet", mine=True)
            .execute(num_retries=DENEME)["items"][0]["snippet"]["title"]
        )
        print("token geçerli, kanal:", kanal)


if __name__ == "__main__":
    main()
