"""YouTube Data API v3: OAuth (masaüstü uygulaması), yükleme, planlama, yerelleştirme, altyazı.

Sırlar koda ve repoya girmez:
- Yerel: `sirlar/istemci.json` (Google Cloud OAuth istemcisi), `sirlar/token.json` (ilk yetkiden sonra yazılır).
- Actions: `YT_ISTEMCI_JSON` ve `YT_TOKEN_JSON` ortam değişkenleri (GitHub Secrets).

Not: Google'ın denetiminden (audit) geçmemiş projede yüklenen her video private'a kilitlenir (docs/arastirma/03).
`publishAt` yine yazılır; audit gelince aynı kod planlı public yayına geçer.
"""

import datetime as dt
import io
import json
import os
from pathlib import Path

from otomat.ayarlar import KOK

KAPSAMLAR = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",  # altyazı ve yerelleştirme
    "https://www.googleapis.com/auth/yt-analytics.readonly",  # Faz 6 geri besleme
]
SIRLAR = KOK / "sirlar"
KATEGORI_BILIM = "28"  # Science & Technology
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

    if ham := os.environ.get("YT_TOKEN_JSON"):
        bilgi = json.loads(ham)
    elif (SIRLAR / "token.json").exists():
        bilgi = json.loads((SIRLAR / "token.json").read_text(encoding="utf-8"))
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
    """Yerelde bir kez: tarayıcıda izin verilir, refresh token sirlar/token.json'a yazılır."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    akis = InstalledAppFlow.from_client_config(_istemci_bilgisi(), KAPSAMLAR)
    k = akis.run_local_server(port=0, prompt="consent", access_type="offline")
    SIRLAR.mkdir(exist_ok=True)
    yol = SIRLAR / "token.json"
    yol.write_text(k.to_json(), encoding="utf-8")
    return yol


def servis(k=None):
    from googleapiclient.discovery import build

    return build("youtube", "v3", credentials=k or kimlik(), cache_discovery=False)


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
    govde = {
        "snippet": {
            "title": baslik[:100],
            "description": aciklama[:5000],
            "tags": etiketler[:15],
            "categoryId": KATEGORI_BILIM,
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": False,  # gerçekçi değil: veri animasyonu (YouTube yardım 14328491)
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
    istek = yt.videos().insert(
        part=parcalar, body=govde, media_body=MediaFileUpload(str(video), mimetype="video/mp4", resumable=True)
    )
    yanit = None
    while yanit is None:
        _, yanit = istek.next_chunk(num_retries=DENEME)
    return yanit["id"]


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
    alt.add_parser("yetki", help="tarayıcıda izin ver, token'ı sirlar/token.json'a yaz")
    alt.add_parser("kontrol", help="token geçerli mi, kanal adı ne")
    a = p.parse_args()
    if a.komut == "yetki":
        print("token yazıldı:", yetki_al())
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
