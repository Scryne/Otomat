"""Trend kaynak toplayıcı testleri: yalnız ayrıştırıcılar ve saf fonksiyonlar sınanır (ağ yok)."""

import json
from pathlib import Path

import pytest

from otomat.trend import kaynak

VERI = Path(__file__).parent / "veri" / "trend"


def _metin(ad: str) -> str:
    return (VERI / ad).read_text(encoding="utf-8")


def test_wiki_ozet_ayristir():
    aciklama, ozet = kaynak.wiki_ozet_ayristir(_metin("wiki_ozet.json"))
    assert aciklama  # "2026 video game"
    assert "Grand Theft Auto VI" in ozet


def test_wiki_metin_ayristir():
    makale = kaynak.wiki_metin_ayristir(_metin("wiki_metin.json"))
    assert makale.baslik == "Grand Theft Auto VI"
    assert makale.revid == 1386720263
    assert makale.zaman == "2026-11-20T04:29:59Z"
    assert len(makale.metin) > 10_000
    assert "File:Miami - Skyline from Harbor.jpg" in makale.dosyalar
    assert len(makale.dosyalar) >= 10


def test_wiki_bolumler():
    bolumler = kaynak.wiki_metin_ayristir(_metin("wiki_metin.json")).bolumler()
    assert bolumler[0][0] == "Lead" and "Grand Theft Auto VI" in bolumler[0][1]
    assert len(bolumler) >= 4
    basliklar = [b[0] for b in bolumler]
    assert "Gameplay" in basliklar and "Development" in basliklar
    assert "Setting and characters" in basliklar  # alt başlık da ayrı bölümdür
    assert "Synopsis" not in basliklar  # gövdesiz üst başlık atlanır
    for atlanan in ("References", "External links", "Notes", "Further reading", "See also", "Awards"):
        assert atlanan not in basliklar  # atlanan + boş gövdeli ("Awards") bölümler
    assert all(govde.strip() for _, govde in bolumler)


def test_wiki_metin_ayristir_sayfa_yok():
    yanit = json.dumps({"query": {"pages": [{"missing": "", "title": "Yok"}]}})
    with pytest.raises(kaynak.KaynakHatasi):
        kaynak.wiki_metin_ayristir(yanit)


def test_haber_ayristir():
    kayitlar = kaynak.haber_ayristir(_metin("gnews_arama.xml"))
    assert len(kayitlar) >= 5
    assert all(not h.baslik.endswith(" - TODAY.com") for h in kayitlar)  # yayıncı başlıktan ayıklandı
    assert any(h.yayinci == "USA Today" for h in kayitlar)
    assert all(h.zaman.tzinfo is not None for h in kayitlar)
    assert kayitlar == sorted(kayitlar, key=lambda h: h.zaman, reverse=True)  # en yeni önce


def test_haber_yayinci_basliktan_ayiklanir():
    kayitlar = kaynak.haber_ayristir(_metin("gnews_arama.xml"))
    usa = next(h for h in kayitlar if h.yayinci == "USA Today")
    assert usa.baslik == "Here's where you know GTA 6 voice actress Manni L. Perez from"
    assert usa.url.startswith("https://")


def test_haber_tekrar_tek_tutulur():
    # ilk "A" haberi tutulur; source yoksa yayıncı başlıktaki kuyruktan gelir
    xml = (
        "<rss><channel><title>kanal</title>"
        "<item><title>A - X</title><link>https://x/1</link>"
        "<pubDate>Thu, 19 Nov 2026 10:00:00 GMT</pubDate><source url=''>X</source></item>"
        "<item><title>A - Y</title><link>https://x/2</link>"
        "<pubDate>Thu, 19 Nov 2026 11:00:00 GMT</pubDate><source url=''>Y</source></item>"
        "<item><title>C - Z</title><link>https://x/3</link>"
        "<pubDate>Thu, 19 Nov 2026 09:00:00 GMT</pubDate></item>"
        "</channel></rss>"
    )
    kayitlar = kaynak.haber_ayristir(xml)
    assert [(h.baslik, h.yayinci) for h in kayitlar] == [("A", "X"), ("C", "Z")]


def test_lisans_serbest():
    assert kaynak.lisans_serbest("CC BY 2.0")
    assert kaynak.lisans_serbest("CC BY-SA 4.0")
    assert kaynak.lisans_serbest("Public domain")
    assert kaynak.lisans_serbest("CC0")
    assert kaynak.lisans_serbest("pd-old")
    assert not kaynak.lisans_serbest("CC BY-NC-SA 2.0")  # NC önce denetlenir
    assert not kaynak.lisans_serbest("CC BY-ND 4.0")
    assert not kaynak.lisans_serbest("Fair use")
    assert not kaynak.lisans_serbest("")


def test_gorsel_ayristir():
    gorseller = kaynak.gorsel_ayristir(_metin("commons_arama.json"))
    assert len(gorseller) >= 5
    assert all(kaynak.lisans_serbest(g.lisans) for g in gorseller)
    assert any(g.kredi_satiri == "Photo: TechCrunch / CC BY 2.0" for g in gorseller)
    assert all(g.sayfa.startswith("https://commons.wikimedia.org/wiki/File%3A") for g in gorseller)
    assert all(g.url.startswith("https://") for g in gorseller)
    assert gorseller[0].dosya == "File:Dario Amodei in 2023.jpg"  # arama sırası ("index") korunur


def test_gorsel_missing_ve_fair_use_elenir():
    yanit = {
        "query": {
            "pages": {
                "1": {"pageid": 1, "ns": 6, "title": "File:Yerel fair use.jpg", "missing": ""},
                "2": {
                    "pageid": 2,
                    "ns": 6,
                    "title": "File:FairUse.jpg",
                    "index": 1,
                    "imageinfo": [
                        {
                            "url": "https://upload/fair.jpg",
                            "width": 2000,
                            "height": 1000,
                            "mime": "image/jpeg",
                            "extmetadata": {"LicenseShortName": {"value": "Fair use"}, "Artist": {"value": "X"}},
                        }
                    ],
                },
                "3": {
                    "pageid": 3,
                    "ns": 6,
                    "title": "File:Iyi foto.jpg",
                    "index": 2,
                    "imageinfo": [
                        {
                            "thumburl": "https://thumb/iyi.jpg",
                            "url": "https://upload/iyi.jpg",
                            "width": 4000,
                            "height": 3000,
                            "mime": "image/jpeg",
                            "extmetadata": {
                                "LicenseShortName": {"value": "CC BY-SA 4.0"},
                                "Artist": {"value": "<a href='u'>Yazar&nbsp;Adı</a>"},
                            },
                        }
                    ],
                },
            }
        }
    }
    gorseller = kaynak.gorsel_ayristir(json.dumps(yanit))
    assert [g.dosya for g in gorseller] == ["File:Iyi foto.jpg"]
    g = gorseller[0]
    assert g.url == "https://thumb/iyi.jpg"  # thumburl varsa o
    assert g.yazar == "Yazar Adı"  # HTML etiketleri ve &nbsp; temizlenir
    assert g.kredi_satiri == "Photo: Yazar Adı / CC BY-SA 4.0"
    assert g.sayfa == "https://commons.wikimedia.org/wiki/File%3AIyi_foto.jpg"  # quote ":" işaretini de kodlar


def test_html_temizle():
    assert kaynak.html_temizle('<a href="x">Ken&nbsp;Questa</a>  ') == "Ken Questa"


def test_gorsel_uygun():
    def _g(dosya="File:Normal foto.jpg", genislik=1920, yukseklik=1080, mime="image/jpeg"):
        return kaynak.Gorsel(
            dosya=dosya,
            url="https://x",
            genislik=genislik,
            yukseklik=yukseklik,
            mime=mime,
            lisans="CC BY 2.0",
            yazar="",
            kredi_satiri="",
            sayfa="",
        )

    assert kaynak.gorsel_uygun(_g())  # 1920x1080 jpeg, normal ad
    assert not kaynak.gorsel_uygun(_g(genislik=800))  # eşik altı genişlik
    assert not kaynak.gorsel_uygun(_g(dosya="File:Flag of Florida.svg", mime="image/svg+xml"))
    assert not kaynak.gorsel_uygun(_g(dosya="File:Logo of Company.png"))
    assert not kaynak.gorsel_uygun(_g(dosya="File:Map of Leonida.jpg"))
    assert not kaynak.gorsel_uygun(_g(genislik=1920, yukseklik=400))  # oran 4.8 > 2.6
    assert not kaynak.gorsel_uygun(_g(genislik=600, yukseklik=1920), en_az_genislik=500)  # oran < 0.5
    assert kaynak.gorsel_uygun(_g(genislik=1200, yukseklik=1920), en_az_genislik=1000)  # dikey foto


def test_gorsel_indir_varsa_indirmez(tmp_path):
    g = kaynak.Gorsel(
        dosya="File:Iyi foto.jpg",
        url="https://thumb/iyi.jpg",
        genislik=4000,
        yukseklik=3000,
        mime="image/jpeg",
        lisans="CC BY-SA 4.0",
        yazar="",
        kredi_satiri="",
        sayfa="",
    )
    hedef = tmp_path / "iyi-foto.jpg"
    hedef.write_bytes(b"eski")
    assert kaynak.gorsel_indir(g, tmp_path) == hedef
    assert hedef.read_bytes() == b"eski"  # ağa hiç gidilmedi
