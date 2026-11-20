"""Trend radarı: o an trend olan konuları iki bedava kaynaktan toplayıp birleştirir, skorlar ve sıralar.

Kaynaklar (ikisi de ücretsiz, anahtar gerektirmez; HTTP isteklerinde User-Agent zorunlu):
- Google Trends "Trending now" RSS: sorgu, yaklaşık arama trafiği, haber satırları, resim.
- Wikimedia Pageview API: günlük en çok görüntülenen makaleler (top) ve tek makalenin günlük
  görüntülemesi (artış oranı için taban medyanı).

Skor (belirleyici; birleşen konu ne kadar geniş ve hızlı büyüyorsa o kadar yüksek):
  skor = 1.0*log10(1+gt_trafik) + 0.8*len(gt_geolar)
       + 1.2*log10(1+wiki_goruntuleme) + 1.5*log2(max(wiki_artis or 1, 1))
GT trafiği hacmi, geo sayısı yayılımı, wiki görüntüleme büyüklüğü, artış momentumu ölçer.
"""

import dataclasses as dc
import datetime as dt
import json
import math
import re
import statistics
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "Otomat/0.1 (https://github.com/Scryne; trend research)"}
GT_RSS = "https://trends.google.com/trending/rss?geo={geo}"
WIKI_TOP_URL = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/{y}/{m}/{d}"
WIKI_MAKALE_URL = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{makale}"
    "/daily/{bas}/{bit}"
)
HT_NS = {"ht": "https://trends.google.com/trending/rss"}  # Google Trends RSS ad alanı
# "The_Hunger_Games:_..." gibi iki nokta içeren asıl makaleler elenmez; iki noktanın öncesindeki
# bölüm bu kümedeyse ad alanı sayfasıdır (Special:, Wikipedia:, File:, Portal:, Help:, Template:,
# Category:, Talk:, User:)
AD_ALANLARI = frozenset({"Special", "Wikipedia", "File", "Portal", "Help", "Template", "Category", "Talk", "User"})
TABAN_ALT_SINIR = 50  # az görüntülenen makalede artış oranı gürültüdür
ARTIS_TABAN_GUN = 28  # son 3 gün (son gün + önceki 2) hariç tabana giren en çok gün sayısı

# GT yaklaşık trafiği: "200+", "1,000+", "20K+", "2M+"
TRAFIK_BICIMI = re.compile(r"^([\d.,]*\d[\d.,]*)\s*([kKmM])?\+?$")


class RadarHatasi(RuntimeError):
    """Trend kaynağı kullanılamıyor (404, yanıt yok)."""


@dc.dataclass
class GTKayit:
    """Google Trends'ten tek satır."""

    sorgu: str
    geo: str
    trafik: int
    zaman: dt.datetime  # UTC, tz-aware
    haberler: list[dict] = dc.field(default_factory=list)  # {"baslik", "url", "kaynak"}
    resim: str | None = None


@dc.dataclass
class Konu:
    """Birleşik trend adayı: aynı konuda GT sorguları ve (eşleşirse) wiki makalesi tek satırda."""

    anahtar: str  # normalize(ad); eşleştirme kimliği
    ad: str  # okunur ad: wiki varsa makale başlığı, yoksa GT sorgusu
    gt_trafik: int = 0  # bütün geolardaki trafiğin toplamı
    gt_geolar: list[str] = dc.field(default_factory=list)  # sıralı (görülme sırası), tekrarsız
    haberler: list[dict] = dc.field(default_factory=list)  # url'ye göre tekrarsız, en çok 10
    wiki_makale: str | None = None
    wiki_goruntuleme: int = 0
    wiki_artis: float | None = None  # son gün / taban medyanı
    skor: float = 0.0


def normalize(metin: str) -> str:
    """Eşleştirme anahtarı: küçük harf, aksan sil (NFKD), parantez içi yok, harf/rakam dışı boşluk, tek boşluk."""
    ayrisik = unicodedata.normalize("NFKD", metin)
    aksansiz = "".join(h for h in ayrisik if not unicodedata.combining(h)).lower().replace("_", " ")
    parantezsiz = re.sub(r"\([^)]*\)", " ", aksansiz)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", parantezsiz).split())


def trafik_sayi(metin: str) -> int:
    """GT yaklaşık trafiği sayıya çevirir: "200+"→200, "20K+"→20000, "2M+"→2000000, "1,000+"→1000. Tanınmazsa 0."""
    es = TRAFIK_BICIMI.match(metin.strip())
    if not es:
        return 0
    kat = (es.group(2) or "").upper()
    return int(float(es.group(1).replace(",", "")) * {"": 1, "K": 1_000, "M": 1_000_000}[kat])


def gt_ayristir(xml_metin: str, geo: str) -> list[GTKayit]:
    """Google Trends RSS'ini ayrıştırır. `<pubDate>` RFC 2822'dir, UTC'ye çevrilir.

    `<description/>` boş gelir, `ht:news_item_snippet` boş olabilir; ikisi de okunmaz.
    """
    kayitlar = []
    for item in ET.fromstring(xml_metin).findall(".//item"):
        haberler = [
            {
                "baslik": (ni.findtext("ht:news_item_title", namespaces=HT_NS) or "").strip(),
                "url": (ni.findtext("ht:news_item_url", namespaces=HT_NS) or "").strip(),
                "kaynak": (ni.findtext("ht:news_item_source", namespaces=HT_NS) or "").strip(),
            }
            for ni in item.findall("ht:news_item", HT_NS)
        ]
        zaman = dt.datetime.strptime((item.findtext("pubDate") or "").strip(), "%a, %d %b %Y %H:%M:%S %z").astimezone(
            dt.UTC
        )
        kayitlar.append(
            GTKayit(
                sorgu=(item.findtext("title") or "").strip(),
                geo=geo,
                trafik=trafik_sayi(item.findtext("ht:approx_traffic", namespaces=HT_NS) or ""),
                zaman=zaman,
                haberler=haberler,
                resim=item.findtext("ht:picture", namespaces=HT_NS) or None,
            )
        )
    return kayitlar


def makale_uygun(makale: str) -> bool:
    """Wiki top listesinde anlamlı bir konu makalesi mi: teknik/ad alanı, ölüm listesi, liste ve
    "Other" satırı ("-") elenir."""
    if makale == "Main_Page" or makale == "-":  # ana sayfa ve Wikimedia'nın "Other" satırı
        return False
    if ":" in makale and makale.split(":", 1)[0] in AD_ALANLARI:
        return False
    if makale.startswith(("Deaths_in_", "List_of_")) or makale.startswith("."):
        return False
    return True


def wiki_top_ayristir(json_metin: str) -> list[tuple[str, int]]:
    """Wikimedia top yanıtından uygun makaleleri (makale, görüntüleme) olarak liste sırasıyla döndürür."""
    makaleler = json.loads(json_metin)["items"][0]["articles"]
    return [(m["article"], m["views"]) for m in makaleler if makale_uygun(m["article"])]


def artis_hesapla(json_metin: str, taban_gun: int = ARTIS_TABAN_GUN) -> float | None:
    """Son günün görüntülemesinin taban medyanına oranı (`round(..., 2)`).

    Taban: son günden önceki 2 gün hariç (yükselişin başı tabanı şişirmesin; son 3 gün girmez),
    ondan önceki en çok `taban_gun` günün medyanı. Medyan `TABAN_ALT_SINIR`'in altındaysa o kullanılır.
    Eleman sayısı 7'den azsa None.
    """
    elemanlar = sorted(json.loads(json_metin)["items"], key=lambda e: e["timestamp"])
    if len(elemanlar) < 7:
        return None
    taban = statistics.median(e["views"] for e in elemanlar[:-3][-taban_gun:])
    return round(elemanlar[-1]["views"] / max(taban, TABAN_ALT_SINIR), 2)


def _ayni_konu(anahtar1: str, anahtar2: str) -> bool:
    """İki normalize anahtar aynı konu mu: eşitler, ya da kısa olan ≥ 2 kelimelik ve bütün kelimeleri
    uzun olanda var. Tek kelimelik ("vgk") bir makaleyle ("vgk arena") birleşmez."""
    if anahtar1 == anahtar2:
        return True
    kisa, uzun = sorted((anahtar1, anahtar2), key=len)
    kelimeler = kisa.split()
    return len(kelimeler) >= 2 and set(kelimeler) <= set(uzun.split())


def birlestir(gt: list[GTKayit], wiki: list[tuple[str, int]], artislar: dict[str, float]) -> list[Konu]:
    """GT kayıtlarını ve wiki makalelerini konulara birleştirir, her konuyu skorlar.

    GT kayıtları `normalize(sorgu)` anahtarıyla gruplanır (trafik toplanır, geo eklenir, haberler
    url'ye göre tekrarsız birleşir, en çok 10). Her wiki makalesi ilk eşleşen gruba gider (eşleşme
    `_ayni_konu`); bir grup yalnız ilk makaleyi okunur ad ve artış için alır, sonraki eşleşmeler
    kendi konularını açar. Hiçbir gruba tutmayan makale de kendi konusunu açar. Dönüş skora göre
    azalan, eşitlikte anahtara göre artan.
    """
    konular: dict[str, Konu] = {}
    for kayit in gt:
        anahtar = normalize(kayit.sorgu)
        konu = konular.get(anahtar)
        if konu is None:
            konu = Konu(anahtar=anahtar, ad=kayit.sorgu)
            konular[anahtar] = konu
        konu.gt_trafik += kayit.trafik
        if kayit.geo not in konu.gt_geolar:
            konu.gt_geolar.append(kayit.geo)
        gorulen = {h["url"] for h in konu.haberler}
        for haber in kayit.haberler:
            if haber["url"] not in gorulen and len(konu.haberler) < 10:
                gorulen.add(haber["url"])
                konu.haberler.append(haber)
    eslesen: set[str] = set()  # wiki makalesi bağlanmış grup anahtarları
    for makale, goruntuleme in wiki:
        m_anahtar = normalize(makale)
        hedef = konular.get(m_anahtar)
        if hedef is None:
            hedef = next((k for a, k in konular.items() if a not in eslesen and _ayni_konu(m_anahtar, a)), None)
        if hedef is None:
            hedef = Konu(anahtar=m_anahtar, ad=makale.replace("_", " "))
            konular[m_anahtar] = hedef
        hedef.wiki_goruntuleme += goruntuleme
        if hedef.wiki_makale is None:  # okunur ad ve artış wiki makalesinden gelir
            hedef.wiki_makale = makale
            if hedef.gt_geolar:  # wiki başlığı GT sorgusundan daha okunur
                hedef.ad = makale.replace("_", " ")
            hedef.wiki_artis = artislar.get(makale)
            eslesen.add(hedef.anahtar)
    sonuc = list(konular.values())
    for konu in sonuc:
        konu.skor = skorla(konu)
    return sorted(sonuc, key=lambda k: (-k.skor, k.anahtar))


def skorla(k: Konu) -> float:
    """Belirleyici skor (modül docstring'indeki formül), `round(..., 3)`."""
    return round(
        1.0 * math.log10(1 + k.gt_trafik)
        + 0.8 * len(k.gt_geolar)
        + 1.2 * math.log10(1 + k.wiki_goruntuleme)
        + 1.5 * math.log2(max(k.wiki_artis or 1, 1)),
        3,
    )


# --- ağ katmanı (ince sarmalayıcı; testte çağrılmaz) ---


def _getir(url: str, deneme: int = 3) -> str:
    """UA başlıklı GET. 5xx ve bağlantı hatasında 2 sn bekleyip yeniden denenir; 404 ve denemeleri
    tükenen istek `RadarHatasi` verir. Diğer 4xx doğrudan yükselir: yeniden denemenin anlamı yok."""
    son_hata = None
    for deneme_no in range(deneme):
        try:
            istek = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(istek, timeout=30) as yanit:
                return yanit.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise RadarHatasi(f"kaynak yok (404): {url}") from e
            if e.code < 500:
                raise
            son_hata = e
        except urllib.error.URLError as e:  # DNS, bağlantı, zaman aşımı
            son_hata = e
        if deneme_no < deneme - 1:
            time.sleep(2)
    raise RadarHatasi(f"kaynak yanıt vermedi ({deneme} deneme): {url} — {son_hata}")


def google_trends(geo: str) -> list[GTKayit]:
    """Bir geo'nun o anki trend sorguları."""
    return gt_ayristir(_getir(GT_RSS.format(geo=geo)), geo)


def wiki_top(gun: dt.date) -> list[tuple[str, int]]:
    """Bir günün en çok görüntülenen uygun makaleleri, sırayla."""
    url = WIKI_TOP_URL.format(y=gun.year, m=f"{gun.month:02d}", d=f"{gun.day:02d}")
    return wiki_top_ayristir(_getir(url))


def wiki_artis(makale: str, gun: dt.date, taban_gun: int = ARTIS_TABAN_GUN) -> float | None:
    """Makalenin `gun` dahil 40 günlük görüntülemesinden artış oranı. Makale bu pencerede yoksa None."""
    bit = gun.strftime("%Y%m%d")
    bas = (gun - dt.timedelta(days=39)).strftime("%Y%m%d")
    url = WIKI_MAKALE_URL.format(makale=urllib.parse.quote(makale, safe=""), bas=bas, bit=bit)
    try:
        return artis_hesapla(_getir(url), taban_gun)
    except (RadarHatasi, urllib.error.URLError):  # yok/taşınmış makale ya da 429: artışsız devam
        return None


def topla(
    gun: dt.date | None = None,
    geolar: tuple[str, ...] = ("US", "GB", "IN", "CA", "AU", "IE", "NZ", "ZA", "PH", "NG"),
    wiki_ilk: int = 60,
) -> list[Konu]:
    """Günlük trend tablosu: bütün geolardaki GT kayıtları + wiki top'un ilk `wiki_ilk` uygun makalesi
    (her birine `wiki_artis`), birleştirilmiş ve skorlanmış.

    `gun` None ise dünün UTC tarihi. Düşen tek geo ya da wiki atlanır; hiçbir kaynak çalışmazsa
    `RadarHatasi`.
    """
    if gun is None:
        gun = (dt.datetime.now(dt.UTC) - dt.timedelta(days=1)).date()
    gt: list[GTKayit] = []
    for geo in geolar:
        try:
            gt += google_trends(geo)
        except (RadarHatasi, urllib.error.URLError):  # bir geo düşerse onu atla
            pass
    try:
        wiki = wiki_top(gun)[:wiki_ilk]
    except (RadarHatasi, urllib.error.URLError):
        wiki = []
    if not gt and not wiki:
        raise RadarHatasi("hiçbir trend kaynağı yanıt vermedi")
    artislar = {}
    for makale, _ in wiki:
        artis = wiki_artis(makale, gun)
        if artis is not None:
            artislar[makale] = artis
    return birlestir(gt, wiki, artislar)
