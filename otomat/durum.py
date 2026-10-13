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
-- Buffer yükledi ama planlama (videos.update) düştü: pist denetimi yalnız bunları yeniden planlar. Kanalda elle
-- private'a çekilmiş bir videoya dokunulmasın diye "plansız private" her videoya değil (10-13 denetimi).
CREATE TABLE IF NOT EXISTS planlanamayan (
    video_id TEXT PRIMARY KEY,
    yayin_ani TEXT NOT NULL,
    deneme INTEGER NOT NULL DEFAULT 0
);
-- Eksik çevirisi sonradan tamamlanan videolar (gunluk.ceviri_onarimi bir videoyu bir kez onarır).
CREATE TABLE IF NOT EXISTS ceviri_onarim (
    video_id TEXT PRIMARY KEY,
    tarih TEXT NOT NULL
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
    # göç: deneme sayacı 10-13 ikinci denetiminde eklendi (kalıcı hatalı video her koşuyu bakım koşusuna çeviriyordu)
    if "deneme" not in {r[1] for r in db.execute("PRAGMA table_info(planlanamayan)")}:
        db.execute("ALTER TABLE planlanamayan ADD COLUMN deneme INTEGER NOT NULL DEFAULT 0")
        db.commit()
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
    # geri çekilen video artık onarılacak bir plan değil
    db.executemany("DELETE FROM planlanamayan WHERE video_id = ?", [(v,) for v in video_idler])
    db.commit()


def planlanamayan_var(db: sqlite3.Connection) -> bool:
    return db.execute("SELECT 1 FROM planlanamayan LIMIT 1").fetchone() is not None


def planlanamadi(db: sqlite3.Connection, video_id: str, yayin_ani: dt.datetime | None) -> None:
    db.execute(
        "INSERT OR REPLACE INTO planlanamayan (video_id, yayin_ani) VALUES (?, ?)",
        (video_id, (yayin_ani or dt.datetime.now(dt.UTC)).isoformat()),
    )
    db.commit()


def planlama_denemesi(db: sqlite3.Connection, video_id: str) -> int:
    """Onarımı düşen videonun deneme sayısını bir artırır, yenisini döner."""
    db.execute("UPDATE planlanamayan SET deneme = deneme + 1 WHERE video_id = ?", (video_id,))
    db.commit()
    satir = db.execute("SELECT deneme FROM planlanamayan WHERE video_id = ?", (video_id,)).fetchone()
    return satir[0] if satir else 0


def jsonl_oku(yol: Path) -> list[dict]:
    """Günlük rapor satırları; bozuk satır atlanır. Yarım yazılmış tek satır (iş zaman aşımı) "iş var mı" adımını
    ve bütün koşuyu her seferinde düşürüyordu, dosya elle düzeltilene kadar."""
    if not yol.exists():
        return []
    satirlar = []
    for s in yol.read_text(encoding="utf-8").splitlines():
        try:
            if isinstance(k := json.loads(s), dict):
                satirlar.append(k)
        except ValueError:
            continue
    return satirlar


def ceviri_bekliyor(db: sqlite3.Connection, rapor: Path, simdi: dt.datetime) -> bool:
    """Çevirisi atlanmış (kota) ve hâlâ planlı, onarılmamış video var mı (gunluk.ceviri_onarimi). Pist dolu günlerde
    koşu ilk adımda bittiği için onarım hiç yapılmıyordu; video yayına çevirisiz çıkıyordu."""
    yapilan = {v for (v,) in db.execute("SELECT video_id FROM ceviri_onarim UNION SELECT video_id FROM geri_cekilen")}
    sinir = simdi + dt.timedelta(minutes=30)
    for k in jsonl_oku(rapor):
        # `ceviri_atlanan` 10-13'ten önce yazılmıyordu: o kayıtlarda boş `diller` dört dilin de atlandığını gösterir
        eksik = k.get("ceviri_atlanan") or ("diller" in k and not k["diller"])
        if not (eksik and k.get("video_id")) or k["video_id"] in yapilan:
            continue
        try:
            if dt.datetime.fromisoformat(k["yayin_ani"]).astimezone(dt.UTC) > sinir:
                return True
        except (KeyError, TypeError, ValueError):
            continue
    return False


def yayin_slotu(db: sqlite3.Connection, simdi: dt.datetime, saat: int | None = None) -> dt.datetime:
    """Günde tek yayın, kanalın yayın saatinde: en erken bir saat sonrası, kanalda videosu olmayan ilk gün. Video
    kimliği olmayan (Plan B / teslim) ve geri çekilen satırlar slot tutmaz. İlk boş gün aranır, son videonun ertesi
    günü değil: pistin ortasından geri çekilen videonun slotu (T+1 çekildi, T+2 planlı) kalıcı boş kalıyordu."""
    saat = kanal.aktif().yayin_saati_utc if saat is None else saat
    aday = simdi.replace(hour=saat, minute=0, second=0, microsecond=0)
    if aday < simdi + dt.timedelta(hours=1):
        aday += dt.timedelta(days=1)
    dolu = {
        dt.datetime.fromisoformat(y).astimezone(dt.UTC).date()
        for (y,) in db.execute(
            "SELECT yayin_ani FROM secimler WHERE video_id IS NOT NULL"
            " AND video_id NOT IN (SELECT video_id FROM geri_cekilen)"
        )
    }
    while aday.date() in dolu:
        aday += dt.timedelta(days=1)
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
    n = 0
    for k in jsonl_oku(rapor):
        if k.get("durum") != "tamam" or not all(a in k for a in ("anahtar", "hash", "kalip", "sablon", "baslik")):
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
    db = baglan()
    mod = os.environ.get("OTOMAT_YAYIN", "teslim")
    pist = mod in ("api", "buffer")
    is_yok = (
        pist_dolu(db, simdi, mod)
        and rapor.bekleyen(simdi.date()) is None
        and not (pist and planlanamayan_var(db))  # planlaması düşmüş video bakım bekliyor
        and not (pist and ceviri_bekliyor(db, kanal.aktif().raporlar / "gunluk.jsonl", simdi))
    )
    sys.exit(0 if is_yok else 1)
