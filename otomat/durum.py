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
# Pist (stok): buffer/api modunda kanalda bugünden sonraki PIST_GUN günün yayını da planlı durur. Kota, GitHub'ın
# geciktirdiği/atladığı cron ya da hakemden düşen bir hikâye o günün yayınını kaçırtmaz; açık slot oldukça üretilir
# (2026-10-09: 06:17 koşusu hiç başlamadı, elle tetiklenen koşu Cloudflare kotasına takıldı → o gün video yoktu).
PIST_GUN = 2

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


def yayin_slotu(db: sqlite3.Connection, simdi: dt.datetime, saat: int | None = None) -> dt.datetime:
    """Günde tek yayın, kanalın yayın saatinde: en erken bir saat sonrası, kanala yüklenmiş son videonun ertesi günü.
    Video kimliği olmayan (Plan B / teslim) ve geri çekilen satırlar slot tutmaz."""
    saat = kanal.aktif().yayin_saati_utc if saat is None else saat
    aday = simdi.replace(hour=saat, minute=0, second=0, microsecond=0)
    if aday < simdi + dt.timedelta(hours=1):
        aday += dt.timedelta(days=1)
    son = db.execute(
        "SELECT max(yayin_ani) FROM secimler WHERE video_id IS NOT NULL"
        " AND video_id NOT IN (SELECT video_id FROM geri_cekilen)"
    ).fetchone()[0]
    if son:
        ertesi = dt.datetime.fromisoformat(son).astimezone(dt.UTC) + dt.timedelta(days=1)
        aday = max(aday, ertesi.replace(hour=saat, minute=0, second=0, microsecond=0))
    return aday


def pist_dolu(db: sqlite3.Connection, simdi: dt.datetime, mod: str) -> bool:
    """Üretecek iş yok mu? buffer/api: sıradaki boş slot pistin ötesinde. teslim: bugün zaten üretildi (Scryne'ın
    haftalık elle yüklemesi için günde bir paket yeter)."""
    if mod not in ("api", "buffer"):
        return bugun_secildi_mi(db, simdi.date())
    return yayin_slotu(db, simdi).date() > simdi.date() + dt.timedelta(days=PIST_GUN)


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
    # Actions "Üretilecek iş var mı" adımı (uv kurulmadan, sistem python3'üyle): pist dolu ve bekleyen haftalık rapor
    # yoksa 0 (koşu atlanır).
    import sys

    from otomat import rapor

    simdi = dt.datetime.now(dt.UTC)
    is_yok = (
        pist_dolu(baglan(), simdi, os.environ.get("OTOMAT_YAYIN", "teslim")) and rapor.bekleyen(simdi.date()) is None
    )
    sys.exit(0 if is_yok else 1)
