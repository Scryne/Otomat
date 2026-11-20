"""Trend konusu için anlatım kaynaklarını toplar: Wikipedia düz metni (sabit revizyonla) ve özeti,
Google News arama haberleri, Wikimedia Commons'ta serbest lisanslı görseller.

Hepsi anahtar gerektirmeyen ücretsiz uçlar. Ağ katmanı `radar._getir`'i ve `radar.UA`'yı yeniden
kullanır (aynı yeniden deneme ilkesi); ikili indirme için ayrı `_indir` yazıldı. Wikimedia nezaket
kuralı: istek/indirme arasında en az 1 sn bekleme.
"""

import dataclasses as dc
import datetime as dt
import email.utils
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from otomat.trend.radar import UA, RadarHatasi, _getir

WIKI_OZET_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{baslik}"
WIKI_METIN_URL = (
    "https://en.wikipedia.org/w/api.php?action=query&format=json&formatversion=2"
    "&prop=extracts|revisions|images&explaintext=1&rvprop=ids|timestamp&imlimit=50&redirects=1&titles={baslik}"
)
GNEWS_URL = "https://news.google.com/rss/search?q={q}+when:{gun}d&hl=en-US&gl=US&ceid=US:en"
COMMONS_URL = "https://commons.wikimedia.org/w/api.php"
COMMONS_SAYFA_URL = "https://commons.wikimedia.org/wiki/"
# hem generator=search hem titles= isteklerinde ortak imageinfo parametreleri
COMMONS_IMAGEINFO = {
    "action": "query",
    "format": "json",
    "prop": "imageinfo",
    "iiprop": "url|extmetadata|size|mime",
    "iiurlwidth": 1920,
}
# "== X ==" ve "=== X ===" satırları bölüm sınırıdır
BOLUM_BASLIGI = re.compile(r"^(={2,})\s*(.+?)\s*\1$")
ATLANAN_BOLUMLER = frozenset({"see also", "references", "external links", "notes", "further reading"})
# Dekor/infobox dosyaları: adında bu sözcükler geçen görsel anlatıma yakışmaz
DEKOR_SOZCUKLERI = ("logo", "icon", "flag", "symbol", "map", "coat of arms", "signature", "seal", "diagram")
BITMAP_MIME = frozenset({"image/jpeg", "image/png", "image/webp"})


class KaynakHatasi(RuntimeError):
    """Anlatım kaynağı kullanılamıyor (404, yanıt yok, sayfa yok)."""


@dc.dataclass
class WikiMetin:
    """Bir Wikipedia makalesinin düz metni, sabit revizyonu ve dosya listesi."""

    baslik: str
    revid: int  # anlatım bu revizyona bağlanır
    zaman: str  # revizyon zaman damgası (ISO 8601)
    metin: str  # extracts ile düz metin; "== Başlık ==" satırları bölüm sınırıdır
    dosyalar: list[str]  # makaledeki "File:..." adları
    ozet: str = ""  # REST summary extract
    aciklama: str = ""  # REST summary description

    def bolumler(self) -> list[tuple[str, str]]:
        """Metni (bolum_basligi, govde) listesine böler. Başlıktan önceki kısım "Lead"; "== X ==" ve
        "=== X ===" satırları bölüm sınırıdır (alt başlıklar ayrı bölüm sayılır). "See also",
        "References", "External links", "Notes", "Further reading" bölümleri ve boş gövdeliler
        atlanır."""
        sonuc: list[tuple[str, str]] = []
        baslik = "Lead"
        govde: list[str] = []

        def _bosalt() -> None:
            metin = "\n".join(govde).strip()
            if metin and baslik.lower() not in ATLANAN_BOLUMLER:
                sonuc.append((baslik, metin))

        for satir in self.metin.splitlines():
            es = BOLUM_BASLIGI.match(satir.strip())
            if es:
                _bosalt()
                baslik = es.group(2)
                govde = []
            else:
                govde.append(satir)
        _bosalt()
        return sonuc


@dc.dataclass
class Haber:
    """Google News arama satırı; `baslik` sondaki " - Yayıncı" ekinden arındırılmıştır."""

    baslik: str
    yayinci: str
    url: str
    zaman: dt.datetime  # UTC, tz-aware


@dc.dataclass
class Gorsel:
    """Commons dosyası; `url` thumburl varsa o (1920 genişlik), yoksa asıl dosya."""

    dosya: str  # "File:..."
    url: str
    genislik: int
    yukseklik: int
    mime: str
    lisans: str  # LicenseShortName, HTML'den arındırılmış
    yazar: str  # Artist, düz metin, en çok 80 karakter
    kredi_satiri: str  # ekrana yazılır: "Photo: {yazar} / {lisans}"
    sayfa: str  # Commons açıklama sayfası


def wiki_ozet_ayristir(json_metin: str) -> tuple[str, str]:
    """REST summary yanıtından (description, extract). Alan yoksa ""."""
    veri = json.loads(json_metin)
    return (veri.get("description") or "", veri.get("extract") or "")


def wiki_metin_ayristir(json_metin: str) -> WikiMetin:
    """action=query yanıtından makale (formatversion=2: `pages` LİSTE). Sayfa yoksa (missing)
    KaynakHatasi."""
    sayfa = json.loads(json_metin)["query"]["pages"][0]
    if "missing" in sayfa:
        raise KaynakHatasi(f"wiki sayfası yok: {sayfa.get('title', '?')}")
    revizyon = sayfa["revisions"][0]
    return WikiMetin(
        baslik=sayfa.get("title", ""),
        revid=revizyon.get("revid", 0),
        zaman=revizyon.get("timestamp", ""),
        metin=sayfa.get("extract", ""),
        dosyalar=[g["title"] for g in sayfa.get("images", []) if "title" in g],
    )


def haber_ayristir(xml_metin: str) -> list[Haber]:
    """Google News arama RSS'i. Başlıktaki son " - " ayrıcından sonrası yayıncıdır ve başlıktan
    ayıklanır; `<source>` öğesi varsa yayıncı ondan alınır. Aynı başlık bir kez tutulur.
    `<pubDate>` RFC 2822'dir; dönüş en yeni önce sıralı, zaman UTC tz-aware."""
    kayitlar: list[Haber] = []
    gorulen: set[str] = set()
    for item in ET.fromstring(xml_metin).findall(".//item"):  # kanal başlığı item değildir
        tam = (item.findtext("title") or "").strip()
        baslik, kuyruk = tam.rsplit(" - ", 1) if " - " in tam else (tam, "")
        baslik = baslik.strip()
        if not baslik or baslik in gorulen:
            continue
        gorulen.add(baslik)
        zaman = email.utils.parsedate_to_datetime((item.findtext("pubDate") or "").strip())
        if zaman.tzinfo is None:  # parsedate nadiren naive döner
            zaman = zaman.replace(tzinfo=dt.UTC)
        kayitlar.append(
            Haber(
                baslik=baslik,
                yayinci=(item.findtext("source") or "").strip() or kuyruk.strip(),
                url=(item.findtext("link") or "").strip(),
                zaman=zaman,
            )
        )
    return sorted(kayitlar, key=lambda h: h.zaman, reverse=True)


def html_temizle(s: str) -> str:
    """HTML etiketlerini siler, varlıkları çözer (`&nbsp;`), boşlukları tekle."""
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", s)).split())


def lisans_serbest(lisans: str) -> bool:
    """Lisans adı serbest mi (büyük/küçük harf duyarsız). NC/ND önce denetlenir: "CC BY-NC-SA 2.0"
    serbest değildir. "Fair use", "non-free" ve boş adlar da serbest sayılmaz."""
    ad = lisans.strip().lower()
    if not ad:
        return False
    if "-nc" in ad or "noncommercial" in ad or "-nd" in ad or "noderivs" in ad:
        return False
    if "fair use" in ad or "non-free" in ad:
        return False
    return (
        ad.startswith("pd")
        or "public domain" in ad
        or ad.startswith("cc0")
        or "cc by" in ad
        or "attribution" in ad
        or "gfdl" in ad
        or "no restrictions" in ad
    )


def gorsel_ayristir(json_metin: str) -> list[Gorsel]:
    """Commons imageinfo yanıtını Görsellere çevirir (`query.pages` SÖZLÜK, anahtar pageid). Arama
    yanıtlarında "index" varsa sonuç o sıraya dizilir. Makaledeki yerel (fair use) dosyalar
    Commons'ta "missing" döner; lisansı serbest olmayanla birlikte ikisi de elenir."""
    sayfalar = json.loads(json_metin).get("query", {}).get("pages", {})
    sonuc = []
    for sayfa in sorted(sayfalar.values(), key=lambda s: s.get("index", 10**9)):
        if "missing" in sayfa or not sayfa.get("imageinfo"):
            continue
        bilgi = sayfa["imageinfo"][0]
        meta = bilgi.get("extmetadata", {})
        lisans = html_temizle(meta.get("LicenseShortName", {}).get("value", ""))
        if not lisans_serbest(lisans):
            continue
        yazar = html_temizle(meta.get("Artist", {}).get("value", ""))[:80]
        dosya = sayfa.get("title", "")
        sonuc.append(
            Gorsel(
                dosya=dosya,
                url=bilgi.get("thumburl") or bilgi.get("url", ""),
                genislik=bilgi.get("width", 0),
                yukseklik=bilgi.get("height", 0),
                mime=bilgi.get("mime", ""),
                lisans=lisans,
                yazar=yazar,
                kredi_satiri=f"Photo: {yazar} / {lisans}" if yazar else f"Photo: Wikimedia Commons / {lisans}",
                sayfa=COMMONS_SAYFA_URL + urllib.parse.quote(dosya.replace(" ", "_")),
            )
        )
    return sonuc


def gorsel_uygun(g: Gorsel, en_az_genislik: int = 1000) -> bool:
    """Görsel videoya yakışır mı: bitmap (jpeg/png/webp), genişlik eşik üstü, en-boy oranı
    0.5..2.6 (yatay çok geniş / dikey çok uzun değil), adında dekor sözcüğü (logo, flag, simge…)
    yok. Ölçüler asıl dosyanındır; thumb genişliği değil."""
    if g.mime not in BITMAP_MIME or g.genislik < en_az_genislik or g.yukseklik <= 0:
        return False
    if not 0.5 <= g.genislik / g.yukseklik <= 2.6:
        return False
    ad = g.dosya.lower()
    return not any(sozcuk in ad for sozcuk in DEKOR_SOZCUKLERI)


# --- ağ katmanı (ince sarmalayıcı; testte çağrılmaz) ---


def _cagir(url: str) -> str:
    """`radar._getir`'i çağırır; hata türünü bu modülün `KaynakHatasi`'sına çevirir."""
    try:
        return _getir(url)
    except RadarHatasi as e:
        raise KaynakHatasi(str(e)) from e


def wiki_metin(baslik: str) -> WikiMetin:
    """Makalenin düz metni (sabit revizyonla) ve REST summary özeti; iki istek. Özet alınamazsa
    (summary 404) boş özetle devam: asıl içerik metin isteğindedir."""
    kodlu = urllib.parse.quote(baslik.replace(" ", "_"), safe="")
    kayit = wiki_metin_ayristir(_cagir(WIKI_METIN_URL.format(baslik=kodlu)))
    try:
        kayit.aciklama, kayit.ozet = wiki_ozet_ayristir(_cagir(WIKI_OZET_URL.format(baslik=kodlu)))
    except KaynakHatasi:
        pass
    return kayit


def haberler(sorgu: str, gun: int = 3, en_cok: int = 20) -> list[Haber]:
    """Son `gun` günün haberleri, en yeni önce, en çok `en_cok`."""
    q = urllib.parse.quote_plus('"' + sorgu + '"')
    return haber_ayristir(_cagir(GNEWS_URL.format(q=q, gun=gun)))[:en_cok]


def commons_ara(sorgu: str, n: int = 20) -> list[Gorsel]:
    """Commons'ta bitmap araması; serbest lisanslı olmayanlar `gorsel_ayristir`'da zaten elenir."""
    parametreler = COMMONS_IMAGEINFO | {
        "generator": "search",
        "gsrsearch": f"filetype:bitmap {sorgu}",
        "gsrnamespace": 6,
        "gsrlimit": n,
    }
    return gorsel_ayristir(_cagir(f"{COMMONS_URL}?{urllib.parse.urlencode(parametreler)}"))


def commons_dosyalar(dosyalar: list[str]) -> list[Gorsel]:
    """Adı verilen "File:..." dosyalarının imageinfo'su, 40'lık parçalarla (Commons istek sınırı).
    Yerel (fair use) dosyalar Commons'ta "missing" döner: `gorsel_ayristir` eler."""
    sonuc = []
    for i in range(0, len(dosyalar), 40):
        parc = dosyalar[i : i + 40]
        parametreler = COMMONS_IMAGEINFO | {"titles": "|".join(parc)}
        sonuc += gorsel_ayristir(_cagir(f"{COMMONS_URL}?{urllib.parse.urlencode(parametreler)}"))
        if i + 40 < len(dosyalar):
            time.sleep(1)  # art arda istekler arasında bekleme
    return sonuc


def gorsel_indir(g: Gorsel, dizin: Path) -> Path:
    """Görseli `dizin`e indirir. Ad: güvenli ascii slug + url'den gerçek uzantı (başlıktaki uzantı
    değil; thumb format değiştirebilir); dosya varsa indirilmez. Wikimedia kuralı: indirmeden önce
    1 sn bekleme."""
    dizin.mkdir(parents=True, exist_ok=True)
    govde = g.dosya
    if "." in govde:
        govde = govde.rsplit(".", 1)[0]
    slug = re.sub(r"[^a-z0-9]+", "-", govde.lower())
    if slug.startswith("file-"):
        slug = slug[len("file-") :]
    slug = slug[:60].strip("-")
    uzanti = Path(urllib.parse.urlparse(g.url).path).suffix.lstrip(".") or "jpg"
    hedef = dizin / f"{slug}.{uzanti}"
    if hedef.exists():
        return hedef
    time.sleep(1)
    return _indir(g.url, hedef)


def _indir(url: str, hedef: Path) -> Path:
    """UA başlıklı ikili GET; önce ".part" dosyasına yazar, sonra yerine taşır. 5xx ve bağlantı
    hatasında 2 sn bekleyip yeniden denenir; 404 ve denemeleri tükenen istek KaynakHatasi verir.
    Diğer 4xx doğrudan yükselir: yeniden denemenin anlamı yok."""
    parc = hedef.with_name(hedef.name + ".part")
    son_hata = None
    for deneme_no in range(3):
        try:
            istek = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(istek, timeout=30) as yanit:
                parc.write_bytes(yanit.read())
            parc.replace(hedef)
            return hedef
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise KaynakHatasi(f"kaynak yok (404): {url}") from e
            if e.code < 500:
                raise
            son_hata = e
        except urllib.error.URLError as e:  # DNS, bağlantı, zaman aşımı
            son_hata = e
        if deneme_no < 2:
            time.sleep(2)
    raise KaynakHatasi(f"kaynak indirilemedi (3 deneme): {url} — {son_hata}")
