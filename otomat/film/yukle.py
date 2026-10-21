"""Bitmiş filmi One Ticket Back'e yükler (K-30, K-32): videos.insert + thumbnails.set, kayıt `yukleme.json`.

Shorts kanallarının profil/Buffer hattından ayrıdır: aynı OAuth istemcisi (`sirlar/istemci.json`), kanalın kendi token'ı
(`sirlar/token_film.json`). Token başka kanala aitse hiçbir şey yüklenmez.

    uv run python -m otomat.film.yukle yetki                                  # bir kez: izin ekranında One Ticket Back
    uv run python -m otomat.film.yukle filmler/<slug>/senaryo.json [plan|unlisted|private|public]  # varsayılan plan
    uv run python -m otomat.film.yukle planla filmler/<slug>/senaryo.json     # takvim dışı yüklenmişi slota koy
    uv run python -m otomat.film.yukle kesit filmler/<slug>/senaryo.json [sıra]  # Shorts kesitleri (film planlı olmalı)
    uv run python -m otomat.film.yukle durum filmler/<slug>/senaryo.json      # YouTube'daki gizlilik/işlenme durumu

Denetlenmemiş projede yüklenen video eskiden private'a kilitleniyordu (10-05 gözlemi); belge 2026-10-15'te tersini
söylüyor. İlk yükleme bunu ölçer: istenen görünürlük ile YouTube'un döndürdüğü `yukleme.json`'a yazılır.
"""

import datetime as dt
import json
import os
import sys
from pathlib import Path

from otomat.film import senaryo, uretim
from otomat.yayin import youtube

KANAL_AD = "One Ticket Back"
# K-34 takvim: haftada bir film, cumartesi 19:00 UTC (ABD doğu 15:00, TR 22:00); filmin kesitleri sonraki pazartesi,
# çarşamba, cuma aynı saatte (Scryne: "sürekli arka arkaya aynı gün video atmamamız lazım, haftada 1 video")
FILM_GUNU, SAAT_UTC = 5, 19
KESIT_GUNLERI = (2, 4, 6)
EN_ERKEN = dt.timedelta(hours=24)  # yükleme + işlenme + son bakış payı
TOKEN = youtube.SIRLAR / "token_film.json"
TOKEN_DEGISKENI = "YT_TOKEN_JSON_FILM"
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

    if ham := os.environ.get(TOKEN_DEGISKENI):  # Actions: haftalık film raporu (otomat/film/rapor.py)
        bilgi = json.loads(ham)
    elif TOKEN.exists():
        bilgi = json.loads(TOKEN.read_text(encoding="utf-8"))
    else:
        raise YuklemeHatasi("token yok: önce `python -m otomat.film.yukle yetki`")
    k = Credentials.from_authorized_user_info(bilgi, youtube.KAPSAMLAR)
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


def _zaman_yazi(t: dt.datetime) -> str:
    return t.astimezone(dt.UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def film_takvimi(kok: Path | None = None) -> list[dt.datetime]:
    """Planlanmış ya da yayınlanmış filmlerin yayın anları (calisma/film/*/yukleme.json)."""
    kok = kok or uretim.KOK / "calisma" / "film"
    anlar = []
    for yol in kok.glob("*/yukleme.json"):
        if yayin := json.loads(yol.read_text(encoding="utf-8")).get("yayin"):
            anlar.append(dt.datetime.fromisoformat(yayin.replace("Z", "+00:00")))
    return sorted(anlar)


def sonraki_film_slotu(simdi: dt.datetime, dolu: list[dt.datetime]) -> dt.datetime:
    """İlk uygun cumartesi 19:00 UTC: en az 24 saat sonra ve son filmden en az 7 gün sonra (haftada bir)."""
    t = simdi.astimezone(dt.UTC).replace(hour=SAAT_UTC, minute=0, second=0, microsecond=0)
    t += dt.timedelta(days=(FILM_GUNU - t.weekday()) % 7)
    while t < simdi + EN_ERKEN or any(abs(t - x) < dt.timedelta(days=7) for x in dolu):
        t += dt.timedelta(days=7)
    return t


def kesit_slotu(film_yayin: dt.datetime, sira: int) -> dt.datetime:
    if sira >= len(KESIT_GUNLERI):
        raise YuklemeHatasi(f"film başına en çok {len(KESIT_GUNLERI)} kesit (takvim)")
    return film_yayin + dt.timedelta(days=KESIT_GUNLERI[sira])


def yukle(film: senaryo.Film, gorunurluk: str = "plan", yt=None, simdi: dt.datetime | None = None) -> dict:
    """gorunurluk "plan": private yüklenir, takvimdeki sıradaki cumartesi kendiliğinden public olur."""
    from googleapiclient.http import MediaFileUpload

    y = dosyalar(film)
    if y["kayit"].exists():
        raise YuklemeHatasi(f"{film.slug} zaten yüklendi: {y['kayit'].read_text(encoding='utf-8')}")
    yayin = sonraki_film_slotu(simdi or dt.datetime.now(dt.UTC), film_takvimi()) if gorunurluk == "plan" else None
    g = govde(film, y["aciklama"].read_text(encoding="utf-8"), "private" if yayin else gorunurluk)
    if yayin:
        g["status"]["publishAt"] = _zaman_yazi(yayin)
    yt = yt or servis()
    istek = yt.videos().insert(
        part="snippet,status",
        body=g,
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
    if yayin:
        kayit["yayin"] = _zaman_yazi(yayin)
    y["kayit"].write_text(json.dumps(kayit, indent=1), encoding="utf-8")  # kapak düşse de çift yükleme olmasın
    try:
        yt.thumbnails().set(videoId=yanit["id"], media_body=MediaFileUpload(str(y["kapak"]), mimetype="image/jpeg")
                            ).execute()  # fmt: skip
        kayit["kapak"] = "tamam"
    except Exception as e:  # telefonla doğrulanmamış kanal: 403; video yine yüklendi
        kayit["kapak"] = youtube.kisa_hata(e)
    y["kayit"].write_text(json.dumps(kayit, indent=1), encoding="utf-8")
    return kayit


def planla(film: senaryo.Film, yt=None, simdi: dt.datetime | None = None) -> dict:
    """Takvim dışı yüklenmiş filmi (ör. unlisted deneme) sıradaki film slotuna planlar."""
    y = dosyalar(film)
    kayit = json.loads(y["kayit"].read_text(encoding="utf-8"))
    if kayit.get("yayin"):
        raise YuklemeHatasi(f"{film.slug} zaten planlı: {kayit['yayin']}")
    yayin = sonraki_film_slotu(simdi or dt.datetime.now(dt.UTC), film_takvimi())
    yt = yt or servis()
    # bütün status alanlarıyla: verilmeyen alan varsayılana döner (10-19'da Klondike gömülemez oldu)
    yt.videos().update(part="status", body=youtube.tam_durum(yt, kayit["video_id"], mfk=False, yayin_ani=yayin)
                       ).execute()  # fmt: skip
    kayit["yayin"] = _zaman_yazi(yayin)
    y["kayit"].write_text(json.dumps(kayit, indent=1), encoding="utf-8")
    return kayit


def kesit_govde(film: senaryo.Film, k: senaryo.Kesit, film_id: str, aciklama: str) -> dict:
    """Kesit açıklaması: filmin bağlantısı, kaynaklar, müzik atfı (bölüm zaman damgaları kesitte yanlış olur)."""
    kaynakca = aciklama[aciklama.index("Sources") :] if "Sources" in aciklama else ""
    g = govde(film, f"{k.baslik}\n\nFull film: https://www.youtube.com/watch?v={film_id}\n\n{kaynakca}", "private")
    g["snippet"]["title"] = youtube.temiz(k.baslik)[:100]
    return g


def yukle_kesit(film: senaryo.Film, sira: int, yt=None) -> dict:
    """Kesit filmden sonra yayına girer (açıklamasındaki bağlantı ancak o zaman açılır): film planlı olmalı."""
    from googleapiclient.http import MediaFileUpload

    y = dosyalar(film)
    if not y["kayit"].exists():
        raise YuklemeHatasi(f"{film.slug}: önce film yüklenmeli (kesit filme bağlanır)")
    fk = json.loads(y["kayit"].read_text(encoding="utf-8"))
    if not fk.get("yayin"):
        raise YuklemeHatasi(f"{film.slug}: film takvimde değil (planla)")
    video = y["video"].parent / "kesit" / f"{sira:02d}.mp4"
    kayit_yol = y["video"].parent / "kesit" / f"{sira:02d}.json"
    if not video.exists():
        raise YuklemeHatasi(f"kesit üretilmemiş: {video}")
    if kayit_yol.exists():
        raise YuklemeHatasi(f"kesit {sira} zaten yüklendi: {kayit_yol.read_text(encoding='utf-8')}")
    yayin = kesit_slotu(dt.datetime.fromisoformat(fk["yayin"].replace("Z", "+00:00")), sira)
    g = kesit_govde(film, film.kesitler[sira], fk["video_id"], y["aciklama"].read_text(encoding="utf-8"))
    g["status"]["publishAt"] = _zaman_yazi(yayin)
    yt = yt or servis()
    ortam = MediaFileUpload(str(video), mimetype="video/mp4", resumable=True)
    istek = yt.videos().insert(part="snippet,status", body=g, media_body=ortam)
    yanit = None
    while yanit is None:
        _, yanit = istek.next_chunk(num_retries=youtube.DENEME)
    kayit = {"video_id": yanit["id"], "yayin": _zaman_yazi(yayin), "film": fk["video_id"],
             "donen": yanit.get("status", {}).get("privacyStatus")}  # fmt: skip
    kayit_yol.write_text(json.dumps(kayit, indent=1), encoding="utf-8")
    return kayit


def eksik_kesitler(film: senaryo.Film) -> list[int]:
    """Kaydı olmayan kesitler: kanalın 24 saatte 10 video sınırı (10-19, `uploadLimitExceeded`) yarıda keserse."""
    d = uretim.dizin(film) / "kesit"
    return [i for i in range(len(film.kesitler)) if not (d / f"{i:02d}.json").exists()]


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
    elif a and a[0] == "planla":
        print(json.dumps(planla(senaryo.oku(Path(a[1]))), indent=1))
    elif a and a[0] == "kesit":
        film = senaryo.oku(Path(a[1]))
        for i in eksik_kesitler(film) if len(a) == 2 else [int(a[2])]:
            print(json.dumps(yukle_kesit(film, i), indent=1))
    elif a:
        print(json.dumps(yukle(senaryo.oku(Path(a[0])), a[1] if len(a) > 1 else "plan"), indent=1))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
