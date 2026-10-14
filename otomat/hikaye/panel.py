"""Sahne görselinde panel (çizgi roman sayfası) denetimi. klein istemdeki "not a comic, no panels" cümlesine rağmen
ara sıra kareyi ara boşluklu 2-4 panele bölüyor: Ganesha (10-16, "three separate temples" tarifi), Mónica Macías
(10-13, yayında), Molasses (10-08) ve Curse of the Colonel. Son üçünün tarifi tek mekânlı, hepsi son sahne ve zaman
sıçraması ("now an adult", "Modern summer street"): dünya cümlesi eski dönemi söylerken sahne bugünü istiyor.

Ölçüm (2026-10-14, 164 benzersiz sahne, 26 hikâye; gözle etiketlendi, 4 panelli): panel ara boşluğu kenar kırpıldıktan
sonra iç bölgede (%8-92) kare boyunca uzanan düz bir bant, iki yanında resim var. Bant: pikselleri satır medyanına
yakın (±18) satırların ≥ %95'i; bantın hemen üstündeki ve altındaki 4 satırın düzlük oranlarının ortalaması < 0,7.
Panelli 4 karenin 4'ü yakalanıyor (ortalama 0,32-0,55); panelsiz 160 karede yanlış alarm 0 (gökyüzü, duvar ve
zemin bantlarının en düşük ortalaması 0,80: iki yanından biri de düz). CPU'da kare başına ~10 ms, neuron harcamaz.
"""

from pathlib import Path

import numpy as np
from PIL import Image

GENISLIK = 256
TOLERANS = 18  # satır medyanından bu kadar uzak piksel "düz değil"
DUZ = 0.95  # satırın bu oranı medyana yakınsa satır düz
IC = (0.08, 0.92)  # kenar kırpmasından kalan çerçeve çizgileri sayılmasın
KOMSU = 4
ESIK = 0.7  # bantın iki yanındaki satırların düzlük ortalaması bundan azsa iki yanda resim var: panel ara boşluğu
KALINLIK = 0.06  # bundan kalın düz bant ara boşluk değil, gökyüzü ya da duvar


def _duzluk(a: np.ndarray) -> np.ndarray:
    return (np.abs(a - np.median(a, axis=1, keepdims=True)) < TOLERANS).mean(axis=1)


def bantlar(a: np.ndarray) -> list[tuple[float, float]]:
    """(konum oranı, komşu düzlüğü): satırlar boyunca uzanan iç düz bantlar. `a` gri tonlu dizi, satır = bir çizgi."""
    duzluk = _duzluk(a)
    duz = duzluk >= DUZ
    h, bulgu, y = len(duz), [], 0
    while y < h:
        if not duz[y]:
            y += 1
            continue
        bas = y
        while y < h and duz[y]:
            y += 1
        if bas > IC[0] * h and y < IC[1] * h and y - bas <= KALINLIK * h:
            komsu = (duzluk[max(0, bas - KOMSU) : bas].mean() + duzluk[y : y + KOMSU].mean()) / 2
            bulgu.append((round(bas / h, 3), round(float(komsu), 2)))
    return bulgu


def panelli(yol: Path) -> bool:
    """Karede yatay ya da dikey bir panel ara boşluğu var mı (üretimin kırptığı kadrajda bakılır)."""
    from otomat.hikaye.uretim import kenar_kirp  # döngüsel import: uretim bu modülü kullanıyor

    g = kenar_kirp(Image.open(yol).convert("RGB")).convert("L")
    g = g.resize((GENISLIK, max(1, round(g.height * GENISLIK / g.width))))
    a = np.asarray(g, dtype=np.float32)
    return any(k < ESIK for m in (a, a.T) for _, k in bantlar(m))
