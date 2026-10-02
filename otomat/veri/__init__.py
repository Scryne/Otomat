"""Veri katmanı: açık kaynaklardan olgu paketleri.

Olgu paketi bir videonun tek doğruluk kaynağıdır. Anlatımdaki her sayı ve özel ad buradan gelir (K-4);
LLM yalnız yer tutucu yazar. Paket, görsel şablonun ihtiyaç duyduğu ham veriyi ve kaynağın atfını da taşır.
"""

import hashlib
import json
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Olgu:
    deger: int | float | str
    anlam: str  # LLM'e giden İngilizce açıklama: bu yer tutucu neyi ifade ediyor
    birim: str = ""


@dataclass(frozen=True)
class Kaynak:
    ad: str  # videoda "Data: <ad>"
    url: str
    lisans: str
    cekildi: str  # ISO 8601, UTC


@dataclass
class OlguPaketi:
    kol: str  # usgs | dunya_bankasi | eurostat
    tur: str  # olgu tipi, ör. ulke_yillik, en_yuksek_10
    anahtar: str  # anlamsal kimlik; tekrar engeli bunu kullanır
    konu: str  # LLM'e konu ipucu (İngilizce)
    olgular: dict[str, Olgu]
    gorsel: dict  # {"sablon": ..., şablona özel veri}
    kaynak: Kaynak
    etiketler: list[str] = field(default_factory=list)

    @property
    def hash(self) -> str:
        ozet = {
            "kol": self.kol,
            "tur": self.tur,
            "anahtar": self.anahtar,
            "olgular": {k: v.deger for k, v in sorted(self.olgular.items())},
            "gorsel": self.gorsel,
        }
        return hashlib.sha256(json.dumps(ozet, sort_keys=True, default=str).encode()).hexdigest()[:16]

    def sozluk(self) -> dict:
        d = asdict(self)
        d["hash"] = self.hash
        return d
