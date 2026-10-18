"""Bitmiş filmi One Ticket Back'e yükler (K-30, K-32): videos.insert + thumbnails.set, kayıt `yukleme.json`.

Shorts kanallarının profil/Buffer hattından ayrıdır: aynı OAuth istemcisi (`sirlar/istemci.json`), kanalın kendi token'ı
(`sirlar/token_film.json`). Token başka kanala aitse hiçbir şey yüklenmez.

    uv run python -m otomat.film.yukle yetki                                  # bir kez: izin ekranında One Ticket Back
    uv run python -m otomat.film.yukle filmler/<slug>/senaryo.json [unlisted|private|public]
    uv run python -m otomat.film.yukle durum filmler/<slug>/senaryo.json      # YouTube'daki gizlilik/işlenme durumu

Denetlenmemiş projede yüklenen video eskiden private'a kilitleniyordu (10-05 gözlemi); belge 2026-10-15'te tersini
söylüyor. İlk yükleme bunu ölçer: istenen görünürlük ile YouTube'un döndürdüğü `yukleme.json`'a yazılır.
"""

import datetime as dt
import json
import sys
from pathlib import Path

from otomat.film import senaryo, uretim
from otomat.yayin import youtube

KANAL_AD = "One Ticket Back"
TOKEN = youtube.SIRLAR / "token_film.json"
KATEGORI = "27"  # Education
GORUNURLUKLER = ("unlisted", "private", "public")
VARSAYILAN_ETIKET = ["history", "animated history", "what if", "your life as", "history documentary"]


class YuklemeHatasi(RuntimeError):
    pass


def yetki() -> Path:
    from google_auth_oauthlib.flow import InstalledAppFlow

    k = InstalledAppFlow.from_client_config(youtube._istemci_bilgisi(), youtube.KAPSAMLAR).run_local_server(
        port=0, prompt="consent", access_type="offline"
    )
    servis(k)  # yanlış kanal seçildiyse token yazılmaz
    youtube.SIRLAR.mkdir(exist_ok=True)
    TOKEN.write_text(k.to_json(), encoding="utf-8")
    return TOKEN


def kimlik():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not TOKEN.exists():
        raise YuklemeHatasi("token yok: önce `python -m otomat.film.yukle yetki`")
    k = Credentials.from_authorized_user_info(json.loads(TOKEN.read_text(encoding="utf-8")), youtube.KAPSAMLAR)
    if not k.valid:
        k.refresh(Request())
    return k


def kanal_dogrula(yt) -> None:
    ogeler = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
    ad = ogeler[0]["snippet"]["title"] if ogeler else None
    if ad != KANAL_AD:
        raise YuklemeHatasi(f"token '{ad}' kanalına ait, beklenen '{KANAL_AD}'")


def servis(k=None):
    from googleapiclient.discovery import build

    yt = build("youtube", "v3", credentials=k or kimlik(), cache_discovery=False)
    kanal_dogrula(yt)
    return yt


def govde(film: senaryo.Film, aciklama: str, gorunurluk: str) -> dict:
    if gorunurluk not in GORUNURLUKLER:
        raise YuklemeHatasi(f"bilinmeyen görünürlük '{gorunurluk}'")
    return {
        "snippet": {
            "title": youtube.temiz(film.baslik)[:100],
            "description": youtube.temiz(aciklama)[:5000],
            "tags": list(film.etiketler or VARSAYILAN_ETIKET),
            "categoryId": KATEGORI,
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": gorunurluk,
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": False,  # gerçekçi değil, tamamen animasyon (YouTube yardım 14328491)
        },
    }


def dosyalar(film: senaryo.Film) -> dict[str, Path]:
    d = uretim.dizin(film)
    yollar = {"video": d / "video.mp4", "aciklama": d / "aciklama.txt", "kapak": d / "kapak.jpg"}
    if eksik := [ad for ad, y in yollar.items() if not y.exists()]:
        raise YuklemeHatasi(f"{film.slug}: üretilmemiş dosya {eksik}")
    return {**yollar, "kayit": d / "yukleme.json"}


def yukle(film: senaryo.Film, gorunurluk: str = "unlisted", yt=None) -> dict:
    from googleapiclient.http import MediaFileUpload

    y = dosyalar(film)
    if y["kayit"].exists():
        raise YuklemeHatasi(f"{film.slug} zaten yüklendi: {y['kayit'].read_text(encoding='utf-8')}")
    yt = yt or servis()
    istek = yt.videos().insert(
        part="snippet,status",
        body=govde(film, y["aciklama"].read_text(encoding="utf-8"), gorunurluk),
        media_body=MediaFileUpload(str(y["video"]), mimetype="video/mp4", resumable=True, chunksize=16 * 1024 * 1024),
    )
    yanit = None
    while yanit is None:
        _, yanit = istek.next_chunk(num_retries=youtube.DENEME)
    kayit = {
        "video_id": yanit["id"],
        "istenen": gorunurluk,
        "donen": yanit.get("status", {}).get("privacyStatus"),
        "zaman": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
    }
    y["kayit"].write_text(json.dumps(kayit, indent=1), encoding="utf-8")  # kapak düşse de çift yükleme olmasın
    try:
        yt.thumbnails().set(videoId=yanit["id"], media_body=MediaFileUpload(str(y["kapak"]), mimetype="image/jpeg")
                            ).execute()  # fmt: skip
        kayit["kapak"] = "tamam"
    except Exception as e:  # telefonla doğrulanmamış kanal: 403; video yine yüklendi
        kayit["kapak"] = youtube.kisa_hata(e)
    y["kayit"].write_text(json.dumps(kayit, indent=1), encoding="utf-8")
    return kayit


def durum(film: senaryo.Film, yt=None) -> dict:
    kayit = json.loads(dosyalar(film)["kayit"].read_text(encoding="utf-8"))
    yt = yt or servis()
    ogeler = yt.videos().list(part="status,processingDetails", id=kayit["video_id"]).execute().get("items", [])
    if not ogeler:
        return {**kayit, "youtube": "bulunamadı"}
    return {**kayit, "youtube": ogeler[0]["status"], "islenme": ogeler[0].get("processingDetails", {})}


def main() -> None:
    a = sys.argv[1:]
    if a == ["yetki"]:
        print("token:", yetki())
    elif a and a[0] == "durum":
        print(json.dumps(durum(senaryo.oku(Path(a[1]))), indent=1, ensure_ascii=False))
    elif a:
        print(json.dumps(yukle(senaryo.oku(Path(a[0])), a[1] if len(a) > 1 else "unlisted"), indent=1))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
