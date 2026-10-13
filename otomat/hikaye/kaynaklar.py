"""Hikâye kaynakları: repodaki havuz anlık görüntüsünden `OlguPaketi` listesi.

- `tuhaf` (Earth → hikâye kanalı): Wikipedia:Unusual articles alt sayfalarındaki makaleler + editörün tek satırlık
  tanımı. Makale metni üretim anında Wikipedia API'den çekilir (CC BY-SA 4.0, açıklamada atıf).
- `ezop` (Orbit → masal kanalı, genel kitle; K-24): Aesop's Fables, V. S. Vernon Jones çevirisi (1912), Project
  Gutenberg #11339, kamu malı. Metin havuzda.

Havuzlar bir kez çıkarılıp TypeSafe (jev-1.13.0) ile süzüldü (K-18, docs/arastirma/08). Puanlar havuzda durur,
eşikler burada: anlam kararı modelde, kural kodda.
"""

import datetime as dt
import http.client
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from otomat import kanal
from otomat.veri import Kaynak, OlguPaketi

UA = {"User-Agent": "Otomat/0.1 (https://github.com/Scryne; daily educational shorts)"}
WIKI_API = "https://en.wikipedia.org/w/api.php"
EZOP_URL = "https://www.gutenberg.org/ebooks/11339"
EN_AZ_METIN = 400  # karakter; daha kısa kaynaktan 75-90 kelimelik hikâye uydurmadan yazılamaz, hakem turları boşa gider


# Başlıkta/anlatımda hakaret ya da ağır küfür: reklam uygunluğu ve nefret söylemi politikası. TypeSafe süzgecinden
# "Lord Bloody Wog Rolo" geçti, video 10-13'e planlanmıştı (10-12'de geri çekildi). Kelime sınırıyla: Fagan,
# raccoon geçer. "dyke" çıkarıldı (10-13): Hollanda seddi makalelerini render'dan sonra reddediyordu.
HAKARET = re.compile(
    r"\b(?:wogs?|nigg(?:er|a)s?|coons?|chinks?|gooks?|japs?|kikes?|spics?|wetbacks?|pakis?|ragheads?|redskins?|"
    r"squaws?|trann(?:y|ies)|retards?|fags?|faggots?|cunts?|fuck\w*|shit\w*)\b",
    re.I,
)


class KaynakHatasi(RuntimeError):
    """Hikâyenin kaynağı kullanılamıyor (makale silinmiş/taşınmış ya da çok kısa): yalnız bu hikâye düşer."""


def _kol(bolum: str) -> str:
    return re.sub(r"[^a-z]+", "_", bolum.lower().split(",")[0]).strip("_")


def tuhaf_uygun(ts: dict) -> bool:
    """Hikâye anlatan (olay/kişi), reklamverenin kaçmayacağı, güncel siyasete girmeyen makale."""
    siyaset = ts.get("siyaset")  # yalnız ilk iki süzgeçten geçenlere soruldu
    return ts["hikaye"] >= 0.5 and ts["hassas"] < 0.5 and siyaset is not None and siyaset < 0.5


def ezop_uygun(ts: dict) -> bool:
    """Yetişkin teması yok. 10-13'e kadar 3-7 yaşa göre ölüm (`olum`) ve 5 yaşın anlayışı (`anlasilir`) da eleme
    nedeniydi (144/283); genel kitlede (K-24) ölüm düz söylenir, havuz 247'ye çıkar ve en bilinen masallar girer
    (Kuzu ile Kurt, Yalancı Çoban, Kral İsteyen Kurbağalar)."""
    return ts["yetiskin"] < 0.5


# Bugünün izleyicisine ırk ve kölelik üzerinden kurulmuş masallar (10-13, genişletilen 103 masal tek tek okundu)
EZOP_DISLA = {"The Blackamoor", "The Runaway Slave"}


def _tuhaf(havuz: list[dict], cekildi: str) -> list[OlguPaketi]:
    sonuc, gorulen = [], set()
    for h in havuz:
        # bazı makaleler iki bölümde listeli
        if not tuhaf_uygun(h["ts"]) or h["baslik"] in gorulen or HAKARET.search(h["baslik"]):
            continue
        gorulen.add(h["baslik"])
        url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(h["baslik"].replace(" ", "_"))
        sonuc.append(
            OlguPaketi(
                kol=_kol(h["bolum"]),
                tur="tuhaf",
                anahtar=f"wiki:{h['baslik']}",
                konu=h["tanim"],
                olgular={},
                gorsel={"sablon": "illustrasyon", "baslik": h["baslik"]},
                kaynak=Kaynak("Wikipedia", url, "CC BY-SA 4.0", cekildi),
                etiketler=list(dict.fromkeys(["history", "true story", _kol(h["bolum"]).replace("_", " ")])),
            )
        )
    return sonuc


def _ezop(havuz: list[dict], cekildi: str) -> list[OlguPaketi]:
    return [
        OlguPaketi(
            kol="ezop",
            tur="masal",
            anahtar=f"ezop:{h['baslik']}",
            konu=h["baslik"],
            olgular={},
            gorsel={"sablon": "illustrasyon", "baslik": h["baslik"], "metin": h["metin"]},
            kaynak=Kaynak("Aesop's Fables, tr. V. S. Vernon Jones (1912)", EZOP_URL, "Public domain", cekildi),
            etiketler=["Aesop", "fables", "short stories", "moral stories"],  # genel kitle (K-24, 10-13)
        )
        for h in havuz
        if ezop_uygun(h["ts"]) and h["baslik"] not in EZOP_DISLA and not HAKARET.search(h["baslik"])
    ]


KAYNAKLAR = {"tuhaf": _tuhaf, "ezop": _ezop}


def topla() -> tuple[list[OlguPaketi], list[str]]:
    k = kanal.aktif()
    havuz = json.loads(k.veri.read_text(encoding="utf-8"))
    cekildi = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    paketler: list[OlguPaketi] = []
    for ad in k.kaynaklar:
        paketler += KAYNAKLAR[ad](havuz, cekildi)
    return paketler, []


def _wiki(params: dict) -> dict:
    """429, 5xx ve bağlantı hataları yeniden denenir. Wikipedia'nın kalıcı hatası hikâye hatası değil (KaynakHatasi
    değil): öyle sayılsaydı geçici bir kesintide denenen 3 hikâye havuzdan kalıcı düşerdi; koşu düşer, alarm yazılır."""
    son = None
    for i in range(4):
        try:
            istek = urllib.request.Request(WIKI_API + "?" + urllib.parse.urlencode(params), headers=UA)
            with urllib.request.urlopen(istek, timeout=30) as yanit:
                return json.load(yanit)
        except urllib.error.HTTPError as e:
            if e.code != 429 and e.code < 500:
                raise
            son = e
        except (OSError, http.client.HTTPException, ValueError) as e:  # URLError, kopan bağlantı, yarım JSON
            son = e
        if i < 3:
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"wikipedia yanıt vermedi: {son}")


BITIS = re.compile(
    r"\n(?:See also|References|External links|Notes|Further reading|Sources|Bibliography|Footnotes|Citations|"
    r"Works cited)\n"
)


def metin(paket: OlguPaketi) -> str:
    """Hikâyenin tek doğruluk kaynağı (hakem buna bakar)."""
    if paket.tur == "masal":
        return paket.gorsel["metin"]
    d = _wiki(
        dict(action="query", titles=paket.gorsel["baslik"], prop="extracts", explaintext=1, exsectionformat="plain",
             format="json", formatversion=2, redirects=1)
    )["query"]["pages"][0]  # fmt: skip
    if "extract" not in d:
        raise KaynakHatasi(f"makale bulunamadı: {paket.gorsel['baslik']}")
    # Kaynakça ve dış bağlantılar hikâyeye girmesin
    govde = re.split(BITIS, d["extract"])[0].strip()
    if len(govde) < EN_AZ_METIN:
        raise KaynakHatasi(f"makale çok kısa ({len(govde)} karakter): {paket.gorsel['baslik']}")
    return govde
