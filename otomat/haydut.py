"""Faktörlü Thompson sampling: konu (veri kolu) ve kanca kalıbı için ayrı Beta posteriorları.

Ödül [0, 1] arasıdır ve videonun ±14 gün içindeki komşularına göre sırasıdır: 0,7 × engagedViews sırası +
0,3 × ortalama izlenme yüzdesi sırası, ikisi de yayın günü + 2 günlük pencerede (analitik.py). Mutlak sayı yerine sıra:
kanal büyüdükçe her video öncekini geçer, ama bu konunun ya da kancanın başarısı değildir. İzlenme ağırlığı öldürme
kriterinin (Faz 8) ölçüsü olduğu için büyük; izlenme yüzdesi Shorts dağıtımının öncü göstergesi.

Posteriorlar her koşuda SQLite'tan baştan hesaplanır (Beta(1, 1) + son 56 günün ödülleri); saklanan durum yoktur.
Örnekleme ters CDF ile yapılır: her kol için bir u ~ U(0, 1) çekilir, θ = F⁻¹(u; α, β). Aynı u'larla veri olmadan
(Beta(1, 1), θ = u) seçilecek kol da bulunur; ikisi farklıysa seçimi analitik değiştirmiştir ve log bunu yazar.
"""

import datetime as dt
import math
import random
import sqlite3

PENCERE_GUN = 56  # posteriora giren ödüllerin yaşı
KOMSU_GUN = 14  # ödül sırası bu yakınlıktaki videolara göre
AGIRLIK = {"engaged_views": 0.7, "ort_izlenme_yuzde": 0.3}
ONCUL = (1.0, 1.0)


def _betacf(a: float, b: float, x: float) -> float:
    # Düzenlenmiş eksik beta için sürekli kesir (Lentz yöntemi)
    kucuk = 1e-300
    c, d = 1.0, 1.0 - (a + b) * x / (a + 1)
    d = 1 / (d if abs(d) > kucuk else kucuk)
    h = d
    for m in range(1, 300):
        for aa in (
            m * (b - m) * x / ((a - 1 + 2 * m) * (a + 2 * m)),
            -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 1 + 2 * m)),
        ):
            d = 1 + aa * d
            d = 1 / (d if abs(d) > kucuk else kucuk)
            c = 1 + aa / c
            c = c if abs(c) > kucuk else kucuk
            h *= d * c
        if abs(d * c - 1) < 1e-14:
            break
    return h


def beta_cdf(x: float, a: float, b: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    ln = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(ln) * _betacf(a, b, x) / a
    return 1 - math.exp(ln) * _betacf(b, a, 1 - x) / b


def beta_ters(u: float, a: float, b: float) -> float:
    alt, ust = 0.0, 1.0
    for _ in range(60):
        orta = (alt + ust) / 2
        if beta_cdf(orta, a, b) < u:
            alt = orta
        else:
            ust = orta
    return (alt + ust) / 2


def _sira(x: float, digerleri: list[float]) -> float:
    return (sum(d < x for d in digerleri) + 0.5 * sum(d == x for d in digerleri)) / len(digerleri)


def oduller(db: sqlite3.Connection, bugun: dt.date) -> list[dict]:
    """Ölçülmüş her video için ödül; komşusu olmayan video (ilk video) ödülsüz kalır."""
    bas = (bugun - dt.timedelta(days=PENCERE_GUN + KOMSU_GUN)).isoformat()
    satirlar = db.execute(
        "SELECT s.konu, s.kalip, o.video_id, o.yayin_gunu, o.engaged_views, o.ort_izlenme_yuzde "
        "FROM secimler s JOIN olcumler o ON o.video_id = s.video_id WHERE o.yayin_gunu >= ? ORDER BY o.yayin_gunu",
        (bas,),
    ).fetchall()
    videolar = [
        {"konu": k, "kalip": kl, "video_id": v, "gun": dt.date.fromisoformat(g), "engaged_views": e,
         "ort_izlenme_yuzde": y}
        for k, kl, v, g, e, y in satirlar
    ]  # fmt: skip
    sonuc = []
    sinir = bugun - dt.timedelta(days=PENCERE_GUN)
    for v in videolar:
        if v["gun"] < sinir:
            continue
        komsular = [w for w in videolar if w is not v and abs((w["gun"] - v["gun"]).days) <= KOMSU_GUN]
        if not komsular:
            continue
        odul = sum(a * _sira(v[m], [w[m] for w in komsular]) for m, a in AGIRLIK.items())
        sonuc.append({**v, "gun": v["gun"].isoformat(), "odul": round(odul, 4), "komsu": len(komsular)})
    return sonuc


def posteriorlar(odul_listesi: list[dict], eksen: str) -> dict[str, tuple[float, float, int]]:
    post: dict[str, tuple[float, float, int]] = {}
    for o in odul_listesi:
        a, b, n = post.get(o[eksen], (*ONCUL, 0))
        post[o[eksen]] = (a + o["odul"], b + 1 - o["odul"], n + 1)
    return post


def thompson(secenekler: list[str], post: dict, rng: random.Random) -> tuple[str, str, dict]:
    """(seçilen, veri olmadan seçilecek olan, kol başına ayrıntı)."""
    ayrinti = {}
    for s in sorted(secenekler):
        a, b, n = post.get(s, (*ONCUL, 0))
        u = rng.random()
        ayrinti[s] = {
            "a": round(a, 3),
            "b": round(b, 3),
            "n": n,
            "u": round(u, 4),
            "theta": round(beta_ters(u, a, b), 4),
        }
    secilen = max(ayrinti, key=lambda s: ayrinti[s]["theta"])
    veri_olmadan = max(ayrinti, key=lambda s: ayrinti[s]["u"])
    return secilen, veri_olmadan, ayrinti


def sec(
    db: sqlite3.Connection, bugun: dt.date, konular: list[str], kaliplar: list[str], rng: random.Random
) -> tuple[str, str, dict]:
    """Günün konusu ve kanca kalıbı; üçüncü değer seçim logudur (SQLite + günlük rapor)."""
    od = oduller(db, bugun)
    konu, konu0, konu_ayr = thompson(konular, posteriorlar(od, "konu"), rng)
    kalip, kalip0, kalip_ayr = thompson(kaliplar, posteriorlar(od, "kalip"), rng)
    degisti = [e for e, s, s0 in (("konu", konu, konu0), ("kalip", kalip, kalip0)) if s != s0]
    log = {
        "odul_sayisi": len(od),
        "konu": konu_ayr,
        "kalip": kalip_ayr,
        "veri_olmadan": {"konu": konu0, "kalip": kalip0},
        "degisti": degisti,
    }
    return konu, kalip, log
