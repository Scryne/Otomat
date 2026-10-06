"""Kanal profili: aynı motor, farklı kanal. Her kanal `kanallar/<id>/kanal.toml`'da tanımlıdır.

Motor kanaldan habersizdir; kanala bağlı her şey (veri kaynakları, görsel kimlik, ses, yayın saati, durum dosyaları,
YouTube token'ı, Buffer kanal adı, LLM'e verilen kanal tanımı) profilden okunur. Etkin kanal `OTOMAT_KANAL` ortam
değişkenidir (varsayılan `earth`); Actions her kanalı ayrı bir matris işinde koşar (gunluk.yml).

Yollar proje köküne göredir. Earth in Numbers çok kanal öncesi yollarını korur (durum/otomat.db, raporlar/,
DESIGN.md): taşıma yok, geçmiş ve analitik eşleşmesi bozulmaz.
"""

import os
import tomllib
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from otomat.ayarlar import KOK

KANALLAR = KOK / "kanallar"
VARSAYILAN = "earth"


@dataclass(frozen=True)
class Kanal:
    id: str
    ad: str  # YouTube'daki ve Buffer'daki kanal adı (Buffer kanalı bu adla bulunur)
    tanim: str  # LLM'e: kanalın ne anlattığı, kime (İngilizce, tek cümle)
    kaynaklar: tuple[str, ...]  # veri adaptörleri (otomat/veri/kaynaklar.py)
    veri: Path  # adaptör ayarları (gösterge listeleri vb.)
    tasarim: Path  # görsel kimlik: frontmatter token'ları
    durum: Path  # SQLite
    raporlar: Path  # gunluk.jsonl + haftalık raporlar
    ses: str  # Kokoro sesi
    yayin_saati_utc: int
    diller: tuple[str, ...]  # İngilizceye ek yerelleştirme dilleri
    kategori: str  # YouTube categoryId
    sir_eki: str  # YT_TOKEN_JSON<sir_eki>: kanalın kendi OAuth token'ı (aynı istemci)
    ornekler: str  # LLM'e kanca/başlık üslup örnekleri
    buffer_kanal_id: str = ""  # boşsa Buffer'da adla aranır
    yasak: tuple[str, ...] = ()  # kanala özel yasak ifade düzenli ifadeleri (politika kapısına eklenir)
    kaliplar: tuple[str, ...] = ("soru", "senin_ulken", "duygusal", "olcek")  # kanca kalıpları (anlatim)
    yedek_kancalar: dict | None = None  # kalıp → LLM kapıdan geçemezse kullanılacak kancalar

    @property
    def token_degiskeni(self) -> str:
        return f"YT_TOKEN_JSON{self.sir_eki}"

    @property
    def token_dosyasi(self) -> Path:
        return KOK / "sirlar" / ("token.json" if not self.sir_eki else f"token{self.sir_eki.lower()}.json")


def yukle(kimlik: str) -> Kanal:
    yol = KANALLAR / kimlik / "kanal.toml"
    if not yol.exists():
        raise ValueError(f"kanal profili yok: {yol.relative_to(KOK)}")
    with open(yol, "rb") as f:
        d = tomllib.load(f)
    if d["id"] != kimlik:
        raise ValueError(f"{yol.relative_to(KOK)}: id '{d['id']}' klasör adıyla aynı olmalı")
    return Kanal(
        id=d["id"],
        ad=d["ad"],
        tanim=d["tanim"],
        kaynaklar=tuple(d["kaynaklar"]),
        veri=KOK / d["veri"],
        tasarim=KOK / d["tasarim"],
        durum=KOK / d["durum"],
        raporlar=KOK / d["raporlar"],
        ses=d["ses"],
        yayin_saati_utc=int(d["yayin_saati_utc"]),
        diller=tuple(d["diller"]),
        kategori=str(d["kategori"]),
        sir_eki=d.get("sir_eki", ""),
        ornekler=d["ornekler"].strip(),
        buffer_kanal_id=d.get("buffer_kanal_id", ""),
        yasak=tuple(d.get("yasak", [])),
        kaliplar=tuple(d.get("kaliplar", Kanal.kaliplar)),
        yedek_kancalar=d.get("yedek_kancalar"),
    )


def hepsi() -> list[str]:
    return sorted(p.parent.name for p in KANALLAR.glob("*/kanal.toml"))


@cache
def _aktif(kimlik: str) -> Kanal:
    return yukle(kimlik)


def aktif() -> Kanal:
    return _aktif(os.environ.get("OTOMAT_KANAL", VARSAYILAN))
