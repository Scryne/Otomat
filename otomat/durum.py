"""Kalıcı durum (SQLite, repoda): üretilen paketler (tekrar engeli), seçim logu ve analitik ölçümleri."""

import datetime as dt
import json
import os
import sqlite3
from pathlib import Path

from otomat import kanal
from otomat.veri import OlguPaketi

VARSAYILAN = Path(os.environ.get("OTOMAT_DURUM", kanal.aktif().durum))
TEKRAR_GUN = 60

SEMA = """
CREATE TABLE IF NOT EXISTS uretilen (
    hash TEXT NOT NULL,
    kol TEXT NOT NULL,
    tur TEXT NOT NULL,
    anahtar TEXT NOT NULL,
    tarih TEXT NOT NULL,
    video_id TEXT,
    PRIMARY KEY (hash, tarih)
);
CREATE INDEX IF NOT EXISTS uretilen_anahtar ON uretilen (anahtar, tarih);
-- Günde bir video: seçimin kolu (konu) ve kanca kalıbı haydudun öğrendiği eksenlerdir; `gunluk` haydudun kaydı (JSON).
CREATE TABLE IF NOT EXISTS secimler (
    tarih TEXT PRIMARY KEY,
    anahtar TEXT NOT NULL,
    hash TEXT NOT NULL,
    konu TEXT NOT NULL,
    kalip TEXT NOT NULL,
    sablon TEXT NOT NULL,
    baslik TEXT NOT NULL,
    yayin_ani TEXT NOT NULL,
    video_id TEXT,
    gunluk TEXT
);
-- Kanaldan geri çekilen (private'a alınıp planı kaldırılan) videolar: yayın slotu ve analitik bunları yok sayar
-- (2026-10-08 format değişimi: eski veri videoları).
CREATE TABLE IF NOT EXISTS geri_cekilen (
    video_id TEXT PRIMARY KEY,
    tarih TEXT NOT NULL,
    neden TEXT NOT NULL
);
-- Ödül penceresi ölçümü: yayın günü + 2 gün (Analytics), bir kez yazılır.
CREATE TABLE IF NOT EXISTS olcumler (
    video_id TEXT PRIMARY KEY,
    yayin_gunu TEXT NOT NULL,
    olculdu TEXT NOT NULL,
    views INTEGER NOT NULL,
    engaged_views INTEGER NOT NULL,
    ort_izlenme_yuzde REAL NOT NULL,
    ort_izlenme_sn REAL NOT NULL,
    abone INTEGER NOT NULL
);
"""


def baglan(yol: Path = VARSAYILAN) -> sqlite3.Connection:
    yol.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(yol)
    db.executescript(SEMA)
    return db


def taze_mi(db: sqlite3.Connection, paket: OlguPaketi, bugun: dt.date, gun: int = TEKRAR_GUN) -> bool:
    """Aynı olgu (hash) ya da aynı açı (anahtar) son `gun` günde kullanılmadıysa True."""
    sinir = (bugun - dt.timedelta(days=gun)).isoformat()
    satir = db.execute(
        "SELECT 1 FROM uretilen WHERE (hash = ? OR anahtar = ?) AND tarih >= ? LIMIT 1",
        (paket.hash, paket.anahtar, sinir),
    ).fetchone()
    return satir is None


def kaydet(db: sqlite3.Connection, paket: OlguPaketi, bugun: dt.date, video_id: str | None = None) -> None:
    db.execute(
        "INSERT OR REPLACE INTO uretilen (hash, kol, tur, anahtar, tarih, video_id) VALUES (?, ?, ?, ?, ?, ?)",
        (paket.hash, paket.kol, paket.tur, paket.anahtar, bugun.isoformat(), video_id),
    )
    db.commit()


def geri_cek(db: sqlite3.Connection, video_idler: list[str], bugun: dt.date, neden: str) -> None:
    db.executemany(
        "INSERT OR REPLACE INTO geri_cekilen (video_id, tarih, neden) VALUES (?, ?, ?)",
        [(v, bugun.isoformat(), neden) for v in video_idler],
    )
    db.commit()


def bugun_secildi_mi(db: sqlite3.Connection, bugun: dt.date) -> bool:
    """Günde bir video: yedek cron ya da elle tetikleme aynı günü ikinci kez üretmesin."""
    return db.execute("SELECT 1 FROM secimler WHERE tarih = ?", (bugun.isoformat(),)).fetchone() is not None


def secim_kaydet(
    db: sqlite3.Connection,
    bugun: dt.date,
    paket: OlguPaketi,
    kalip: str,
    sablon: str,
    baslik: str,
    yayin_ani: dt.datetime,
    video_id: str | None,
    gunluk: dict | None,
) -> None:
    db.execute(
        "INSERT OR REPLACE INTO secimler VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            bugun.isoformat(),
            paket.anahtar,
            paket.hash,
            paket.kol,
            kalip,
            sablon,
            baslik,
            yayin_ani.isoformat(),
            video_id,
            json.dumps(gunluk, ensure_ascii=False) if gunluk else None,
        ),
    )
    db.commit()


def gecmisi_doldur(db: sqlite3.Connection, rapor: Path) -> int:
    """Faz 6 öncesi günlük koşuları (raporlar/gunluk.jsonl) seçim tablosuna taşır; elle yüklenen videolar eşleşsin."""
    if not rapor.exists():
        return 0
    n = 0
    for satir in rapor.read_text(encoding="utf-8").splitlines():
        k = json.loads(satir)
        if k.get("durum") != "tamam":
            continue
        kol = k["anahtar"].split(":")[0]
        n += db.execute(
            "INSERT OR IGNORE INTO secimler VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
            (
                k["tarih"],
                k["anahtar"],
                k["hash"],
                kol,
                k["kalip"],
                k["sablon"],
                k["baslik"],
                k["yayin_ani"],
                k.get("video_id"),
            ),
        ).rowcount
    db.commit()
    return n


if __name__ == "__main__":
    # Actions "Bugün üretildi mi" adımı (uv kurulmadan, sistem python3'üyle): kanalın bugünkü seçimi varsa 0.
    import sys

    sys.exit(0 if bugun_secildi_mi(baglan(), dt.datetime.now(dt.UTC).date()) else 1)
