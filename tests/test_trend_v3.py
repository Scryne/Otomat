"""Trend v3 (11-26, "gerçek insan gibi" geri bildirimi): Ming anlatıcısının metin hazırlığı, değişken duraklama, görsel
ağırlıklı senaryo kuralları, yakın kopya ve kesit süzgeçleri, baskı düzeni, bölüm kartı derinliği."""

from pathlib import Path

from PIL import Image, ImageDraw

from otomat.film.anlatim import blok_arasi, fark, soylenis
from otomat.trend import kesik, kurgu, medya, senaryo


def test_birim_kisaltmasi_yaziya_doner_nokta_kalir():
    assert soylenis("He lost 35 lbs.") == "He lost 35 pounds."
    assert soylenis("10 km at 30 mph") == "10 kilometres at 30 miles per hour"
    assert soylenis("the lbs key") == "the lbs key"  # sayıdan sonra değilse dokunmaz
    assert fark("He lost 35 lbs for the role", "He lost 35 pounds for the role") < 0.12


def test_blok_arasi_metne_gore_degisir():
    soru = blok_arasi("Why him?", "Because Amazon wanted it.", 0.38)
    surer = blok_arasi("Then he said:", "and nobody laughed.", 0.38)
    duz = blok_arasi("He signed in March.", "The studio confirmed it.", 0.38)
    assert soru > duz > surer >= 0.12
    assert blok_arasi("a.", "b.", 0.38) == blok_arasi("a.", "b.", 0.38)  # tekrarlanabilir


def test_kalip_ifadeler_yasak():
    for k in ("here's the thing", "hold that thought", "nobody saw it coming", "the real story"):
        assert k in senaryo.YASAK_IFADE
    s = {"tez": "x", "sahneler": [{"tur": "foto", "anlatim": "But here's the thing: it worked.", "gorsel": "G1"}]}
    assert any("yasak ifade" in h for h in senaryo.yapi_kapisi(s, 5))


def test_baslikli_foto_sinirlanir_sayi_ve_bolum_basi_korunur():
    s = [{"tur": "foto", "anlatim": "hook", "gorsel": "G30"},
         {"tur": "bolum", "anlatim": "x", "no": "01", "baslik": "A", "gorsel": "G29"}]  # fmt: skip
    for i in range(9):
        s.append({"tur": "foto", "anlatim": "w " * 10, "gorsel": f"G{i + 1}", "baslik": f"Headline {i}"})
        s.append({"tur": "manset", "anlatim": "w", "mansetler": [], "gorsel": f"G{i + 10}"})
    s[6]["baslik"] = "$3.3B box office"
    s.append({"tur": "kapanis", "anlatim": "end", "metin": "x"})
    d = {"sahneler": s}
    senaryo.yapi_onar(d, gorsel_sayisi=40)
    s = d["sahneler"]
    fotolar = [sh for sh in s if sh["tur"] == "foto"]
    baslikli = [sh for sh in fotolar if sh.get("baslik")]
    assert len(baslikli) <= int(len(fotolar) * senaryo.BASLIKLI_FOTO_PAY)
    assert fotolar[1]["baslik"] == "Headline 0"  # bölüm başındaki ilk fotoğraf
    assert any(sh["baslik"] == "$3.3B box office" for sh in baslikli)  # sayılı başlık


def test_duragan_karttan_donen_foto_basliksiz():
    s = [{"tur": "foto", "anlatim": "w", "gorsel": "G1"}]
    for i in range(6):
        s += [{"tur": "ifade", "anlatim": "w", "metin": f"Big line {i}", "gorsel": f"G{i + 2}"},
              {"tur": "foto", "anlatim": "w", "gorsel": f"G{i + 10}"}]  # fmt: skip
    s.append({"tur": "kapanis", "anlatim": "end", "metin": "x"})
    d = {"sahneler": s}
    senaryo.yapi_onar(d, gorsel_sayisi=40)
    s = d["sahneler"]
    assert sum(1 for sh in s if sh["tur"] in senaryo.STATIK) <= len(s) * senaryo.STATIK_PAY
    donen = [sh for sh in s if sh["tur"] == "foto" and sh.get("gorsel") in {f"G{i + 2}" for i in range(6)}]
    assert donen and all(not sh.get("baslik") for sh in donen)


def _foto(yol: Path, boyut, renk, sekil=True):
    im = Image.new("RGB", boyut, renk)
    if sekil:
        d = ImageDraw.Draw(im)
        d.ellipse((boyut[0] * 0.3, boyut[1] * 0.2, boyut[0] * 0.7, boyut[1] * 0.6), fill=(240, 200, 170))
        d.rectangle((0, 0, boyut[0] * 0.2, boyut[1] * 0.3), fill=(20, 60, 120))
    im.save(yol)
    return yol


def test_yakin_kopya_elenir_buyuk_kalir(tmp_path):
    a = _foto(tmp_path / "pierce-brosnan.jpg", (1200, 1600), (90, 90, 90))
    Image.open(a).crop((0, 0, 1180, 1580)).resize((600, 800)).save(tmp_path / "pierce-brosnan-cropped.jpg")
    c = _foto(tmp_path / "other.jpg", (1600, 1200), (10, 140, 60), sekil=False)
    ImageDraw.Draw(im := Image.open(c)).line((0, 0, 1600, 1200), fill=(255, 255, 0), width=200)
    im.save(c)
    g = [{"yerel": str(tmp_path / "pierce-brosnan-cropped.jpg")}, {"yerel": str(a)}, {"yerel": str(c)}]
    kalan = medya.yakin_kopyalari_ele(g)
    assert [Path(x["yerel"]).name for x in kalan] == ["pierce-brosnan.jpg", "other.jpg"]


def test_dikey_foto_baski_duzeni(tmp_path):
    a = _foto(tmp_path / "portre.jpg", (1000, 1500), (80, 70, 60))
    hedef = medya.hazirla(a, tmp_path / "hazir.jpg")
    im = Image.open(hedef)
    assert im.size == (1920, 1080)
    # baskının beyaz kenarı karede var; dolgu artık ortalanmış bulanık şerit değil
    acik = sum(1 for p in im.convert("L").getdata() if p > 225)
    assert acik > 3000


def test_renk_derecelendirmesi_siyahi_kaldirir_beyazi_yumusatir():
    im = Image.new("RGB", (4, 1))
    im.putdata([(0, 0, 0), (255, 255, 255), (128, 128, 128), (60, 60, 60)])
    r = list(medya.renk(im).getdata())
    assert min(r[0]) >= 8 and max(r[1]) <= 250


def test_kesit_belirginlik(tmp_path):
    tek = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    ImageDraw.Draw(tek).ellipse((50, 30, 150, 190), fill=(200, 150, 120, 255))
    tek.save(tmp_path / "tek.png")
    assert kesik.belirgin(tmp_path / "tek.png")
    parca = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    for x in range(0, 200, 50):
        ImageDraw.Draw(parca).rectangle((x, 60, x + 20, 140), fill=(1, 1, 1, 255))
    parca.save(tmp_path / "parca.png")
    assert not kesik.belirgin(tmp_path / "parca.png")  # kalabalık: parça parça
    bos = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    bos.save(tmp_path / "bos.png")
    assert not kesik.belirgin(tmp_path / "bos.png")


def test_bolum_karti_kesitli_derinlik():
    sh = {"id": "s05", "sure": 3.0, "tur": "bolum", "no": "02", "baslik": "The backlash", "anlatim": "x",
          "kelimeler": [], "gorsel": "assets/img/g03.jpg", "kesit": "assets/kesit/h03.png"}  # fmt: skip
    h = kurgu.sahne_bolum(sh, "kesme", 1)
    assert h.index('class="dev gb"') < h.index("assets/kesit/h03.png")  # numara kesitin arkasında
    assert "SA('.kat')" in h  # fotoğraf ve kesit aynı kamerayla
    duz = kurgu.sahne_bolum({**sh, "kesit": None}, "kesme", 1)
    assert 'class="dev gb"' not in duz


def test_uzun_sahnede_yakin_plan_kesmesi_kelime_basinda():
    kel = [{"w": "a", "s": 1.0, "e": 1.2}, {"w": "b", "s": 3.4, "e": 3.7}, {"w": "c", "s": 4.5, "e": 4.8}]
    sh = {"id": "s09", "sure": 8.0, "gorsel": "assets/img/g01.jpg", "kelimeler": kel}
    assert kurgu.vurus_ani(sh) == 3.4  # ortaya (4,0) en yakın kelime başı, %35-65 aralığında
    h, js = kurgu.zemin(sh, 2)
    assert h.startswith('<div class="cek"') and "tl.set(S('.cek'), {scale:1.16" in js and "3.400" in js
    assert kurgu.vurus_ani({**sh, "sure": 5.0}) is None  # kısa sahne
    assert kurgu.vurus_ani({**sh, "klip": "assets/klip/x.mp4"}) is None  # stok video zaten hareketli


def test_stok_soyut_grafik_etiketleri_elenir():
    from otomat.trend import stok

    hit = {"duration": 20, "videos": {"medium": {"url": "u", "width": 1920}}}
    assert stok.uygun({**hit, "tags": "city, night, traffic"}, 6)
    assert stok.uygun({**hit, "tags": "iconic, bridge"}, 6)  # sözcük sınırı
    assert not stok.uygun({**hit, "tags": "social media, icon, network"}, 6)
    assert not stok.uygun({**hit, "tags": "3d render, abstract"}, 6)
