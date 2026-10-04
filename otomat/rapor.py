"""Haftalık rapor: raporlar/YYYY-HWW.md (ISO haftası, pazartesi–pazar).

Üretilen / düşen / yüklenen, kanal sayıları ve öldürme kriterine uzaklık, ödül penceresi ölçülen videoların en iyisi ve
en kötüsü, haydut durumu, Scryne'ın dokunuş süresi (raporlar/dokunus.jsonl; elle ya da oturumda eklenir).
Günlük koşu pazartesi günü bir önceki haftanınkini yazar; elle: `python -m otomat.rapor 2026-H41`.
"""

import datetime as dt
import json
import sqlite3
from pathlib import Path

from otomat import haydut
from otomat.ayarlar import KOK

RAPORLAR = KOK / "raporlar"
OLDURME = {"views": 1_200_000, "abone": 200, "gun": 56}  # Faz 8


def hafta_araligi(yil: int, hafta: int) -> tuple[dt.date, dt.date]:
    bas = dt.date.fromisocalendar(yil, hafta, 1)
    return bas, bas + dt.timedelta(days=6)


def dosya(yil: int, hafta: int) -> Path:
    return RAPORLAR / f"{yil}-H{hafta:02d}.md"


def _sayi(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


def _jsonl(yol: Path, bas: dt.date, son: dt.date) -> list[dict]:
    if not yol.exists():
        return []
    satirlar = [json.loads(s) for s in yol.read_text(encoding="utf-8").splitlines() if s.strip()]
    return [s for s in satirlar if bas.isoformat() <= s["tarih"] <= son.isoformat()]


def olustur(db: sqlite3.Connection, yil: int, hafta: int, kanal_bu: dict | None, kanal_56: dict | None,
            analitik_hatasi: str | None = None) -> str:  # fmt: skip
    bas, son = hafta_araligi(yil, hafta)
    kosular = _jsonl(RAPORLAR / "gunluk.jsonl", bas, son)
    secim = {
        t: (k, kl, b, v, g)
        for t, k, kl, b, v, g in db.execute(
            "SELECT tarih, konu, kalip, baslik, video_id, gunluk FROM secimler WHERE tarih BETWEEN ? AND ?",
            (bas.isoformat(), son.isoformat()),
        )
    }
    tamam = [k for k in kosular if k["durum"] == "tamam"]
    dusen = [k for k in kosular if k["durum"] != "tamam"]
    yuklenen = [t for t, s in secim.items() if s[3]]
    s = [
        f"# Haftalık rapor: {yil} / hafta {hafta} ({bas.isoformat()} – {son.isoformat()})",
        "",
        "## Üretim",
        "",
        f"Üretilen **{len(tamam)}** · düşen **{len(dusen)}** · kanala ulaşan **{len(yuklenen)}** "
        f"(koşu kaydı {len(kosular)}/7 gün; mod: {', '.join(sorted({k['mod'] for k in kosular})) or '—'})",
        "",
    ]
    if kosular:
        s += ["| Gün | Durum | Konu | Kanca | Başlık | Video |", "| --- | --- | --- | --- | --- | --- |"]
        for k in kosular:
            # satır koşunun kendi kaydından; aynı gün iki koşu olursa seçim tablosunda yalnız sonuncusu durur
            baslik = k.get("baslik", "")
            konu, kalip = k.get("anahtar", ":").split(":")[0], k.get("kalip", "")
            _, _, s_baslik, s_vid, _ = secim.get(k["tarih"], ("", "", "", None, None))
            vid = k.get("video_id") or (s_vid if baslik and s_baslik == baslik else None)
            durum = "✅" if k["durum"] == "tamam" else "❌ " + k.get("hata", "")[:80]
            s.append(f"| {k['tarih']} | {durum} | {konu} | {kalip} | {baslik} | {vid or '—'} |")
        s.append("")
    hatalar = sorted({h for k in kosular for h in k.get("kaynak_hatalari", [])})
    if hatalar:
        s += ["Kaynak hataları: " + "; ".join(hatalar), ""]

    s += ["## Kanal", ""]
    if kanal_bu is None:
        s += [f"Analitik alınamadı: {analitik_hatasi or 'bilinmiyor'}", ""]
    else:
        s += [
            f"Bu hafta {_sayi(kanal_bu['views'])} görüntüleme (engaged {_sayi(kanal_bu['engaged_views'])}), "
            f"abone net {kanal_bu['abone_net']:+d}. Kanalda {kanal_bu['video_sayisi']} video, "
            f"{kanal_bu['abone_toplam']} abone.",
            "",
        ]
        if kanal_56:
            s += [
                f"Öldürme kriteri (Faz 8, son {OLDURME['gun']} gün): {_sayi(kanal_56['views'])} / "
                f"{_sayi(OLDURME['views'])} görüntüleme · {kanal_bu['abone_toplam']} / {OLDURME['abone']} abone.",
                "",
            ]

    od = haydut.oduller(db, son)
    olculen = [
        (v, g, e, y)
        for v, g, e, y in db.execute(
            "SELECT video_id, yayin_gunu, engaged_views, ort_izlenme_yuzde FROM olcumler WHERE olculdu BETWEEN ? AND ?",
            (bas.isoformat(), son.isoformat()),
        )
    ]
    s += ["## Videolar (ödül penceresi: yayın günü + 2 gün)", ""]
    if not olculen:
        s += ["Bu hafta ölçümü olgunlaşan video yok.", ""]
    else:
        odul = {o["video_id"]: o["odul"] for o in od}
        sirali = sorted(olculen, key=lambda r: (odul.get(r[0], -1), r[2]), reverse=True)
        s += ["| Video | Yayın | Engaged | İzlenme % | Ödül |", "| --- | --- | --- | --- | --- |"]
        for v, g, e, y in sirali:
            s.append(f"| {v} | {g} | {_sayi(e)} | {y:.1f} | {odul.get(v, '—')} |")
        s += ["", f"En iyi: {sirali[0][0]} · en kötü: {sirali[-1][0]}", ""]

    s += ["## Haydut", "", f"Posteriora giren ödül: {len(od)} (son {haydut.PENCERE_GUN} gün).", ""]
    for eksen in ("konu", "kalip"):
        post = haydut.posteriorlar(od, eksen)
        if post:
            s.append(
                f"- {eksen}: " + ", ".join(f"{k} {a / (a + b):.2f} (n={n})" for k, (a, b, n) in sorted(post.items()))
            )
    degisen = [(t, json.loads(g)["degisti"]) for t, (_, _, _, _, g) in sorted(secim.items()) if g]
    degisen = [(t, d) for t, d in degisen if d]
    s += [
        "- Seçimi analitiğin değiştirdiği günler: "
        + (", ".join(f"{t} ({'+'.join(d)})" for t, d in degisen) if degisen else "yok"),
        "",
    ]

    dokunus = _jsonl(RAPORLAR / "dokunus.jsonl", bas, son)
    s += ["## Scryne'ın dokunuşu", ""]
    if dokunus:
        s += [f"Toplam {sum(d['dk'] for d in dokunus)} dk (sınır haftada 10 dk):"]
        s += [f"- {d['tarih']}: {d['ne']} ({d['dk']} dk)" for d in dokunus]
    else:
        s += ["Kayıt yok (raporlar/dokunus.jsonl)."]
    return "\n".join(s) + "\n"


def yaz(db: sqlite3.Connection, yil: int, hafta: int, yt=None, ya=None, analitik_hatasi: str | None = None) -> Path:
    from otomat import analitik

    bas, son = hafta_araligi(yil, hafta)
    kanal_bu = kanal_56 = None
    if yt is not None and ya is not None:
        kanal_bu = analitik.kanal(yt, ya, bas, son)
        kanal_56 = analitik.kanal(yt, ya, son - dt.timedelta(days=OLDURME["gun"] - 1), son)
    yol = dosya(yil, hafta)
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(olustur(db, yil, hafta, kanal_bu, kanal_56, analitik_hatasi), encoding="utf-8")
    return yol


def main() -> None:
    import sys

    from otomat import analitik, durum

    yil, hafta = (int(x) for x in sys.argv[1].split("-H"))
    try:
        yt, ya = analitik.servisler()
        hata = None
    except Exception as e:  # noqa: BLE001 — rapor analitiksiz de yazılır
        yt = ya = None
        hata = f"{type(e).__name__}: {e}"
    print(yaz(durum.baglan(), yil, hafta, yt, ya, hata))


if __name__ == "__main__":
    main()
