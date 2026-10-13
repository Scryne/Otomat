"""2026-10-13 ikinci denetimin hikâye hattı bulguları: her test düzeltmeden önceki hatalı davranışı reddeder."""

import dataclasses
import io
import json
import urllib.error

import pytest

from otomat import kanal
from otomat.hikaye import cf, senaryo, uretim


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


def test_olumsuz_kalip_virgulde_biter_pankart_gizlenmez():
    tarif = "A bareheaded man without a hat, holding a protest placard and a newspaper, stands on the steps."
    assert senaryo.yazi_tasiyanlar("A city square.", [tarif]) == [(1, "placard, newspaper")]
    assert senaryo.yazi_tasiyanlar("No signs, no text.", ["A fox without any labels walks."]) == []


def test_kadro_tarifindeki_yazi_tasiyan_nesne_duser(monkeypatch):
    sc = senaryo.Senaryo("T", "m", "A street in 1900.", ["Tom: a newsboy, holding a stack of newspapers"], ["l"],
                         ["Tom shouts on a corner at dawn while people walk by quickly."])  # fmt: skip
    monkeypatch.setattr(cf, "sohbet", lambda *a: pytest.fail("tarifte yazı yoktu, onarım gerekmez"))
    senaryo.gorsel_temizle(sc)
    assert sc.oyuncular == ["Tom: a newsboy."]


def test_giysi_duz_yer_adina_dokunmaz():
    assert senaryo.giysi_duz("A fan in a numbered jersey in New Jersey.") == "A fan in a uniform in New Jersey."
    assert senaryo.giysi_duz("The Jersey Devil flew over the jerseys.") == "The Jersey Devil flew over the uniforms."


def test_hakem_acilis_kalibini_gorur_aralik_disi_satir_duser(monkeypatch):
    istemler = []

    def sohbet(istem, sema):
        istemler.append(istem)
        return {"problems": [{"line": 9, "reason": "yok böyle satır"}, {"line": 2, "reason": "gerçek"}]}

    monkeypatch.setattr(cf, "sohbet", sohbet)
    sorun = senaryo._hakem("tuhaf", "kaynak", "Başlık", ["a b c"] * 7, "sonuc_once")
    assert sorun == [(2, "gerçek")]
    assert senaryo.KALIPLAR["sonuc_once"] in istemler[0] and "do not flag line 1 for following it" in istemler[0]
    senaryo._hakem("masal", "masal", "Başlık", ["a b c"] * 7, "ders")
    assert senaryo.KALIPLAR["ders"] in istemler[1]


def test_masal_istemindeki_ornek_kiyafetsiz():
    """Masal kuralı "kıyafet yok" derken değişim örneği "red scarf"lı tilki veriyordu."""
    assert "scarf" not in senaryo.SAHNE_ISTEMI and "bandage" not in senaryo.SAHNE_ISTEMI


def test_gorme_cevabi_dize_gelirse_dogru_okunur(tmp_path, monkeypatch):
    (tmp_path / "k.jpg").write_bytes(b"x")
    yanitlar = iter([{"answer": "false", "confidence": 0.9}, {"answer": "Yes", "confidence": 80}])

    def istek(*a, **k):
        return {"choices": [{"message": {"content": json.dumps(next(yanitlar))}}]}

    monkeypatch.setattr(cf, "_istek", istek)
    assert cf.gorsel_sor(tmp_path / "k.jpg", "Tail?") == (False, 0.9)  # bool("false") True'ydu
    assert cf.gorsel_sor(tmp_path / "k.jpg", "Tail?") == (True, 0.8)


def _http(kod, govde=b"{}"):
    return urllib.error.HTTPError("u", kod, "x", {}, io.BytesIO(govde))


def test_metin_modelinin_400u_yeniden_denenir_401_denenmez(monkeypatch):
    cagri = []

    def istek(*a, **k):
        cagri.append(1)
        if len(cagri) == 1:
            raise _http(400, b'{"errors":[{"message":"AiError: InferenceUpstreamError"}]}')
        return {"choices": [{"message": {"content": '{"ok": 1}'}}]}

    monkeypatch.setattr(cf, "_istek", istek)
    assert cf.sohbet("x", {}) == {"ok": 1} and len(cagri) == 2
    cagri.clear()
    monkeypatch.setattr(cf, "_istek", lambda *a, **k: cagri.append(1) or (_ for _ in ()).throw(_http(401)))
    with pytest.raises(cf.CFHatasi):
        cf.sohbet("x", {})
    assert len(cagri) == 1


def test_filtre_yumusatmasi_istemde_birikmez(tmp_path, monkeypatch):
    istemler = []

    def istek(yol, govde, tur, *a):
        istemler.append(govde.decode(errors="ignore").split('name="prompt"\r\n\r\n')[1].split("\r\n")[0])
        raise _http(400, b'{"errors":[{"code":3030,"message":"flagged"}]}')

    monkeypatch.setattr(cf, "_istek", istek)
    with pytest.raises(cf.FiltreHatasi):
        cf.gorsel("A storm.", tmp_path / "s.jpg", 1)
    assert istemler[0] == "A storm." and all(i.count("non-graphic") == 1 for i in istemler[1:])


def _sc(**k):
    gorseller = ["Felix sits.", "Felix runs.", "Felix hides.", "Felix sleeps.", "Felix wakes."]
    return senaryo.Senaryo("Bir başlık burada", "grim", "W.", ["Felix: a red fox"], ["l"] * 5, gorseller, **k)


def test_referans_degisimden_sonraki_sahneye_verilmez(kanal_sec, monkeypatch):
    kanal_sec("uzay")
    monkeypatch.setattr(kanal, "aktif", lambda: dataclasses.replace(kanal.yukle("uzay"), referans=True))
    sc = _sc()
    sc.degisimler = [{"kim": "Felix", "sahne": 4, "gorunum": "a tailless red fox", "soru": "Tail?", "beklenen": False}]
    assert uretim.referans_plani(sc) == (0, "Felix", frozenset({1, 2}))  # 3-4 kuyruksuz: kuyruklu kare verilmez


def test_eski_bicimli_senaryo_surdurulmez_eski_mood_muzigi_dusurmez(kanal_sec, tmp_path, monkeypatch):
    """K-24 öncesi Orbit senaryosu (çocuk istemi, mood "playful") artifact'tan dönünce yeniden kullanılıyordu; mood
    kanalda olmadığı için render'dan sonra KeyError bütün koşuyu düşürüyordu."""
    kanal_sec("uzay")
    paket = type("P", (), {"anahtar": "ezop:Fox", "hash": "h", "tur": "masal", "konu": "", "gorsel": {"baslik": "F"}})()
    eski = {"anahtar": "ezop:Fox", "hash": "h", "kalip": "ders", "senaryo": dataclasses.asdict(_sc()), "istemler": []}
    (tmp_path / uretim.SENARYO).write_text(json.dumps(eski), encoding="utf-8")
    (tmp_path / "sahne_0.jpg").write_bytes(b"eski")
    yazilan = []
    monkeypatch.setattr(uretim.kaynaklar, "metin", lambda p: "masal")
    monkeypatch.setattr(senaryo, "yaz", lambda *a: yazilan.append(a) or _sc())
    uretim.senaryo_al(paket, "ders", tmp_path)
    assert yazilan and not (tmp_path / "sahne_0.jpg").exists()  # imzasız kayıt: yeniden yazıldı, eski kare silindi
    yazilan.clear()
    uretim.senaryo_al(paket, "ders", tmp_path)
    assert not yazilan  # aynı imza: sürdürülür
    monkeypatch.setattr(uretim, "MUZIK_DIZIN", tmp_path)
    ilk_mood = next(iter(kanal.aktif().muzik.values()))
    for ad in ilk_mood:  # önbellekte: ağa çıkılmaz
        (tmp_path / f"{ad}.mp3").write_bytes(b"ID3")
    assert uretim.muzik_sec("playful", "t")[1] in ilk_mood
