"""Hikâye videosunun uçtan uca üretimi: `uretim.uret` gerçek render (Ken Burns + yakılmış altyazı), gerçek ffmpeg
karışımı (anlatıcı/müzik loudness) ve gerçek yayın kabulüyle. Yalnız dış servisler sahte: senaryo modeli, sahne
görselleri (Cloudflare), OCR, Kokoro ve Whisper. Önceden `uret` hiçbir testte koşmuyordu; `meta.json` sözleşmesi
(kabul, hazır üretim, yayın hepsi onu okur) elle yazılmış sözlüklerle sınanıyordu (2026-10-13 ikinci denetim)."""

import json
import re
import subprocess
import wave

import imageio_ffmpeg
import numpy as np
import pytest
from PIL import Image

from otomat import kanal
from otomat.hikaye import cf, hizala, kabul, kaynaklar, senaryo, uretim, yazi
from otomat.ses import Parca
from otomat.veri import Kaynak, OlguPaketi

SATIRLAR = [
    "In 1919 a wave of molasses swept through Boston.",
    "A huge storage tank on Commercial Street burst open.",
    "The sticky flood rolled down the narrow streets.",
    "Horses and carts were caught in the brown tide.",
    "Rescuers waded in to pull people from the syrup.",
    "The harbor stayed brown for months after the disaster.",
    "People said the street smelled sweet for decades.",
]


@pytest.fixture
def earth(monkeypatch):
    monkeypatch.setenv("OTOMAT_KANAL", "earth")
    kanal._aktif.cache_clear()
    yield kanal.aktif()
    kanal._aktif.cache_clear()


def _paket() -> OlguPaketi:
    return OlguPaketi(
        kol="tuhaf",
        tur="tuhaf",
        anahtar="wiki:Great Molasses Flood",
        konu="a flood of molasses in Boston",
        olgular={},
        gorsel={"sablon": "illustrasyon", "baslik": "Great Molasses Flood"},
        kaynak=Kaynak("Wikipedia", "https://en.wikipedia.org/wiki/Great_Molasses_Flood", "CC BY-SA 4.0", "2026-10-13"),
        etiketler=["true story", "history"],
    )


def _senaryo(*_):
    return senaryo.Senaryo(
        baslik="The day Boston drowned in molasses",
        mood="mysterious",
        dunya="Boston harbor, 1919.",
        oyuncular=["Rescuer: a tall man in a wool coat"],
        satirlar=SATIRLAR,
        gorseller=[f"Scene {i}: a narrow Boston street flooded with brown syrup, the Rescuer wading" for i in range(7)],
        turlar=[[]],
    )


def _gorsel(istem, yol, tohum, **_):
    """Kâğıt kenarı kırpmasına takılmayan, kareden kareye farklı renkli 768×1344 görsel."""
    rng = np.random.default_rng(tohum)
    a = rng.integers(40, 200, size=(1344 // 16, 768 // 16, 3), dtype=np.uint8)
    Image.fromarray(a).resize((768, 1344), Image.NEAREST).save(yol, quality=90)
    cf.NEURON["toplam"] += 156
    return yol


def _seslendir(satirlar, cikti):
    """Satır başına 3 sn sinüs (Kokoro'nun 24 kHz mono biçimi) ve gerçek akıştaki gibi ara/kuyruk sessizliği."""
    sr, an, parcalar, sesler = 24000, 0.0, [], []
    for i, s in enumerate(satirlar):
        t = np.arange(int(3.0 * sr)) / sr
        sesler.append(0.3 * np.sin(2 * np.pi * (180 + 20 * i) * t))
        parcalar.append(Parca(round(an, 3), round(an + 3.0, 3), s))
        ara = uretim.ARA if i < len(satirlar) - 1 else uretim.KUYRUK
        sesler.append(np.zeros(int(ara * sr)))
        an += 3.0 + ara
    tum = np.concatenate(sesler)
    with wave.open(str(cikti), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((tum * 32767).astype(np.int16).tobytes())
    return len(tum) / sr, parcalar


def _muzik(tmp_path):
    yol = tmp_path / "muzik.wav"
    subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi", "-i", "sine=f=440:d=8", str(yol)],
        check=True,
    )
    return yol


def _lufs(video) -> float:
    cikti = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(video), "-af", "ebur128", "-f", "null", "-"],
        capture_output=True,
        text=True,
    ).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", cikti)[-1])


def test_uret_gercek_render_ve_karisimla_kabulden_gecer(tmp_path, monkeypatch, earth):
    monkeypatch.setattr(uretim, "FPS", 4)  # 24 sn × 4 kare: kabul boyut ve süreye bakar, kare hızına değil
    monkeypatch.setattr(kaynaklar, "metin", lambda p: "The Great Molasses Flood happened in Boston in 1919.")
    monkeypatch.setattr(senaryo, "yaz", _senaryo)
    monkeypatch.setattr(cf, "gorsel", _gorsel)
    monkeypatch.setattr(yazi, "oku", lambda yol: [])
    monkeypatch.setattr(uretim, "seslendir", _seslendir)
    monkeypatch.setattr(hizala, "whisper_kelimeleri", lambda wav: (_ for _ in ()).throw(RuntimeError("model yok")))
    muzik = _muzik(tmp_path)
    monkeypatch.setattr(uretim, "muzik_sec", lambda mood, tohum: (muzik, "Investigations"))

    dizin = tmp_path / "uretim"
    meta = uretim.uret(_paket(), "sonuc_once", "illustrasyon", dizin, "2026-10-14")

    assert kabul.denetle(dizin / "meta.json") == []
    assert json.loads((dizin / "meta.json").read_text(encoding="utf-8")) == meta
    assert meta["cumleler"] == SATIRLAR and meta["kanca"] == SATIRLAR[0]
    assert meta["vurgu"] == "orantili"  # Whisper düşünce video yine çıkar
    assert meta["neuron"] == 7 * 156 and meta["mfk"] is False
    assert "wikipedia.org/wiki/Great_Molasses_Flood" in meta["aciklama"] and "Investigations" in meta["aciklama"]
    assert sorted(p.name for p in dizin.glob("sahne_*.jpg")) == [f"sahne_{i}.jpg" for i in range(7)]
    assert not (dizin / "sessiz.mp4").exists()
    # hazır/yarım üretim senaryoyu buradan sürdürür (kota ikinci kez harcanmaz)
    kayit = json.loads((dizin / uretim.SENARYO).read_text(encoding="utf-8"))
    assert (kayit["anahtar"], kayit["senaryo"]["satirlar"]) == ("wiki:Great Molasses Flood", SATIRLAR)
    # anlatıcı -14, müzik -30 LUFS'a ayrı çekilir; karışım YouTube'un oynatma hedefine yakın (sessiz video yükseltilmez)
    assert -16.5 <= _lufs(dizin / "video.mp4") <= -12.5


def test_uret_ikinci_kez_senaryo_ve_gorselleri_yeniden_kullanir(tmp_path, monkeypatch, earth):
    """Kota kesintisinden sonra aynı paket: senaryo yeniden yazılmaz, biten sahneler yeniden çizilmez."""
    monkeypatch.setattr(uretim, "FPS", 3)
    monkeypatch.setattr(kaynaklar, "metin", lambda p: "kaynak")
    yazilan, cizilen = [], []
    monkeypatch.setattr(senaryo, "yaz", lambda *a: yazilan.append(1) or _senaryo())

    def gorsel(istem, yol, tohum, **k):
        cizilen.append(yol.name)
        return _gorsel(istem, yol, tohum)

    monkeypatch.setattr(cf, "gorsel", gorsel)
    monkeypatch.setattr(yazi, "oku", lambda yol: [])
    monkeypatch.setattr(uretim, "seslendir", _seslendir)
    monkeypatch.setattr(hizala, "whisper_kelimeleri", lambda wav: None)
    muzik = _muzik(tmp_path)
    monkeypatch.setattr(uretim, "muzik_sec", lambda mood, tohum: (muzik, "Investigations"))
    dizin = tmp_path / "u"
    uretim.uret(_paket(), "sonuc_once", "illustrasyon", dizin, "t")
    (dizin / "sahne_3.jpg").unlink()  # kotaya takılıp yarım kalan sahne
    cizilen.clear()

    # gerçek cf.gorsel "varsa üretme" der; sahte de öyle davransın
    monkeypatch.setattr(cf, "gorsel", lambda i, yol, t, **k: yol if yol.exists() else gorsel(i, yol, t))
    uretim.uret(_paket(), "sonuc_once", "illustrasyon", dizin, "t")
    assert yazilan == [1] and cizilen == ["sahne_3.jpg"]
    assert kabul.denetle(dizin / "meta.json") == []
