"""One Ticket Back haftalık raporu: raporlar/film/YYYY-HWW.md (+ .json, portföy raporu okur).

Film kanalı Shorts matrisinin dışında (K-32): günlük koşusu, `secimler` tablosu, haydudu yok. Rapor her şeyi YouTube'dan
okur; yükleme kayıtları (`calisma/film`) Actions'ta olmadığı için kesit, açıklamasındaki "Full film:" bağlantısıyla
filmine bağlanır, film de süresiyle (≥ 3 dk) ayrılır.

Ne ölçülür (biçim kararı için, Faz 17):
- Film başına ilk 7 gün (filmler aynı yaşta kıyaslansın): görüntüleme, izlenme saati, ortalama süre ve %, 30. saniyede
  kalan izleyici (girişin tutup tutmadığı), kazandırdığı abone; yanında yayından bu yana toplam görüntüleme.
- Kesitler: görüntüleme, engaged, izlenme %; filmlere gelen trafiğin kaynağı (önerilen, arama, Shorts bağlantısı…).
- YPP sayacı: public uzun videoların son 365 gündeki izlenme saati ve abone.
Gösterim ve gösterim tıklama oranı Analytics API'de yok: Studio'dan okunur (rapor bunu hatırlatır).

Günlük iş akışının `film` işi hafta bitiminden RAPOR_GECIKME_GUN sonra yazar. Elle (bitmemiş hafta da olur; uç bugüne
kırpılır): `uv run python -m otomat.film.rapor 2026-H43`. Token: Actions'ta `YT_TOKEN_JSON_FILM`, yerelde
`sirlar/token_film.json` (yukle.kimlik).
"""

import datetime as dt
import json
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]  # ayarlar'ı import etmez: denetim adımı uv'siz, düz python3 ile koşar
RAPORLAR = KOK / "raporlar" / "film"
ILK_HAFTA = (2026, 43)  # ilk film (Klondike) 2026-10-24'te public
GERIYE_HAFTA = 4
RAPOR_GECIKME_GUN = 3  # Analytics 48-72 sa geç dolar (otomat/rapor.py ile aynı gerekçe)
PENCERE_GUN = 7
FILM_EN_AZ_SN = 180  # Shorts 3 dakikaya kadar; kesitler 27-55 sn, filmler 7-11 dk
KALAN_SN = 30
YPP = {"saat": 4_000, "abone": 1_000}
FILM_BAGI = re.compile(r"Full film: https://www\.youtube\.com/watch\?v=([\w-]{11})")
TRAFIK = {
    "RELATED_VIDEO": "önerilen video",
    "SUBSCRIBER": "ana sayfa ve abonelik akışı",
    "YT_SEARCH": "YouTube araması",
    "YT_CHANNEL": "kanal sayfası",
    "SHORTS": "Shorts akışı",
    "SHORTS_CONTENT_LINKS": "Shorts'taki bağlantı",
    "END_SCREEN": "bitiş ekranı",
    "NOTIFICATION": "bildirim",
    "PLAYLIST": "oynatma listesi",
    "YT_PLAYLIST_PAGE": "oynatma listesi sayfası",
    "YT_OTHER_PAGE": "diğer YouTube sayfaları",
    "EXT_URL": "dış site",
    "NO_LINK_OTHER": "doğrudan / bilinmeyen",
    "HASHTAGS": "hashtag",
}


def hafta_araligi(yil: int, hafta: int) -> tuple[dt.date, dt.date]:
    bas = dt.date.fromisocalendar(yil, hafta, 1)
    return bas, bas + dt.timedelta(days=6)


def dosya(yil: int, hafta: int) -> Path:
    return RAPORLAR / f"{yil}-H{hafta:02d}.md"


def bekleyen(bugun: dt.date) -> tuple[int, int] | None:
    """Biten son GERIYE_HAFTA haftadan raporu olmayan ve Analytics'i dolmuş en eski hafta."""
    for geri in range(GERIYE_HAFTA, 0, -1):
        yil, hafta, _ = (bugun - dt.timedelta(days=7 * geri)).isocalendar()
        if (yil, hafta) < ILK_HAFTA or dosya(yil, hafta).exists():
            continue
        if bugun >= hafta_araligi(yil, hafta)[1] + dt.timedelta(days=RAPOR_GECIKME_GUN):
            return yil, hafta
    return None


def sure_sn(iso: str) -> int:
    """ISO 8601 süre (PT8M27S, PT1H2M) → saniye."""
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not m:
        raise ValueError(f"süre okunamadı: {iso}")
    g, s, d, sn = (int(x or 0) for x in m.groups())
    return ((g * 24 + s) * 60 + d) * 60 + sn


def bicim(baslik: str) -> str:
    """K-31 ikinci biçim ("What if you…", ikinci şahıs) mı, kişi/olay anlatısı (üçüncü şahıs) mı."""
    return "What if you" if baslik.casefold().startswith("what if you") else "anlatı"


def ayir(videolar: list[dict], son: dt.date) -> tuple[list[dict], list[dict]]:
    """Haftanın sonuna kadar public olmuş videoları (filmler, kesitler) diye ayırır; yayın sırasıyla."""
    filmler, kesitler = [], []
    for v in sorted(videolar, key=lambda v: v["snippet"]["publishedAt"]):
        yayin = dt.date.fromisoformat(v["snippet"]["publishedAt"][:10])
        if v["status"]["privacyStatus"] != "public" or yayin > son:
            continue
        oge = {"id": v["id"], "baslik": v["snippet"]["title"], "yayin": yayin.isoformat(),
               "sure": sure_sn(v["contentDetails"]["duration"])}  # fmt: skip
        if m := FILM_BAGI.search(v["snippet"].get("description", "")):
            kesitler.append({**oge, "film_id": m.group(1)})
        elif oge["sure"] >= FILM_EN_AZ_SN:
            filmler.append({**oge, "bicim": bicim(oge["baslik"])})
    return filmler, kesitler


def kalan_orani(egri: list[list[float]], sure: int, saniye: int = KALAN_SN) -> float | None:
    """Kitle elde tutma eğrisinden (elapsedVideoTimeRatio, audienceWatchRatio) `saniye`deki izleyici oranı."""
    if not egri or sure <= saniye:
        return None
    hedef = saniye / sure
    return min(egri, key=lambda n: abs(n[0] - hedef))[1]


def _sorgu(ya, bas: dt.date, son: dt.date, metrikler: str, **ek) -> list[list]:
    from otomat.yayin.youtube import DENEME

    y = ya.reports().query(ids="channel==MINE", startDate=bas.isoformat(), endDate=son.isoformat(), metrics=metrikler,
                           **ek).execute(num_retries=DENEME)  # fmt: skip
    return y.get("rows") or []


def _yuklemeler(yt) -> list[dict]:
    from otomat.yayin.youtube import DENEME

    kanal = yt.channels().list(part="contentDetails,statistics", mine=True).execute(num_retries=DENEME)["items"][0]
    liste = kanal["contentDetails"]["relatedPlaylists"]["uploads"]
    idler, belirtec = [], None
    while True:
        y = yt.playlistItems().list(part="contentDetails", playlistId=liste, maxResults=50, pageToken=belirtec
                                    ).execute(num_retries=DENEME)  # fmt: skip
        idler += [i["contentDetails"]["videoId"] for i in y.get("items", [])]
        if not (belirtec := y.get("nextPageToken")):
            break
    videolar = []
    for i in range(0, len(idler), 50):
        y = yt.videos().list(part="snippet,status,contentDetails", id=",".join(idler[i : i + 50])
                             ).execute(num_retries=DENEME)  # fmt: skip
        videolar += y.get("items", [])
    return kanal["statistics"], videolar


def topla(yt, ya, bas: dt.date, son: dt.date) -> dict:
    """Raporun bütün sayıları (YouTube Data + Analytics)."""
    istatistik, videolar = _yuklemeler(yt)
    filmler, kesitler = ayir(videolar, son)
    (views, dakika, kazanilan, kaybedilen), *_ = _sorgu(
        ya, bas, son, "views,estimatedMinutesWatched,subscribersGained,subscribersLost"
    ) or [[0, 0, 0, 0]]
    for f in filmler:
        yayin = dt.date.fromisoformat(f["yayin"])
        p_son = min(yayin + dt.timedelta(days=PENCERE_GUN - 1), son)
        satir = _sorgu(ya, yayin, p_son, "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,"
                       "subscribersGained", filters=f"video=={f['id']}")  # fmt: skip
        f_views, f_dk, ort_sn, ort_yuzde, abone = satir[0] if satir else [0, 0, 0, 0, 0]
        egri = _sorgu(ya, yayin, p_son, "audienceWatchRatio", dimensions="elapsedVideoTimeRatio",
                      filters=f"video=={f['id']}")  # fmt: skip
        toplam = _sorgu(ya, yayin, son, "views", filters=f"video=={f['id']}")
        f.update(pencere_gun=(p_son - yayin).days + 1, views=f_views, saat=f_dk / 60, ort_sn=ort_sn,
                 ort_yuzde=ort_yuzde, kalan_30=kalan_orani(egri, f["sure"]), abone=abone,
                 toplam_views=toplam[0][0] if toplam else 0)  # fmt: skip
    if kesitler:
        k_bas = min(dt.date.fromisoformat(k["yayin"]) for k in kesitler)
        idler = "video==" + ",".join(k["id"] for k in kesitler)
        satirlar = _sorgu(ya, k_bas, son, "views,engagedViews,averageViewPercentage", dimensions="video", filters=idler)
        olcum = {r[0]: r[1:] for r in satirlar}
        for k in kesitler:
            k["views"], k["engaged"], k["ort_yuzde"] = olcum.get(k["id"], [0, 0, 0])
    trafik, ypp_saat = [], 0.0
    if filmler:
        idler = "video==" + ",".join(f["id"] for f in filmler)
        trafik = _sorgu(ya, bas, son, "views", dimensions="insightTrafficSourceType", filters=idler, sort="-views")
        # YPP: son 365 günde public uzun videoların izlenme saati (kesitler Shorts, sayılmaz)
        ypp_saat = sum(r[0] for r in _sorgu(ya, son - dt.timedelta(days=364), son, "estimatedMinutesWatched",
                                             filters=idler)) / 60  # fmt: skip
    return {
        "hafta": {"views": views, "saat": dakika / 60, "abone_net": kazanilan - kaybedilen},
        "abone_toplam": int(istatistik.get("subscriberCount", 0)),
        "public_video": len(filmler) + len(kesitler),
        "ypp_saat": ypp_saat,
        "filmler": filmler,
        "kesitler": kesitler,
        "trafik": trafik,
    }


def _sayi(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


def _ondalik(n: float) -> str:
    return f"{n:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _oran(pay, payda) -> str:
    return f"%{100 * pay / payda:.0f}" if payda else "—"


def _dk_sn(sn: float) -> str:
    return f"{int(sn) // 60}:{int(sn) % 60:02d}"


def olustur(yil: int, hafta: int, s: dict) -> str:
    bas, son = hafta_araligi(yil, hafta)
    h = s["hafta"]
    m = [
        f"# One Ticket Back: {yil} / hafta {hafta} ({bas.isoformat()} – {son.isoformat()})",
        "",
        "## Kanal",
        "",
        f"Bu hafta {_sayi(h['views'])} görüntüleme, {_ondalik(h['saat'])} saat izlenme, abone net "
        f"{h['abone_net']:+d}. Kanalda {s['public_video']} public video, {_sayi(s['abone_toplam'])} abone.",
        "",
        f"YPP: uzun videoların son 365 günde izlenme saati {_ondalik(s['ypp_saat'])} / {_sayi(YPP['saat'])} · abone "
        f"{_sayi(s['abone_toplam'])} / {_sayi(YPP['abone'])} (2027-02-01'den sonraki başvurularda 8.000 saat).",
        "",
        f"## Filmler (ilk {PENCERE_GUN} gün)",
        "",
    ]
    if not s["filmler"]:
        m += ["Bu hafta sonuna kadar public film yok.", ""]
    else:
        m += [
            "| Film | Biçim | Yayın | Gün | Görüntüleme | İzlenme saati | Ort. süre | Ort. % | 30. sn'de kalan "
            "| Abone | Toplam görüntüleme |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for f in s["filmler"]:
            kalan = "—" if f["kalan_30"] is None else f"%{100 * f['kalan_30']:.0f}"
            m.append(
                f"| {f['baslik']} (`{f['id']}`) | {f['bicim']} | {f['yayin']} | {f['pencere_gun']}/{PENCERE_GUN} | "
                f"{_sayi(f['views'])} | {_ondalik(f['saat'])} | {_dk_sn(f['ort_sn'])} / {_dk_sn(f['sure'])} | "
                f"%{f['ort_yuzde']:.0f} | {kalan} | {f['abone']:+d} | {_sayi(f['toplam_views'])} |"
            )
        m += ["", f"Pencere {PENCERE_GUN} günü doldurmamış filmler henüz kıyaslanamaz (Gün sütunu).", ""]
    m += ["## Kesitler (yayından hafta sonuna)", ""]
    if not s["kesitler"]:
        m += ["Public kesit yok.", ""]
    else:
        ad = {f["id"]: f["baslik"] for f in s["filmler"]}
        m += ["| Kesit | Film | Yayın | Görüntüleme | Engaged | Kalan | İzlenme % |",
              "| --- | --- | --- | --- | --- | --- | --- |"]  # fmt: skip
        for k in s["kesitler"]:
            m.append(
                f"| {k['baslik']} (`{k['id']}`) | {ad.get(k['film_id'], k['film_id'])} | {k['yayin']} | "
                f"{_sayi(k['views'])} | {_sayi(k['engaged'])} | {_oran(k['engaged'], k['views'])} | "
                f"%{k['ort_yuzde']:.0f} |"
            )
        m.append("")
    if s["trafik"]:
        toplam = sum(r[1] for r in s["trafik"])
        m += ["## Filmlere trafik (bu hafta)", ""]
        m += [f"- {TRAFIK.get(t, t)}: {_sayi(n)} ({_oran(n, toplam)})" for t, n in s["trafik"] if n]
        m.append("")
    m += [
        "## Studio'dan okunacak",
        "",
        "Gösterim ve gösterim tıklama oranı Analytics API'de yok: Studio → Analytics → İçerik → film → Erişim. "
        "Düşük tıklama oranı kapak ve başlığı, düşük 30. sn kalanı girişi gösterir.",
    ]
    return "\n".join(m) + "\n"


def yaz(yil: int, hafta: int, yt=None, ya=None, bugun: dt.date | None = None) -> Path:
    from googleapiclient.discovery import build

    from otomat.film import yukle

    bas, son = hafta_araligi(yil, hafta)
    son = min(son, (bugun or dt.datetime.now(dt.UTC).date()))  # elle, bitmemiş hafta
    if yt is None or ya is None:
        k = yukle.kimlik()
        yt = yt or yukle.servis(k)  # token başka kanala aitse burada düşer
        ya = ya or build("youtubeAnalytics", "v2", credentials=k, cache_discovery=False)
    sayilar = topla(yt, ya, bas, son)
    yol = dosya(yil, hafta)
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(olustur(yil, hafta, sayilar), encoding="utf-8")
    yol.with_suffix(".json").write_text(json.dumps({**sayilar, "son": son.isoformat()}, ensure_ascii=False, indent=1),
                                        encoding="utf-8")  # fmt: skip
    return yol


def main() -> None:
    a = sys.argv[1:]
    if a == ["bekleyen"]:  # iş akışının denetim adımı: yazılacak hafta yoksa 1 ile çıkar
        b = bekleyen(dt.datetime.now(dt.UTC).date())
        if b is None:
            raise SystemExit(1)
        print(f"{b[0]}-H{b[1]:02d}")
        return
    if a:
        yil, hafta = (int(x) for x in a[0].split("-H"))
    elif (b := bekleyen(dt.datetime.now(dt.UTC).date())) is not None:
        yil, hafta = b
    else:
        print("film raporu: yazılacak hafta yok")
        return
    print(yaz(yil, hafta).relative_to(KOK))


if __name__ == "__main__":
    main()
