"""Trend videosunu ve kesitlerini kendi kanalına yükler: videos.insert (private + publishAt) + thumbnails.set.

Kanal ayrı Google hesabında (K-38); token `sirlar/token_trend.json` (Actions'ta `YT_TOKEN_JSON_TREND`). Token başka
kanala aitse hiçbir şey yüklenmez (`kanal_dogrula`). Trend tazelik ister: uzun video işlenme payı kadar sonra
(varsayılan 45 dk) public olur; kesitler +3 sa, +1 gün, +2 gün. Shorts'tan uzun videoya bağlantı API'de yok
(support 14075157): açıklamaya "Full story" bağlantısı yazılır, Studio'daki "ilgili video" elle (haftalık dokunuş).

    uv run python -m otomat.trend.yukle yetki                 # bir kez: izin ekranında trend kanalı seçilir
    uv run python -m otomat.trend.yukle calisma/trend/<id>    # uzun video + kesitler
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

from otomat.yayin import youtube

KANAL_AD = "Why It's Everywhere"
TOKEN = youtube.SIRLAR / "token_trend.json"
TOKEN_DEGISKENI = "YT_TOKEN_JSON_TREND"
KATEGORI = "27"  # Education
ISLENME_PAYI = dt.timedelta(minutes=45)
KESIT_GECIKME = (dt.timedelta(hours=3), dt.timedelta(days=1), dt.timedelta(days=2))


class YuklemeHatasi(RuntimeError):
    pass


def yetki() -> Path:
    from google_auth_oauthlib.flow import InstalledAppFlow

    k = InstalledAppFlow.from_client_config(youtube._istemci_bilgisi(), youtube.KAPSAMLAR).run_local_server(
        port=0, prompt="consent", access_type="offline"
    )
    servis(k)
    youtube.SIRLAR.mkdir(exist_ok=True)
    TOKEN.write_text(k.to_json(), encoding="utf-8")
    return TOKEN


def kimlik():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if ham := os.environ.get(TOKEN_DEGISKENI):
        bilgi = json.loads(ham)
    elif TOKEN.exists():
        bilgi = json.loads(TOKEN.read_text(encoding="utf-8"))
    else:
        raise YuklemeHatasi("token yok: önce `python -m otomat.trend.yukle yetki`")
    k = Credentials.from_authorized_user_info(bilgi, youtube.KAPSAMLAR)
    if not k.valid:
        k.refresh(Request())
    return k


def servis(k=None):
    from googleapiclient.discovery import build

    yt = build("youtube", "v3", credentials=k or kimlik(), cache_discovery=False)
    ogeler = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
    ad = ogeler[0]["snippet"]["title"] if ogeler else None
    if ad != KANAL_AD:
        raise YuklemeHatasi(f"token '{ad}' kanalına ait, beklenen '{KANAL_AD}'")
    return yt


def _zaman(t: dt.datetime) -> str:
    return t.astimezone(dt.UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def govde(baslik: str, aciklama: str, etiketler: list[str], yayin: dt.datetime) -> dict:
    return {
        "snippet": {"title": youtube.temiz(baslik)[:100], "description": youtube.temiz(aciklama)[:5000],
                    "tags": etiketler[:15], "categoryId": KATEGORI, "defaultLanguage": "en",
                    "defaultAudioLanguage": "en"},
        "status": {"privacyStatus": "private", "publishAt": _zaman(yayin), "selfDeclaredMadeForKids": False,
                   # gerçek fotoğraflar + grafik; gerçekçi AI görüntü yok (support 14328491). Sentetik ses açıklamada.
                   "containsSyntheticMedia": False},
    }  # fmt: skip


def _gonder(yt, govde_: dict, video: Path) -> dict:
    from googleapiclient.http import MediaFileUpload

    istek = yt.videos().insert(part="snippet,status", body=govde_, media_body=MediaFileUpload(
        str(video), mimetype="video/mp4", resumable=True, chunksize=16 * 1024 * 1024))  # fmt: skip
    yanit = None
    while yanit is None:
        _, yanit = istek.next_chunk(num_retries=youtube.DENEME)
    return yanit


def etiketler(meta: dict, konu: str) -> list[str]:
    temel = [konu, f"{konu} explained", "explained", "trending", "why is everyone talking about"]
    return list(dict.fromkeys(t for t in temel if t))


def yukle(d: Path, simdi: dt.datetime | None = None, yt=None) -> dict:
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    secim = json.loads((d / "secim.json").read_text(encoding="utf-8"))["secim"]
    kayit_yol = d / "yukleme.json"
    kayit = json.loads(kayit_yol.read_text(encoding="utf-8")) if kayit_yol.exists() else {"kesitler": {}}
    simdi = simdi or dt.datetime.now(dt.UTC)
    yt = yt or servis()
    etk = etiketler(meta, secim["hikaye"])
    if "video_id" not in kayit:
        yayin = simdi + ISLENME_PAYI
        y = _gonder(yt, govde(meta["baslik"], meta["aciklama"], etk, yayin), d / "video.mp4")
        kayit.update(video_id=y["id"], yayin=_zaman(yayin), donen=y.get("status", {}).get("privacyStatus"))
        kayit_yol.write_text(json.dumps(kayit, indent=1), encoding="utf-8")
        try:
            from googleapiclient.http import MediaFileUpload

            kapak = MediaFileUpload(str(d / "kapak" / "kapak.jpg"), mimetype="image/jpeg")
            yt.thumbnails().set(videoId=y["id"], media_body=kapak).execute()
            kayit["kapak"] = "tamam"
        except Exception as e:  # noqa: BLE001 — doğrulanmamış kanal 403; video yine yüklendi
            kayit["kapak"] = youtube.kisa_hata(e)
        kayit_yol.write_text(json.dumps(kayit, indent=1), encoding="utf-8")
    ana = dt.datetime.fromisoformat(kayit["yayin"].replace("Z", "+00:00"))
    sen = json.loads((d / "senaryo.json").read_text(encoding="utf-8"))
    for i, k in enumerate(sen.get("kesitler") or []):
        video = d / f"kesit{i + 1}" / "kesit.mp4"
        if str(i) in kayit["kesitler"] or not video.exists() or i >= len(KESIT_GECIKME):
            continue
        yayin = max(ana + KESIT_GECIKME[i], simdi + ISLENME_PAYI)
        aciklama = (f"{k.get('baslik', '')}\n\nFull story: https://www.youtube.com/watch?v={kayit['video_id']}\n\n"
                    + meta["aciklama"][meta["aciklama"].find("Sources:"):])  # fmt: skip
        y = _gonder(yt, govde(k.get("baslik") or meta["baslik"], aciklama, etk + ["shorts"], yayin), video)
        kayit["kesitler"][str(i)] = {"video_id": y["id"], "yayin": _zaman(yayin)}
        kayit_yol.write_text(json.dumps(kayit, indent=1), encoding="utf-8")
    return kayit


def main() -> None:
    a = sys.argv[1:]
    if a == ["yetki"]:
        print("token:", yetki())
    elif a:
        print(json.dumps(yukle(Path(a[0])), indent=1, ensure_ascii=False))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
