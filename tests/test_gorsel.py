from pathlib import Path

from otomat.gorsel import sirali_cubuk
from otomat.gorsel.kimlik import renk


def test_sirali_cubuk_degeri_buyurken_taraf_degistirmez(monkeypatch):
    """1. sıranın değeri büyürken dışarıdan içeri zıplıyordu.

    10-05 karelerinde 25.6 dışta, iki kare sonra 31.4 içteydi.
    """
    yakalanan = {}

    def calistir(self, cikti, guncelle):
        yakalanan["sahne"], yakalanan["guncelle"] = self, guncelle
        return cikti

    monkeypatch.setattr(sirali_cubuk.Sahne, "calistir", calistir)
    ogeler = [{"etiket": f"Ülke {i}", "deger": v} for i, v in enumerate([34.5, 8.8, 8.0, 5.1, 3.2], 1)]
    sirali_cubuk.ciz(ogeler, "Test", "Test", Path("yok.mp4"), ondalik=1, saniye=10)
    ax = yakalanan["sahne"].fig.axes[0]
    birinci = [t for t in ax.texts if t.get_va() == "center_baseline"][0]  # değer metinleri satır sırasıyla

    taraflar, gorunen = set(), []
    for k in range(300):
        yakalanan["guncelle"](k / 30)
        taraflar.add((birinci.get_ha(), birinci.get_color()))
        if birinci.get_visible():
            gorunen.append(birinci.get_text())
    assert taraflar == {("right", renk("surface"))}
    assert gorunen[-1] == "34.5"
    assert len(set(gorunen)) > 3  # sayaç hâlâ sayıyor, yalnız son değer görünmüyor
