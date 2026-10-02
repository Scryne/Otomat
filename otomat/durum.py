"""Kalıcı durum (SQLite, repoda). Şimdilik: üretilen paketler ve tekrar engeli."""

import datetime as dt
import sqlite3
from pathlib import Path

from otomat.ayarlar import KOK
from otomat.veri import OlguPaketi

VARSAYILAN = KOK / "durum" / "otomat.db"
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
