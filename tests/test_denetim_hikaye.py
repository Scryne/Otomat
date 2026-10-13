"""2026-10-13 tam denetiminin hikâye hattı bulguları: her test düzeltmeden önceki hatalı davranışı reddeder."""

import io
import json
import re
import shutil
import threading
import urllib.error
from pathlib import Path

import pytest
from PIL import Image

from otomat import kanal
from otomat.hikaye import cf, kabul, kaynaklar, senaryo, uretim
from otomat.ses import Parca

REF = Path(__file__).parent / "veri" / "hikaye_ref" / "meta.json"
KUYRUK = {"who": "Felix", "from_scene": 3, "look": "a tailless fox with a round bare rump and a pink bandage",
          "question": "Does the orange fox have a tail?", "expected": False}  # fmt: skip
TAC = {"who": "Felix", "from_scene": 4, "look": "a tailless fox wearing a small golden crown",
       "question": "Does the fox wear a crown?", "expected": True}  # fmt: skip


@pytest.fixture
def kanal_sec(monkeypatch):
    def sec(kimlik):
        monkeypatch.setenv("OTOMAT_KANAL", kimlik)
        kanal._aktif.cache_clear()

    yield sec
    kanal._aktif.cache_clear()


@pytest.fixture(autouse=True)
def uyku_yok(monkeypatch):
    monkeypatch.setattr(cf.time, "sleep", lambda _: None)
    monkeypatch.setattr(kaynaklar.time, "sleep", lambda _: None)


def _paket():
    p = type("P", (), {})()
    p.anahtar, p.hash, p.tur, p.konu, p.kol = "wiki:Tank", "h1", "tuhaf", "konu", "k"
    p.gorsel = {"baslik": "Tank"}
    return p


def _sahte_video(_yol):
    return {"streams": [{"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920},
                        {"codec_type": "audio", "codec_name": "aac"}], "format": {"duration": "37.71"}}  # fmt: skip


def test_cast_nesneden_ad_tarif_dizesine_cevrilir():
    """Earth'te cast "Heraclitus, a Greek man…" geliyordu: `Ad: tarif` ayrılamadı, tarif hiçbir isteme girmedi."""
    ham = [{"name": "Heraclitus", "look": "a Greek man, white beard"}, {"name": "", "look": "x"},
           {"name": "A: B", "look": "red"}, "Ann: a girl"]  # fmt: skip
    assert senaryo.oyuncular(ham) == ["Heraclitus: a Greek man, white beard", "A  B: red", "Ann: a girl"]
    assert senaryo.sema("tuhaf", ["m"])["properties"]["cast"]["items"]["required"] == ["name", "look"]
    oyuncular = senaryo.oyuncular([{"name": "Heraclitus", "look": "a Greek man"}])
    assert "Heraclitus is a Greek man." in uretim.gorsel_istemi("S", "W.", oyuncular, "Heraclitus reads a scroll.")


def test_sayi_kapisi_tam_sayi_ad_kapisi_kelime_basi():
    kaynak = "In 1950 the 25 villagers met Tomlinson on Friday."
    assert senaryo.sayi_ad_kapisi("By 1950, 25 people came.", kaynak) == []
    # "19" ve "5" alt dize olarak "1950" ve "25" içinde geçiyordu
    assert senaryo.sayi_ad_kapisi("Only 19 or 5 came.", kaynak) == ["number not in source: 19",
                                                                    "number not in source: 5"]  # fmt: skip
    assert senaryo.sayi_ad_kapisi("They met on Monday with Tomlinson.", kaynak) == []  # gün adı uydurma ad değil
    assert senaryo.sayi_ad_kapisi("They met Tom.", "see you tomorrow") == ["name not in source: Tom"]
    assert senaryo.sayi_ad_kapisi("It cost 2.3 million.", "it cost 2.3 million") == []


def test_kod_kontrolu_baslik_ve_hakaret():
    satirlar = ["The old brewery tank burst one cold morning there."] * 8
    assert any(n == 0 and "title" in r for n, r in senaryo.kod_kontrolu("masal", "", satirlar, ""))
    assert any(n == 0 and "slur" in r for n, r in senaryo.kod_kontrolu("masal", "The Fox And The Wog", satirlar, ""))
    temiz = senaryo.kod_kontrolu("masal", "The Dyke Builders Of Holland", satirlar, "")
    assert not any("slur" in r for _, r in temiz)  # "dyke" Hollanda seddi: render'dan sonra reddediliyordu


def test_uzun_kaynakta_son_da_modele_gider():
    k = senaryo.kisalt("A" * 7000 + "THE END")
    assert len(k) <= senaryo.KAYNAK_SINIR + 10 and k.endswith("THE END") and k.startswith("AAAA")
    assert senaryo.kisalt("kısa") == "kısa"


def test_wikipedia_gecici_hatayi_yeniden_dener_kalici_hatayi_hikaye_hatasi_saymaz(monkeypatch):
    cagri = []

    def urlopen(istek, timeout):
        cagri.append(1)
        if len(cagri) < 3:
            raise urllib.error.HTTPError(istek.full_url, 503, "x", {}, io.BytesIO())
        govde = {"query": {"pages": [{"extract": "x" * 500 + "\nReferences\nkaynak"}]}}
        return io.BytesIO(json.dumps(govde).encode())

    monkeypatch.setattr(kaynaklar.urllib.request, "urlopen", urlopen)
    assert kaynaklar.metin(_paket()) == "x" * 500 and len(cagri) == 3

    def kopuk(*a, **k):
        raise OSError("ağ yok")

    monkeypatch.setattr(kaynaklar.urllib.request, "urlopen", kopuk)
    with pytest.raises(RuntimeError, match="wikipedia") as e:
        kaynaklar.metin(_paket())
    assert not isinstance(e.value, kaynaklar.KaynakHatasi)  # kesinti denenen hikâyeleri havuzdan düşürmez
    assert re.split(kaynaklar.BITIS, "metin\nBibliography\nkitaplar")[0] == "metin"


def test_cf_kalici_hatayi_denemez_kopan_baglantiyi_dener_guveni_olcekler(monkeypatch, tmp_path):
    cagri = []

    def yetkisiz(*a, **k):
        cagri.append(1)
        raise urllib.error.HTTPError("u", 401, "x", {}, io.BytesIO(b"auth"))

    monkeypatch.setattr(cf, "_istek", yetkisiz)
    with pytest.raises(cf.CFHatasi):
        cf.sohbet("x", {})
    assert len(cagri) == 1  # 401 yeniden denenmez

    sira = iter([ConnectionResetError("kopuk"), {"choices": [{"message": {"content": '{"a": 1}'}}],
                                                  "usage": {"neurons": 7}}])  # fmt: skip

    def kopuk(*a, **k):
        x = next(sira)
        if isinstance(x, Exception):
            raise x
        return x

    monkeypatch.setattr(cf, "_istek", kopuk)
    cf.NEURON["toplam"] = 0
    assert cf.sohbet("x", {}) == {"a": 1} and cf.NEURON["toplam"] == 7  # eskiden yakalanmadan çöküyordu

    resim = tmp_path / "k.jpg"
    resim.write_bytes(b"x")
    yanit = {"choices": [{"message": {"content": '{"answer": true, "confidence": 85}'}}]}
    monkeypatch.setattr(cf, "_istek", lambda *a, **k: yanit)
    assert cf.gorsel_sor(resim, "?") == (True, 0.85)  # yüzde dönen güven eşiği hep geçiyordu


def test_gorsel_referansla_cok_parcali_istek(monkeypatch, tmp_path):
    ref = tmp_path / "ref.jpg"
    Image.new("RGB", (768, 1344), "red").save(ref)
    giden = {}

    def istek(yol, govde, tur, *a):
        giden["govde"] = govde
        return {"result": {"image": "eHl6"}}

    monkeypatch.setattr(cf, "_istek", istek)
    cf.NEURON["toplam"] = 0
    cf.gorsel("istem", tmp_path / "s.jpg", 1, referanslar=(ref,))
    assert b'name="input_image_0"' in giden["govde"] and b'name="prompt"' in giden["govde"]
    assert cf.NEURON["toplam"] == pytest.approx(cf.GORSEL_NEURON + cf.REFERANS_NEURON)
    with Image.open(io.BytesIO(cf._referans_baytlari(ref))) as k:
        assert max(k.size) < 512  # klein girdi sınırı


def test_sahne_cizimi_kotada_kuyruktakileri_iptal_eder(tmp_path, monkeypatch):
    baslayan, kapi = [], threading.Event()

    def gorsel(istem, yol, tohum):
        baslayan.append(istem)
        if istem == "0":
            raise cf.KotaHatasi("kota")
        kapi.wait(2)
        return yol

    monkeypatch.setattr(cf, "gorsel", gorsel)
    monkeypatch.setattr(uretim, "PARALEL", 1)
    with pytest.raises(cf.KotaHatasi):
        uretim.sahneleri_ciz([str(i) for i in range(6)], tmp_path, 0)
    assert baslayan == ["0"]  # ex.map kalan 5 isteği yine gönderiyordu


def test_durum_yeniden_cizimi_yazisiz_ister_sonraki_degisimin_penceresine_tasmaz(tmp_path, monkeypatch):
    gorseller = ["Felix smiling.", "Felix caught.", "Felix on a log.", "Felix crowned.", "Felix ruling."]
    sc = senaryo.Senaryo("T", "m", "A forest.", ["Felix: a fox"], ["l"] * 5, gorseller)
    sc.degisimler = senaryo.degisimler([KUYRUK, TAC], sc.oyuncular, 5)
    for i in range(5):
        (tmp_path / f"sahne_{i}.jpg").write_bytes(b"eski")
    sorulan, istenen = [], []

    def sor(yol, soru):
        sorulan.append((yol.name, "kuyruk" if "tail" in soru else "tac"))
        if "tail" in soru:  # 1 (sınama) kuyruklu, doğru; 2 eskiden kuyruklu çizilmiş
            return yol.name == "sahne_1.jpg" or yol.read_bytes() == b"eski", 0.9
        return yol.name in ("sahne_3.jpg", "sahne_4.jpg"), 0.9

    def gorsel(istem, yol, tohum):
        istenen.append(istem)
        yol.write_bytes(b"yeni")
        return yol

    monkeypatch.setattr(cf, "gorsel_sor", sor)
    monkeypatch.setattr(cf, "gorsel", gorsel)
    k = uretim.durumlari_denetle(sc, [f"istem {i}" for i in range(5)], tmp_path, 0)
    # kuyruk sorusu 3-4'e sorulmaz (orası tacın penceresi; eskiden ikisinde de soruluyordu)
    assert sorulan == [("sahne_1.jpg", "kuyruk"), ("sahne_2.jpg", "kuyruk"), ("sahne_2.jpg", "kuyruk"),
                       ("sahne_2.jpg", "tac"), ("sahne_3.jpg", "tac"), ("sahne_4.jpg", "tac")]  # fmt: skip
    assert k["yeniden"] == 1 and k["tutmayan"] == {} and istenen == [f"istem 2 {uretim.YAZISIZ}"]


def test_render_hatasinda_ffmpeg_kapanir_yarim_dosya_kalmaz(kanal_sec, tmp_path):
    kanal_sec("earth")
    bozuk = tmp_path / "bozuk.jpg"
    bozuk.write_bytes(b"resim degil")
    cikti = tmp_path / "v.mp4"
    with pytest.raises(OSError):  # PIL.UnidentifiedImageError
        uretim.render([bozuk], [Parca(0.0, 1.0, "One two three")], 1.2, cikti)
    assert not cikti.exists()


def test_kabul_kaynak_atfi_aciklamada_hakaret_sembol_gorunus(kanal_sec, tmp_path):
    kanal_sec("earth")
    meta = json.loads(REF.read_text(encoding="utf-8"))
    shutil.copy(REF, tmp_path / "meta.json")
    (tmp_path / "video.mp4").write_bytes(b"\0" * 300_000)
    for i in range(len(meta["cumleler"])):
        (tmp_path / f"sahne_{i}.jpg").write_bytes(b"x")

    def bozuk(**degisim):
        (tmp_path / "meta.json").write_text(json.dumps({**meta, **degisim}), encoding="utf-8")
        return kabul.denetle(tmp_path / "meta.json", _sahte_video)

    assert bozuk() == []
    wiki_yok = meta["aciklama"].replace("https://en.wikipedia.org/wiki/Great_Molasses_Flood", "")
    assert any("kaynak atfı" in h for h in bozuk(aciklama=wiki_yok))  # müzik atfının https'i yetiyordu
    assert any("hakaret" in h for h in bozuk(etiketler=["history", "wogs"]))
    assert any("sembol" in h for h in bozuk(cumleler=[*meta["cumleler"][:-1], "It moved at 35 mph that day."]))
    assert any("görünüş" in h for h in bozuk(durum={"tutmayan": {"2": "tail?"}}))
