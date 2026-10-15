"""Kart biçimi (K-25, 2026-10-14): Earth'ün sahneli anlatımı 3-81 izlenmede kaldı; nişte tutarlı izlenen kanallar
hikâyeyi anlatıcısız tek ekran paragrafla ve konunun gerçek görseliyle veriyor."""

import json
import subprocess

import imageio_ffmpeg
import numpy as np
import pytest
from PIL import Image
from test_hikaye_uctan_uca import _lufs, _muzik, _paket

from otomat import kanal
from otomat.hikaye import cf, kabul, kart, kaynaklar, senaryo, yazi

KAYNAK = (
    "The Great Molasses Flood occurred on January 15, 1919, in the North End of Boston. A storage tank burst and a "
    "wave of molasses up to 25 feet high rushed through the streets at 35 miles per hour, killing 21 people. "
    "Residents claimed that on hot days the area still smelled of molasses for decades."
)
IYI = {
    "title": "Boston's 1919 Wave of Molasses",
    "hook": "A deadly wave of molasses",
    "sentences": [
        "On January 15, 1919, a storage tank in [[Boston's North End]] burst open.",
        "A wave of molasses up to [[25 feet high]] rushed through the streets at about [[35 miles per hour]].",
        "It crushed buildings and trapped people and horses in the sticky flood.",
        "[[21 people died]], and residents said the area smelled of molasses for decades.",
    ],
    "image": "A flooded Boston street in 1919 covered in dark syrup, rescuers wading through it.",
    "mood": "tragic",
}


@pytest.fixture
def earth(monkeypatch):
    monkeypatch.setenv("OTOMAT_KANAL", "earth")
    kanal._aktif.cache_clear()
    assert kanal.aktif().bicim == "kart"
    yield kanal.aktif()
    kanal._aktif.cache_clear()


def _kart(**degis) -> kart.Kart:
    d = {**IYI, **degis}
    return kart.Kart(d["title"], d["hook"], list(d["sentences"]), d["image"], d["mood"])


def test_kelimeler_vurgu_rengi_sirayla_noktalama_yapisir():
    k = kart.kelimeler(["A [[huge tank]] burst.", "[[21 people died]] , and it [[smelled]]."])
    assert k[1:3] == [("huge", 0), ("tank", 0)]
    assert ("died,", 1) in k and ("smelled.", 2) in k and (".", -1) not in k and (",", -1) not in k


def test_kod_kontrolu_temiz_kart_gecer_yil_sayi_sayilmaz():
    assert kart.kod_kontrolu(_kart(), KAYNAK) == []


@pytest.mark.parametrize(
    "degis,beklenen",
    [
        ({"sentences": [*IYI["sentences"][:3], "[[22 people died]] that day in the sticky flood."]}, "number not in"),
        ({"sentences": [s.replace("[[", "").replace("]]", "") for s in IYI["sentences"]]}, "mark 3-5"),
        ({"sentences": IYI["sentences"][:2]}, "words; it must be"),
        ({"hook": "Molasses"}, "headline must be"),
        ({"sentences": [IYI["sentences"][0] + " [[25 feet high]] 25 feet 35 miles 21 people", *IYI["sentences"][1:]]},
         "numbers; keep at most"),
        ({"sentences": ["On January 15, 1919, a [[storage tank in Boston's North End burst open]].",
                        *IYI["sentences"][1:]]}, "marked phrase is too long"),
    ],
)  # fmt: skip
def test_kod_kontrolu_kusurlu_karti_isaretler(degis, beklenen):
    assert any(beklenen in r for _, r in kart.kod_kontrolu(_kart(**degis), KAYNAK))


def test_yaz_yalniz_isaretli_satiri_onarir_sonra_hakem(monkeypatch):
    uydurma = {**IYI, "sentences": [*IYI["sentences"][:3], "[[22 people died]], and the area smelled for decades."]}
    istemler = []

    def sohbet(istem, sema, deneme=3):
        istemler.append(istem)
        if "hook" in sema["properties"]:
            return uydurma
        if "fixes" in sema["properties"]:
            assert "line 5: number not in source: 22" in istem
            return {"fixes": [{"line": 5, "text": IYI["sentences"][3]}]}
        return {"problems": []}

    monkeypatch.setattr(cf, "sohbet", sohbet)
    k = kart.yaz("Great Molasses Flood", KAYNAK, "a flood", "sonuc_once", ["tragic"])
    assert k.cumleler == IYI["sentences"] and k.turlar[-1] == [] and len(k.turlar) == 2
    # kod kapısı sorunluyken hakem çağrılmaz (kota); kapı temizlenince bir hakem turu
    assert sum("strict fact checker" in i for i in istemler) == 1
    assert "line 1 is a short headline" in istemler[-1]


def test_yaz_dort_turda_temizlenmezse_senaryo_hatasi(monkeypatch):
    def sohbet(istem, sema, deneme=3):
        if "hook" in sema["properties"]:
            return IYI
        if "fixes" in sema["properties"]:
            return {"fixes": []}
        return {"problems": [{"line": 3, "reason": "the source does not say horses were trapped"}]}

    monkeypatch.setattr(cf, "sohbet", sohbet)
    with pytest.raises(senaryo.SenaryoHatasi) as e:
        kart.yaz("Great Molasses Flood", KAYNAK, "a flood", "sonuc_once", ["tragic"])
    assert len(e.value.sorunlar) == senaryo.TUR_SAYISI


def _commons(lisans="Public domain", mime="image/jpeg", w=1260, h=927, nonfree=None, artist="Unknown author"):
    em = {"LicenseShortName": {"value": lisans}, "Artist": {"value": f"<span>{artist}</span>"}}
    if nonfree:
        em["NonFree"] = {"value": "true"}
    return {"query": {"pages": [{"imageinfo": [{"url": "https://u/x.jpg", "thumburl": "https://u/t.jpg", "width": w,
                                                "height": h, "mime": mime, "descriptionurl": "https://c/File:x",
                                                "extmetadata": em}]}]}}  # fmt: skip


@pytest.mark.parametrize(
    "commons,kabul_mu",
    [
        (_commons(), True),
        (_commons(lisans="CC BY-SA 4.0", artist="Jane Roe"), True),
        (_commons(lisans="Fair use"), False),
        (_commons(lisans="CC BY-SA 4.0", nonfree=True), False),
        (_commons(mime="image/svg+xml"), False),
        (_commons(w=300, h=280), False),
        (_commons(w=3000, h=500), False),
    ],
)
def test_wiki_gorseli_lisans_bicim_boyut_suzgeci(monkeypatch, commons, kabul_mu):
    def api(url, params):
        if url == kaynaklar.WIKI_API:
            return {"query": {"pages": [{"pageimage": "X.jpg"}]}}
        return commons

    monkeypatch.setattr(kart, "_api", api)
    g = kart.wiki_gorseli("Dancing plague of 1518")
    assert (g is not None) is kabul_mu
    if g:
        assert g["url"] == "https://u/t.jpg" and g["yazar"] in ("", "Jane Roe")


def test_bilinmeyen_yazar_bos_atif_lisansla_kalir():
    em = {"Artist": {"value": '<span class="x">Unknown author</span><span style="display:none">Unknown author</span>'}}
    assert kart._yazar(em) == ""
    g = {"kaynak": "wikimedia", "yazar": "", "lisans": "Public domain"}
    assert kart.atif_satiri(g) == "Image: Public domain · Wikimedia Commons"


def _dokulu(yol, tohum=1, w=1260, h=927):
    rng = np.random.default_rng(tohum)
    a = rng.integers(40, 200, size=(h // 16 + 1, w // 16 + 1, 3), dtype=np.uint8)
    Image.fromarray(a).resize((w, h), Image.NEAREST).save(yol, quality=90)


def test_belge_gorseli_ai_illustrasyona_duser(tmp_path, monkeypatch, earth):
    """Tarrare'nin ana görseli Fransızca bir belge sayfası (10-14 denemesi): OCR'da harf yığını → AI illüstrasyonu."""
    monkeypatch.setattr(kart, "wiki_gorseli", lambda b: {"url": "u", "sayfa": "s", "lisans": "Public domain",
                                                         "yazar": "", "dosya": "M.jpg"})  # fmt: skip
    monkeypatch.setattr(kart, "_indir", lambda url, yol: _dokulu(yol))
    monkeypatch.setattr(yazi, "oku", lambda yol: ["MEMOIRE SUR LA POLYPHAGIE", "On connait l'histoire ou plutot"]
                        if not cizilen else [])  # fmt: skip
    cizilen = []

    def gorsel(istem, yol, tohum, **_):
        cizilen.append(istem)
        _dokulu(yol, tohum, 768, 1344)
        return yol

    monkeypatch.setattr(cf, "gorsel", gorsel)
    g = kart.gorsel_al(_paket(), _kart(), tmp_path, 5)
    assert g["kaynak"] == "ai" and g["wiki"] == "yazı ağırlıklı (belge)" and g["yeniden"] == 0
    assert cizilen[0].startswith(earth.stil) and IYI["image"] in cizilen[0] and "no panels" in cizilen[0]


def test_wiki_gorseli_yazisizsa_kullanilir_ai_cagrilmaz(tmp_path, monkeypatch, earth):
    w = {"url": "u", "sayfa": "https://c/File:x", "lisans": "Public domain", "yazar": "BPL", "dosya": "x.jpg"}
    monkeypatch.setattr(kart, "wiki_gorseli", lambda b: w)
    monkeypatch.setattr(kart, "_indir", lambda url, yol: _dokulu(yol))
    monkeypatch.setattr(yazi, "oku", lambda yol: ["BPL"])  # köşedeki kısa damga belge değil
    monkeypatch.setattr(cf, "gorsel", lambda *a, **k: pytest.fail("Wikimedia görseli varken AI çizildi"))
    assert kart.gorsel_al(_paket(), _kart(), tmp_path, 5) == {"kaynak": "wikimedia", **w}


def test_kart_uret_gercek_render_kabulden_gecer_dongu_sicramaz(tmp_path, monkeypatch, earth):
    monkeypatch.setattr(kaynaklar, "metin", lambda p: KAYNAK)
    monkeypatch.setattr(cf, "sohbet", lambda istem, sema, deneme=3: IYI if "hook" in sema["properties"]
                        else {"problems": []})  # fmt: skip
    w = {"url": "u", "sayfa": "https://c/File:x", "lisans": "Public domain", "yazar": "BPL", "dosya": "x.jpg"}
    monkeypatch.setattr(kart, "wiki_gorseli", lambda b: w)
    monkeypatch.setattr(kart, "_indir", lambda url, yol: _dokulu(yol))
    monkeypatch.setattr(yazi, "oku", lambda yol: [])
    muzik = _muzik(tmp_path)
    from otomat.hikaye import uretim

    monkeypatch.setattr(uretim, "muzik_sec", lambda mood, tohum: (muzik, "Heartbreaking"))
    monkeypatch.setattr(kart, "FPS", 6)  # kabul boyut ve süreye bakar
    dizin = tmp_path / "u"
    (dizin / "sahne_3.jpg").parent.mkdir()
    (dizin / "sahne_3.jpg").write_bytes(b"onceki deneme")  # aynı slotun eski sahne çıktısı temizlenir

    meta = uretim.uret(_paket(), "sonuc_once", "illustrasyon", dizin, "2026-10-14")

    assert kabul.denetle(dizin / "meta.json") == []
    assert meta["bicim"] == "kart" and meta["altyazi"] == [] and meta["kanca"] == "A deadly wave of molasses"
    assert meta["cumleler"][0] == "On January 15, 1919, a storage tank in Boston's North End burst open."
    assert "Image: BPL, Public domain, via Wikimedia Commons https://c/File:x" in meta["aciklama"]
    assert meta["aciklama"].startswith("On January 15, 1919") and "[[" not in meta["aciklama"]
    assert sorted(p.name for p in dizin.glob("sahne_*")) == ["sahne_0.jpg"]
    assert -18.5 <= _lufs(dizin / "video.mp4") <= -14
    # cos zoom: ilk ve son kare neredeyse aynı (Shorts döngüsünde sıçrama yok)
    kareler = _kareler(dizin / "video.mp4")
    assert np.abs(kareler[0].astype(int) - kareler[-1].astype(int)).mean() < 4
    assert np.abs(kareler[0].astype(int) - kareler[len(kareler) // 2].astype(int)).mean() > 4


def _kareler(video):
    ham = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(video), "-vf", "scale=108:192", "-f", "rawvideo",
         "-pix_fmt", "gray", "-"],
        capture_output=True,
        check=True,
    ).stdout  # fmt: skip
    return np.frombuffer(ham, np.uint8).reshape(-1, 192, 108)


def test_kabul_kart_wikimedia_atfi_yoksa_ve_cumle_azsa_reddeder(tmp_path, earth):
    meta = {
        "bicim": "kart", "baslik": "Boston's 1919 Wave of Molasses", "kanca": "A deadly wave of molasses",
        "cumleler": ["A tank burst in Boston one cold day.", "Molasses flooded the narrow streets."],
        "aciklama": "x\n\nSource: Wikipedia https://en.wikipedia.org/wiki/X\nMusic: Kevin MacLeod "
                    "https://creativecommons.org/licenses/by/4.0/",
        "etiketler": ["history"], "mfk": False, "paket": {"anahtar": "wiki:X"},
        "senaryo": {"hakem_turlari": [[]]}, "kart": {"gorsel": {"kaynak": "wikimedia", "lisans": "CC BY-SA 4.0"}},
        "sure_sn": 8.0,
    }  # fmt: skip
    (tmp_path / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    h = kabul.denetle(tmp_path / "meta.json")
    assert any("2 cümle" in x for x in h) and any("lisans atfı yok" in x for x in h)
    assert any("kart görseli yok" in x for x in h) and any("video.mp4" in x for x in h)


def test_hazirla_altyazisiz_kartta_srt_yazmaz_basligi_cevirir(tmp_path, monkeypatch, earth):
    from otomat.yayin import ceviri, hazirla

    meta = {"baslik": "B", "aciklama": "Paragraf.\n\nSource: x", "altyazi": []}
    (tmp_path / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    cagri = []

    def cevir(dil, baslik, aciklama, altyazilar, tohum=0):
        cagri.append(altyazilar)
        return {"title": f"B-{dil}", "description": f"P-{dil}", "captions": []}

    monkeypatch.setattr(ceviri, "cevir", cevir)
    s = hazirla.hazirla(tmp_path)
    assert set(s["yerel"]) == set(earth.diller) and not list(tmp_path.glob("*.srt")) and cagri[0] == []
    # aynı metin ikinci kez: srt yok diye yeniden çevrilmez (kota)
    hazirla.hazirla(tmp_path)
    assert len(cagri) == len(earth.diller)


def test_cevir_altyazisiz_kartta_gercek_ceviriyi_kabul_eder(monkeypatch, earth):
    # 10-17 kartı: altyazı listesi boş, "çevrilmemiş çıktı" kontrolü [] == [] ile her çeviriyi reddediyordu
    from otomat.yayin import ceviri

    istemler = []

    def uret(istem, sema, tohum):
        istemler.append(istem)
        return {"title": "Botín antiguo de 1.6 millones", "description": "Pagó 1.6 millones en 2010.", "captions": []}

    monkeypatch.setattr(ceviri, "_uret", uret)
    s = ceviri.cevir("es", "Ancient Loot for $1.6M", "It paid $1.6 million in 2010.\n\nSource: x", [])
    assert s and s["title"].startswith("Botín") and s["description"].endswith("Source: x")
    assert "SENTENCES" not in istemler[0]
    # aynen dönen metin yine reddedilir
    monkeypatch.setattr(ceviri, "_uret", lambda i, s, t: {"title": "Ancient Loot for $1.6M",
                                                          "description": "It paid $1.6 million in 2010.",
                                                          "captions": []})  # fmt: skip
    assert ceviri.cevir("es", "Ancient Loot for $1.6M", "It paid $1.6 million in 2010.\n\nSource: x", []) is None


def test_isaret_ici_bosluk_duz_metne_cift_bosluk_birakmaz():
    c = kart.isaret_duzelt("In 2010 it bought [[ $1.6 million]] of items, a [[ $3 million fine ]].")
    assert c == "In 2010 it bought [[$1.6 million]] of items, a [[$3 million fine]]."
    assert "  " not in kart.duz(c) and kart.duz(c).endswith("fine.")
