"""Spor kanalı havuzu (Faz 19, K-37): Wikipedia'nın maç/dövüş/olay makaleleri, popülerliğe göre.

Üç seri, üç profil (kanallar/futbol, mma, boks): her biri günde bir video. Aday makaleler kategori ağacından toplanır,
son 60 günün ortalama günlük görüntülemesiyle sıralanır (popüler konu = hazır kitle; araştırma 12/13), sonra TypeSafe
ile süzülür (K-18'in yöntemi: hikâye mi, hassas mı, güncel siyaset mi). Puanlar havuzda, eşikler kaynaklar.py'de.

    uv run python spikes/s17_spor_havuz.py aday futbol        # calisma/spor/aday_futbol.json
    uv run python spikes/s17_spor_havuz.py puan futbol        # TypeSafe -> kanallar/futbol/havuz.json
"""

import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from otomat.ayarlar import KOK

UA = {"User-Agent": "Otomat/0.1 (https://github.com/Scryne; daily educational shorts)"}
API = "https://en.wikipedia.org/w/api.php"
CIKTI = KOK / "calisma" / "spor"

# seri -> (kol, kök kategori, derinlik). Kol haydudun öğrendiği konu eksenidir.
KOKLER = {
    "futbol": [
        ("dunya_kupasi", "FIFA World Cup matches", 2),
        ("dunya_kupasi", "FIFA World Cup finals", 1),
        ("avrupa_finali", "UEFA Champions League finals", 1),
        ("avrupa_finali", "UEFA Europa League finals", 1),
        ("avrupa_finali", "UEFA European Championship finals", 1),
        ("kupa_finali", "Association football finals", 2),  # FA Cup, Copa Libertadores, Copa América… finalleri
        ("tartisma", "Association football controversies", 2),
        ("mac", "International association football matches", 2),
        ("mac", "Men's association football matches", 2),
        ("mac", "Association football matches by team", 2),
    ],
    "mma": [
        ("ufc", "Ultimate Fighting Championship flagship events", 1),
        ("ufc", "Ultimate Fighting Championship events in the Las Vegas Valley", 1),
        ("ufc", "Ultimate Fighting Championship events in New York City", 1),
        ("ufc", "UFC Fight Night", 1),
        ("ufc", "UFC on ESPN", 1),
        ("ufc", "UFC on ABC", 1),
        ("ufc", "Fox UFC", 1),
        ("dovus", "Mixed martial arts matches", 1),
        ("dovus", "Mixed martial arts controversies", 1),
        ("pride", "Pride Fighting Championships events", 1),
        ("dovus", "Mixed martial arts events", 2),
    ],
    "boks": [
        ("unvan", "Professional boxing world title matches", 2),
        ("mac", "Boxing matches by year", 2),
        ("mac", "Pay-per-view boxing matches", 1),
        ("mac", "Boxing matches by boxer", 2),
        ("capraz", "Crossover boxing matches", 1),
    ],
}
EN_AZ_BAYT = 7000  # kısa makale (sonuç tablosu + iki cümle) 75-90 kelimelik hikâyeye yetmez
EN_AZ_GORUNTULENME = 15  # günlük ortalama; altı "popüler" değil
LISTE = re.compile(
    r"^(?:List of|Lists of|Timeline of|\d{4}(?:–\d{2,4})? in )|\bseason\b|\bstatistics\b|\brecords\b", re.I
)


def al(params: dict) -> dict:
    params = {**params, "format": "json", "formatversion": 2}
    for deneme in range(5):
        try:
            istek = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=UA)
            with urllib.request.urlopen(istek, timeout=40) as y:
                return json.load(y)
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            if deneme == 4:
                raise
            print(f"  yeniden ({e})", file=sys.stderr)
            time.sleep(5 * (deneme + 1))
    raise RuntimeError


def uyeler(kat: str) -> tuple[list[str], list[str]]:
    sayfa, alt, devam = [], [], {}
    while True:
        d = al(dict(action="query", list="categorymembers", cmtitle="Category:" + kat, cmlimit=500,
                    cmtype="page|subcat", **devam))  # fmt: skip
        for m in d["query"]["categorymembers"]:
            (alt if m["ns"] == 14 else sayfa).append(m["title"].removeprefix("Category:"))
        if "continue" not in d:
            return sayfa, alt
        devam = d["continue"]


def tara(kok: str, derinlik: int, gorulen: set[str]) -> list[str]:
    sayfalar, sira = [], [(kok, 0)]
    while sira:
        kat, d = sira.pop(0)
        if kat in gorulen:
            continue
        gorulen.add(kat)
        s, alt = uyeler(kat)
        sayfalar += s
        if d < derinlik:
            sira += [(a, d + 1) for a in alt if not re.search(r"(?i)cancel|proposed|women|award|stub|templat", a)]
        time.sleep(0.2)
    return sayfalar


def bilgi(basliklar: list[str]) -> dict[str, dict]:
    """Uzunluk, kısa tanım ve son 60 günün ortalama günlük görüntülemesi (50'lik gruplar). `pageviews` bir istekte
    grubun yalnız bir kısmını döner, kalanı `continue` ile gelir: okunmayınca makalelerin çoğu 0 görüntülemeli kalıyordu
    (ilk koşu: MMA'nın 1.600 sayfasından 105'i)."""
    sonuc: dict[str, dict] = {}
    for i in range(0, len(basliklar), 50):
        grup, devam = basliklar[i : i + 50], {}
        while True:
            d = al(dict(action="query", titles="|".join(grup), prop="info|pageviews|description", pvipdays=60,
                        redirects=1, **devam))  # fmt: skip
            for p in d["query"].get("pages", []):
                if p.get("missing") or p.get("ns") != 0:
                    continue
                s = sonuc.setdefault(p["title"], {"bayt": 0, "tanim": "", "goruntulenme": 0})
                s["bayt"] = p.get("length", s["bayt"])
                s["tanim"] = p.get("description", s["tanim"])
                if gunler := [v for v in (p.get("pageviews") or {}).values() if v is not None]:
                    s["goruntulenme"] = round(sum(gunler) / len(gunler), 1)
            if "continue" not in d:
                break
            devam = d["continue"]
            time.sleep(0.2)
        time.sleep(0.3)
    return sonuc


def aday(seri: str) -> None:
    gorulen: set[str] = set()
    kol_of: dict[str, str] = {}
    for kol, kok, derinlik in KOKLER[seri]:
        bulunan = tara(kok, derinlik, gorulen)
        for b in bulunan:
            kol_of.setdefault(b, kol)
        print(f"{kok}: {len(bulunan)} sayfa (toplam {len(kol_of)})")
    basliklar = [b for b in kol_of if not LISTE.search(b)]
    b = bilgi(basliklar)
    adaylar = [
        {"baslik": t, "bolum": kol_of.get(t, "mac"), **v}
        for t, v in b.items()
        if v["bayt"] >= EN_AZ_BAYT and v["goruntulenme"] >= EN_AZ_GORUNTULENME
    ]
    adaylar.sort(key=lambda a: -a["goruntulenme"])
    CIKTI.mkdir(parents=True, exist_ok=True)
    yol = CIKTI / f"aday_{seri}.json"
    yol.write_text(json.dumps(adaylar, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{seri}: {len(basliklar)} başlık -> {len(adaylar)} aday ({yol.relative_to(KOK)})")


# --- TypeSafe (K-18 yöntemi; sürüm sabit: puanlar havuzda donar) ---
TS_MODEL = "jev-1.14.0"
TS_URL = "https://api.typesafe.ai/v1/systemone"
SORULAR = {
    "hikaye": {
        "type": "noul",
        "instructions": "Does `article` tell the story of one specific sporting event (a match, a fight, a final, an "
        "incident or a scandal) with a clear sequence of what happened, rather than being mainly a list of results, a "
        "fight card, a rivalry overview, a season summary or a biography?",
    },
    "dram": {
        "type": "noul",
        "instructions": "Does `article` describe something a casual sports fan would find dramatic or surprising: an "
        "upset, a comeback, a controversy, a brawl, a record, a famous moment or an unusual turn of events?",
    },
    "hassas": {
        "type": "noul",
        "instructions": "Is the central event of `article` a tragedy or abuse: people killed or fatally injured, a "
        "stadium disaster, a crowd crush, terrorism, sexual abuse, or a racist attack?",
    },
    "olmadi": {
        "type": "noul",
        "instructions": "Has the main event of `article` not taken place: it is still upcoming or scheduled, it was "
        "cancelled, or it was only proposed?",
    },
    "siyaset": {
        "type": "noul",
        "instructions": "Is `article` mainly about government politics, a war or a political conflict between states "
        "after 1990, rather than about sport?",
    },
}


def _ts(govde: dict) -> dict:
    socket.getaddrinfo = _ipv4(socket.getaddrinfo)
    istek = urllib.request.Request(
        TS_URL, json.dumps(govde).encode(), headers={"Authorization": f"Bearer {os.environ['TYPESAFE_API_KEY']}",
                                                     "Content-Type": "application/json"},
    )  # fmt: skip
    for deneme in range(4):
        try:
            with urllib.request.urlopen(istek, timeout=60) as y:
                return json.load(y)
        except (urllib.error.URLError, TimeoutError) as e:
            if deneme == 3:
                raise
            time.sleep(3 * (deneme + 1))
    raise RuntimeError


def _ipv4(asil):
    # bu makinede IPv6 çözümlemesi ~12 sn bekliyor (ts.py notu)
    if getattr(asil, "_ipv4", False):
        return asil

    def f(host, port, family=0, *a, **k):
        return asil(host, port, family or socket.AF_INET, *a, **k)

    f._ipv4 = True
    return f


def giris(baslik: str) -> str:
    """Giriş bölümü (maç makalesinde olayın özeti); kısa girişte gövdenin başı da eklenir."""
    d = al(dict(action="query", titles=baslik, prop="extracts", explaintext=1, exintro=1, redirects=1))
    metin = d["query"]["pages"][0].get("extract", "")
    if len(metin) < 800:
        d = al(dict(action="query", titles=baslik, prop="extracts", explaintext=1, redirects=1))
        metin = d["query"]["pages"][0].get("extract", "")
    return metin[:3000]


def puan(seri: str) -> None:
    adaylar = json.loads((CIKTI / f"aday_{seri}.json").read_text(encoding="utf-8"))
    ara = CIKTI / f"puan_{seri}.json"  # yarıda kesilirse kaldığı yerden
    puanli = json.loads(ara.read_text(encoding="utf-8")) if ara.exists() else {}
    for i, a in enumerate(adaylar):
        if a["baslik"] in puanli:
            continue
        metin = giris(a["baslik"])
        y = _ts({"model": TS_MODEL, "state": {"article": {"title": a["baslik"], "text": metin}}, "questions": SORULAR})
        puanli[a["baslik"]] = {k: round(v["noul"], 2) for k, v in y["answers"].items()}
        if i % 25 == 0:
            ara.write_text(json.dumps(puanli, ensure_ascii=False), encoding="utf-8")
            print(f"{i}/{len(adaylar)} {a['baslik']}: {puanli[a['baslik']]}")
        time.sleep(0.2)
    ara.write_text(json.dumps(puanli, ensure_ascii=False), encoding="utf-8")
    havuz = [{**a, "ts": puanli[a["baslik"]]} for a in adaylar]
    yol = KOK / "kanallar" / seri / "havuz.json"
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(havuz, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{seri}: {len(havuz)} -> {yol.relative_to(KOK)}")


if __name__ == "__main__":
    {"aday": aday, "puan": puan}[sys.argv[1]](sys.argv[2])
