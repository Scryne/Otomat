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
SLOT_GUNLERI = (0, 2, 5)  # K-49 (araştırma 15): Pazartesi, Çarşamba, Cumartesi
SLOT_SAAT = dt.time(21, 50)  # UTC; resmi kaynak saati önemsiz sayıyor, sabit olsun yeter


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


def siradaki_slot(simdi: dt.datetime, dolu: set[str]) -> dt.datetime:
    """K-49: uzun video haftada 3 (Pzt/Çar/Cmt) 21:50 UTC, günde en çok bir. `simdi + ISLENME_PAYI`'ndan sonraki,
    `dolu` (YYYY-MM-DD) olmayan ilk yayın günü."""
    gun = simdi.astimezone(dt.UTC).date()
    for i in range(0, 60):
        aday_gun = gun + dt.timedelta(days=i)
        aday = dt.datetime.combine(aday_gun, SLOT_SAAT, tzinfo=dt.UTC)
        if aday_gun.weekday() in SLOT_GUNLERI and aday >= simdi + ISLENME_PAYI and aday_gun.isoformat() not in dolu:
            return aday
    raise YuklemeHatasi("60 gün içinde boş yayın günü yok")


def dolu_gunler(haric: Path | None = None) -> set[str]:
    """Zamanlanmış ya da yayınlanmış uzun videoların günleri (her iş klasörünün yukleme.json'undan)."""
    kok = Path(__file__).resolve().parents[2] / "calisma" / "trend"
    gunler = set()
    for y in kok.glob("*/yukleme.json"):
        if haric is not None and y.parent.resolve() == haric.resolve():
            continue
        k = json.loads(y.read_text(encoding="utf-8"))
        if k.get("yayin"):
            gunler.add(k["yayin"][:10])
    return gunler


def _zamanla(yt, video_id: str, t: dt.datetime) -> None:
    yt.videos().update(part="status", body={"id": video_id, "status": {
        "privacyStatus": "private", "publishAt": _zaman(t), "selfDeclaredMadeForKids": False,
        "containsSyntheticMedia": False}}).execute()  # fmt: skip


def yukle(d: Path, simdi: dt.datetime | None = None, yt=None) -> dict:
    """Uzun video + kesitleri private yükler; kapak yüklenmeden hiçbir şey zamanlanmaz (11-27: Marka Hesabı kanalında
    telefon doğrulaması yokken kapak 403 verdi, video kapaksız yayına çıkacaktı). Kapak tamamsa uzun video sıradaki boş
    yayın gününe, kesitler ondan +3 sa, +1 gün, +2 gün sonraya zamanlanır. Yarım kalan iş sonraki koşuda tamamlanır."""
    from googleapiclient.http import MediaFileUpload

    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    secim = json.loads((d / "secim.json").read_text(encoding="utf-8"))["secim"]
    kayit_yol = d / "yukleme.json"
    kayit = json.loads(kayit_yol.read_text(encoding="utf-8")) if kayit_yol.exists() else {"kesitler": {}}

    def yaz() -> None:
        kayit_yol.write_text(json.dumps(kayit, indent=1), encoding="utf-8")

    simdi = simdi or dt.datetime.now(dt.UTC)
    yt = yt or servis()
    etk = etiketler(meta, secim["hikaye"])
    if "video_id" not in kayit:
        g = govde(meta["baslik"], meta["aciklama"], etk, simdi)
        g["status"].pop("publishAt")  # kapak yüklenene kadar zamansız private
        y = _gonder(yt, g, d / "video.mp4")
        kayit.update(video_id=y["id"], donen=y.get("status", {}).get("privacyStatus"))
        yaz()
    if kayit.get("kapak") != "tamam":
        try:
            kapak = MediaFileUpload(str(d / "kapak" / "kapak.jpg"), mimetype="image/jpeg")
            yt.thumbnails().set(videoId=kayit["video_id"], media_body=kapak).execute()
            kayit["kapak"] = "tamam"
        except Exception as e:  # noqa: BLE001 — kapak izni yok (telefon doğrulaması): video private bekler
            kayit["kapak"] = youtube.kisa_hata(e)
        yaz()
    if kayit.get("kapak") != "tamam":
        kayit["durum"] = "kapak bekliyor: kanal telefon doğrulaması (youtube.com/verify), sonra `yukle son`"
        yaz()
        return kayit
    if not kayit.get("yayin"):
        t = siradaki_slot(simdi, dolu_gunler(haric=d))
        _zamanla(yt, kayit["video_id"], t)
        kayit["yayin"] = _zaman(t)
        yaz()
    kayit.pop("durum", None)
    ana = dt.datetime.fromisoformat(kayit["yayin"].replace("Z", "+00:00"))
    sen = json.loads((d / "senaryo.json").read_text(encoding="utf-8"))
    for i, k in enumerate(sen.get("kesitler") or []):
        video = d / f"kesit{i + 1}" / "kesit.mp4"
        if i >= len(KESIT_GECIKME) or not video.exists():
            continue
        ks = kayit["kesitler"].get(str(i)) or {}
        yayin = max(ana + KESIT_GECIKME[i], simdi + ISLENME_PAYI)
        if "video_id" not in ks:
            aciklama = (f"{k.get('baslik', '')}\n\nFull story: https://www.youtube.com/watch?v={kayit['video_id']}\n\n"
                        + meta["aciklama"][meta["aciklama"].find("Sources:"):])  # fmt: skip
            y = _gonder(yt, govde(k.get("baslik") or meta["baslik"], aciklama, etk + ["shorts"], yayin), video)
            ks = {"video_id": y["id"], "yayin": _zaman(yayin)}
        elif not ks.get("yayin") or dt.datetime.fromisoformat(ks["yayin"].replace("Z", "+00:00")) < ana:
            _zamanla(yt, ks["video_id"], yayin)  # ana video ertelendiyse kesit ondan önce çıkmasın
            ks["yayin"] = _zaman(yayin)
        kayit["kesitler"][str(i)] = ks
        yaz()
    return kayit


TAZE = dt.timedelta(hours=48)  # trend videosu bundan eskiyse günlük koşu onu yüklemez


def yuklenebilir(kok: Path, simdi: dt.datetime | None = None) -> list[Path]:
    """`yukle son`un adayları: video.mp4'ü olan, `yuklenmez` işareti taşımayan, videosu TAZE içinde üretilmiş işler
    (ada göre sıralı). 11-27: üretim düşerse en yeni klasör bir A/B denemesi ya da kanaldan silinmiş eski bir video
    olabiliyordu; günlük koşu onu yükleyecekti. Zaten yüklenmiş iş (yukleme.json'da video_id) tazelikten bağımsızdır."""
    simdi = simdi or dt.datetime.now(dt.UTC)
    out = []
    for d in sorted(kok.glob("*/")):
        v = d / "video.mp4"
        if not v.exists() or (d / "yuklenmez").exists():
            continue
        yuklu = (d / "yukleme.json").exists()
        if yuklu or simdi - dt.datetime.fromtimestamp(v.stat().st_mtime, dt.UTC) <= TAZE:
            out.append(d)
    return out


def bekleyenler() -> list[Path]:
    """Yüklenmiş ama zamanlanmamış (kapak bekleyen) işler, eskiden yeniye."""
    kok = Path(__file__).resolve().parents[2] / "calisma" / "trend"
    out = []
    for y in sorted(kok.glob("*/yukleme.json")):
        k = json.loads(y.read_text(encoding="utf-8"))
        if k.get("video_id") and not k.get("yayin"):
            out.append(y.parent)
    return out


def kimlik_uygula(yt=None) -> dict:
    """Kanal kimliği: banner + açıklama + anahtar kelimeler (`kanallar/trend/marka.toml`). Ad, @tanıtıcı ve profil
    resmi API ile değişmez (Scryne Studio'dan yaptı, 11-27)."""
    import tomllib

    from googleapiclient.http import MediaFileUpload

    from otomat.ayarlar import KOK

    with open(KOK / "kanallar" / "trend" / "marka.toml", "rb") as f:
        m = tomllib.load(f)
    yt = yt or servis()
    oge = yt.channels().list(part="id,brandingSettings", mine=True).execute()["items"][0]
    banner = yt.channelBanners().insert(media_body=MediaFileUpload(str(KOK / m["banner"]), mimetype="image/png"))
    marka = oge["brandingSettings"]
    marka.setdefault("channel", {}).update({"description": m["aciklama"]["en"], "keywords": m["anahtar"],
                                           "defaultLanguage": "en", "country": "US"})  # fmt: skip
    marka.setdefault("image", {})["bannerExternalUrl"] = banner.execute()["url"]
    yt.channels().update(part="brandingSettings", body={"id": oge["id"], "brandingSettings": marka}).execute()
    return {"kanal": oge["id"], "banner": marka["image"]["bannerExternalUrl"][:60]}


def main() -> None:
    a = sys.argv[1:]
    if a == ["yetki"]:
        print("token:", yetki())
    elif a == ["kimlik"]:
        print(kimlik_uygula())
    elif a == ["son"]:  # günlük koşu: video.mp4'ü olan en yeni iş (kesitleri eksikse onları tamamlar)
        kok = Path(__file__).resolve().parents[2] / "calisma" / "trend"
        isler = yuklenebilir(kok)
        if not isler:
            print("yüklenecek video yok")
            return
        if not TOKEN.exists() and not os.environ.get(TOKEN_DEGISKENI):
            print("trend kanalının token'ı yok: yükleme atlandı (kanal açılınca `yukle yetki`)")
            return
        # trend tazelik ister: en yeni iş ilk boş yayın gününü alır, kapak bekleyen eskiler sonrakileri
        print(json.dumps({"is": isler[-1].name, **yukle(isler[-1])}, indent=1, ensure_ascii=False))
        for b in reversed(bekleyenler()):
            if b != isler[-1]:
                print(json.dumps({"is": b.name, **yukle(b)}, indent=1, ensure_ascii=False))
    elif a:
        print(json.dumps(yukle(Path(a[0])), indent=1, ensure_ascii=False))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
