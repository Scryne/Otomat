"""Analitik toplayıcı: kanaldaki videoları seçimlerle eşleştirir, ödül penceresini ölçer (YouTube Analytics API).

- Eşleştirme: API ile yüklenen videonun kimliği seçimde zaten yazılı. Plan B'de Scryne Studio'dan elle yükler; kanalın
  yükleme listesi okunur, başlık (büyük/küçük harf ve boşluk farkı yok sayılarak) seçimin başlığıyla eşlenir.
- Ölçüm: public video, yayın günü + 2 gün (3 gün) penceresinde; veri 48–72 sa geç geldiği için pencere bittikten 2 gün
  sonra bir kez okunur ve `olcumler`e yazılır. Haydut ödülü buradan hesaplar (haydut.py).
"""

import datetime as dt
import re
import sqlite3

from otomat.yayin.youtube import DENEME

PENCERE_GUN = 3  # ödül penceresi: yayın günü dahil 3 gün
GECIKME_GUN = 2  # Analytics gecikmesi
BOS_BEKLE_GUN = 7  # satırsız (boş) yanıt bu yaştan önce ölçüm sayılmaz
ESLESTIRME_GUN = 60  # bu kadar eski seçim artık eşleştirilmez
METRIKLER = "views,engagedViews,averageViewPercentage,averageViewDuration,subscribersGained"


def servisler():
    """(YouTube Data API, YouTube Analytics API); token düşmüşse youtube.YetkiHatasi."""
    from googleapiclient.discovery import build

    from otomat.yayin import youtube

    k = youtube.kimlik()
    return youtube.servis(k), build("youtubeAnalytics", "v2", credentials=k, cache_discovery=False)


def _norm(baslik: str) -> str:
    return re.sub(r"\s+", " ", baslik).strip().casefold()


def yuklemeler(yt, sayfa: int = 4) -> list[tuple[str, str]]:
    """Kanalın son yüklemeleri: (video_id, başlık), en yeni önce, en fazla 50 × sayfa."""
    kanal = yt.channels().list(part="contentDetails", mine=True).execute(num_retries=DENEME)["items"][0]
    liste = kanal["contentDetails"]["relatedPlaylists"]["uploads"]
    sonuc, belirtec = [], None
    for _ in range(sayfa):
        y = (
            yt.playlistItems()
            .list(part="snippet", playlistId=liste, maxResults=50, pageToken=belirtec)
            .execute(num_retries=DENEME)
        )
        sonuc += [(i["snippet"]["resourceId"]["videoId"], i["snippet"]["title"]) for i in y.get("items", [])]
        if not (belirtec := y.get("nextPageToken")):
            break
    return sonuc


def eslestir(db: sqlite3.Connection, yuklenen: list[tuple[str, str]], bugun: dt.date) -> list[tuple[str, str]]:
    """Video kimliği olmayan seçimlere başlıkla kimlik yazar; (tarih, video_id) listesi döner."""
    bilinen = {v for (v,) in db.execute("SELECT video_id FROM secimler WHERE video_id IS NOT NULL")}
    sinir = (bugun - dt.timedelta(days=ESLESTIRME_GUN)).isoformat()
    bekleyen = db.execute(
        "SELECT tarih, baslik FROM secimler WHERE video_id IS NULL AND tarih >= ? ORDER BY tarih", (sinir,)
    ).fetchall()
    eslesen = []
    for tarih, baslik in bekleyen:
        aday = [v for v, b in yuklenen if v not in bilinen and _norm(b) == _norm(baslik)]
        if aday:
            # aynı başlık iki kez yüklendiyse en eskisi (liste en yeni önce)
            db.execute("UPDATE secimler SET video_id = ? WHERE tarih = ?", (aday[-1], tarih))
            bilinen.add(aday[-1])
            eslesen.append((tarih, aday[-1]))
    db.commit()
    return eslesen


def durumlar(yt, video_idler: list[str]) -> dict[str, dict]:
    """video_id → {"public": bool, "yayin_gunu": date | None}."""
    sonuc = {}
    for i in range(0, len(video_idler), 50):
        y = yt.videos().list(part="status,snippet", id=",".join(video_idler[i : i + 50])).execute(num_retries=DENEME)
        for v in y.get("items", []):
            gun = v["snippet"].get("publishedAt", "")[:10]
            sonuc[v["id"]] = {
                "public": v["status"]["privacyStatus"] == "public",
                "yayin_gunu": dt.date.fromisoformat(gun) if gun else None,
            }
    return sonuc


def pencere(ya, video_id: str, yayin_gunu: dt.date) -> dict:
    y = (
        ya.reports()
        .query(
            ids="channel==MINE",
            startDate=yayin_gunu.isoformat(),
            endDate=(yayin_gunu + dt.timedelta(days=PENCERE_GUN - 1)).isoformat(),
            metrics=METRIKLER,
            filters=f"video=={video_id}",
        )
        .execute(num_retries=DENEME)
    )
    satir = (y.get("rows") or [[0, 0, 0, 0, 0]])[0]
    sonuc = dict(zip(["views", "engaged_views", "ort_izlenme_yuzde", "ort_izlenme_sn", "abone"], satir, strict=True))
    return {**sonuc, "bos": not y.get("rows")}


def olc(db: sqlite3.Connection, yt, ya, bugun: dt.date) -> list[str]:
    """Penceresi olgunlaşmış, henüz ölçülmemiş public videoları ölçer; ölçülen video kimlikleri döner."""
    bekleyen = [
        v
        for (v,) in db.execute(
            "SELECT s.video_id FROM secimler s LEFT JOIN olcumler o ON o.video_id = s.video_id "
            "WHERE s.video_id IS NOT NULL AND o.video_id IS NULL"
            " AND s.video_id NOT IN (SELECT video_id FROM geri_cekilen)"
        )
    ]
    olculen = []
    bilgi = durumlar(yt, bekleyen) if bekleyen else {}
    for vid in bekleyen:
        d = bilgi.get(vid)  # silinmiş video listede gelmez
        gun = d and d["yayin_gunu"]
        if not d or not d["public"] or gun is None or bugun < gun + dt.timedelta(days=PENCERE_GUN + GECIKME_GUN):
            continue
        m = pencere(ya, vid, gun)
        if m["bos"] and bugun < gun + dt.timedelta(days=BOS_BEKLE_GUN):
            # satırsız yanıt gecikme de olabilir, gerçek sıfır da: bir kez yazılan ölçüm düzelmediği için geçici boş
            # yanıt kalıcı sıfır ödül oluyordu; video bir hafta dolunca sıfır gerçek sayılır
            continue
        db.execute(
            "INSERT INTO olcumler VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (vid, gun.isoformat(), bugun.isoformat(), m["views"], m["engaged_views"], m["ort_izlenme_yuzde"],
             m["ort_izlenme_sn"], m["abone"]),
        )  # fmt: skip
        olculen.append(vid)
    db.commit()
    return olculen


def kanal(yt, ya, bas: dt.date, son: dt.date) -> dict:
    """Dönem toplamları ve güncel abone sayısı (haftalık rapor, öldürme kriteri)."""
    y = (
        ya.reports()
        .query(
            ids="channel==MINE",
            startDate=bas.isoformat(),
            endDate=son.isoformat(),
            metrics="views,engagedViews,subscribersGained,subscribersLost",
        )
        .execute(num_retries=DENEME)
    )
    views, engaged, kazanilan, kaybedilen = (y.get("rows") or [[0, 0, 0, 0]])[0]
    ist = yt.channels().list(part="statistics", mine=True).execute(num_retries=DENEME)["items"][0]["statistics"]
    return {
        "views": views,
        "engaged_views": engaged,
        "abone_net": kazanilan - kaybedilen,
        "abone_toplam": int(ist.get("subscriberCount", 0)),
        "video_sayisi": int(ist.get("videoCount", 0)),
    }


def topla(db: sqlite3.Connection, bugun: dt.date, yt, ya) -> dict:
    eslesen = eslestir(db, yuklemeler(yt), bugun)
    olculen = olc(db, yt, ya, bugun)
    return {"eslesen": eslesen, "olculen": olculen}
