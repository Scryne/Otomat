"""Haftalık rapor: raporlar/YYYY-HWW.md (ISO haftası, pazartesi–pazar).

Üretilen / düşen / yüklenen, kanal sayıları ve öldürme kriterine uzaklık, ödül penceresi ölçülen videoların en iyisi ve
en kötüsü, haydut durumu, Scryne'ın dokunuş süresi (raporlar/dokunus.jsonl; elle ya da oturumda eklenir).
Günlük koşu haftanın bitiminden RAPOR_GECIKME_GUN sonra (perşembe, UTC) yazar: Analytics 48-72 sa geç dolar,
pazartesi 00:02 UTC'de yazılan rapor (Kaliforniya'da pazar 17:02) son 2-3 günü eksik sayıyordu ve bir daha
yazılmıyordu. Elle: `python -m otomat.rapor 2026-H41`.
"""

import datetime as dt
import json
import sqlite3
from pathlib import Path

from otomat import haydut, kanal

RAPORLAR = kanal.aktif().raporlar
OLDURME = {"views": 1_200_000, "abone": 200, "gun": 56}  # Faz 8


def hafta_araligi(yil: int, hafta: int) -> tuple[dt.date, dt.date]:
    bas = dt.date.fromisocalendar(yil, hafta, 1)
    return bas, bas + dt.timedelta(days=6)


def dosya(yil: int, hafta: int) -> Path:
    return RAPORLAR / f"{yil}-H{hafta:02d}.md"


GERIYE_HAFTA = 4  # bu kadar eski eksik rapor da yazılır
ANALITIK_YENIDEN_GUN = 14  # analitiksiz yazılan rapor hafta bitiminden bu kadar gün içinde yeniden denenir
RAPOR_GECIKME_GUN = 3  # hafta bittikten bu kadar gün sonra yazılır (Analytics gecikmesi; analitik.GECIKME_GUN + 1)


def _analitiksiz(yil: int, hafta: int, bugun: dt.date) -> bool:
    """Analitiksiz yazılmış ve bugün henüz yeniden denenmemiş rapor. Günde bir deneme: token düşükken her cron
    (günde 4, iki kanal) 14 gün boyunca tam koşu açıp aynı hatayı alıyordu."""
    try:
        sayilar = json.loads(dosya(yil, hafta).with_suffix(".json").read_text(encoding="utf-8"))
        return bool(sayilar.get("analitik_hatasi")) and sayilar.get("yazildi", "") < bugun.isoformat()
    except (OSError, ValueError, AttributeError):
        return False


def bekleyen(bugun: dt.date) -> tuple[int, int] | None:
    """Yazılması gereken en eski hafta (yıl, hafta): biten son GERIYE_HAFTA haftadan raporu olmayan, ya da analitik
    alınamadan yazılmış ve hâlâ yeniden denenebilecek olan. Pazartesi koşusu pist dolu diye atlanırsa rapor ertesi
    koşuda yazılır; eskiden yalnız hemen önceki haftaya bakılıyordu (o hafta kaçarsa sonsuza dek eksik kalıyordu) ve
    analitiksiz rapor bir daha yazılmıyordu. O hafta hiç koşu kaydı olmayan kanal için rapor beklenmez."""
    for geri in range(GERIYE_HAFTA, 0, -1):
        yil, hafta, _ = (bugun - dt.timedelta(days=7 * geri)).isocalendar()
        bas, son = hafta_araligi(yil, hafta)
        if bugun < son + dt.timedelta(days=RAPOR_GECIKME_GUN):
            continue  # Analytics henüz dolmadı
        if dosya(yil, hafta).exists():
            if not (_analitiksiz(yil, hafta, bugun) and bugun <= son + dt.timedelta(days=ANALITIK_YENIDEN_GUN)):
                continue
        if _jsonl(RAPORLAR / "gunluk.jsonl", bas, son):
            return yil, hafta
    return None


def _oran(pay, payda) -> str:
    return f"%{100 * pay / payda:.0f}" if payda else "—"


def _sayi(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


def _jsonl(yol: Path, bas: dt.date, son: dt.date) -> list[dict]:
    from otomat.durum import jsonl_oku  # bozuk satır atlanır (yarım yazılmış satır raporu her koşuda düşürüyordu)

    return [s for s in jsonl_oku(yol) if bas.isoformat() <= str(s.get("tarih", "")) <= son.isoformat()]


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
    tamam_hepsi = [k for k in kosular if k.get("durum") == "tamam"]
    # aynı slot iki kez "tamam" yazılabiliyor (Plan B'ye düşen video sonraki koşuda hazır üretimle kanala çıktı):
    # üretilen video slot başına bir kez sayılır, harcanan neuron ise her koşunun kendi gerçek harcaması
    tamam = list({k["tarih"]: k for k in tamam_hepsi}.values())
    # kotaya takılan koşu ayrı satırda sayılır: aynı slot sonra üretildiyse hem üretilen hem düşen görünüyordu
    dusen = [k for k in kosular if k.get("durum") not in ("tamam", "bos", "kota")]
    cekilen = {v for (v,) in db.execute("SELECT video_id FROM geri_cekilen")}
    yuklenen = [t for t, s in secim.items() if s[3] and s[3] not in cekilen]
    kosu_gunu = {k.get("kosu", k["tarih"]) for k in kosular}
    s = [
        f"# Haftalık rapor: {yil} / hafta {hafta} ({bas.isoformat()} – {son.isoformat()})",
        "",
        "## Üretim",
        "",
        f"Üretilen **{len(tamam)}** · düşen **{len(dusen)}** · kanala ulaşan **{len(yuklenen)}** "
        f"(koşu kaydı {len(kosu_gunu)}/7 gün, {len(kosular)} satır; "
        f"mod: {', '.join(sorted({k['mod'] for k in kosular})) or '—'})",
        "",
    ]
    if kosular:
        s += ["| Gün | Durum | Konu | Kanca | Başlık | Video |", "| --- | --- | --- | --- | --- | --- |"]
        for k in kosular:
            # satır koşunun kendi kaydından; aynı gün iki koşu olursa seçim tablosunda yalnız sonuncusu durur
            baslik = k.get("baslik", "")
            kalip = k.get("kalip", "")
            s_konu, _, s_baslik, s_vid, _ = secim.get(k["tarih"], ("", "", "", None, None))
            # haydudun seçtiği konu (kol); eskiden anahtarın öneki ("wiki", "ezop") yazılıyordu
            konu = s_konu if baslik and s_baslik == baslik else k.get("anahtar", ":").split(":")[0]
            vid = k.get("video_id") or (s_vid if baslik and s_baslik == baslik else None)
            durum = {"tamam": "✅", "kota": "⏸ kota", "bos": "— boş"}.get(
                k.get("durum"), "❌ " + k.get("hata", "")[:80]
            )
            s.append(f"| {k['tarih']} | {durum} | {konu} | {kalip} | {baslik} | {vid or '—'} |")
        s.append("")
    neuron = [k["neuron"] for k in tamam_hepsi if "neuron" in k]
    dusen_hikaye = [d for k in kosular for d in k.get("dusen_hikayeler", [])]
    dusen_neuron = sum(d.get("neuron", 0) for d in dusen_hikaye)
    # kotaya takılan üretimin ve çeviri onarımının harcaması da (eskiden tam kota günlerinde eksik sayılıyordu)
    diger_neuron = sum(k.get("neuron", 0) for k in kosular if k.get("durum") == "kota") + sum(
        k.get("onarim_neuron", 0) for k in kosular
    )
    if (
        neuron or dusen_neuron or diger_neuron
    ):  # hikâye motoru: Cloudflare bedava kotası günde 10.000, iki kanal paylaşır
        ort = f", video başına ort. {_sayi(sum(neuron) / len(neuron))}" if neuron else ""
        diger = f"; kotaya takılan üretim ve çeviri onarımı {_sayi(diger_neuron)}" if diger_neuron else ""
        s += [
            f"Cloudflare: {_sayi(sum(neuron) + dusen_neuron + diger_neuron)} neuron (yayına giden videolar "
            f"{_sayi(sum(neuron))}{ort}; düşen hikâyeler {_sayi(dusen_neuron)}{diger}).",
            "",
        ]
    if dusen_hikaye:
        s += [f"Hakemden ya da yayın kabulünden düşen hikâye: {len(dusen_hikaye)}.", ""]
    istek = sum(k.get("buffer_istek", 0) for k in kosular)
    if istek:
        s += [f"Buffer API: {istek} istek (sınır 30 günde 3.000, anahtar başına; tüm kanallar paylaşır).", ""]
    havuz = [k["havuz_kalan"] for k in kosular if "havuz_kalan" in k]
    if havuz:
        s += [f"Hikâye havuzu: {havuz[-1]} anlatılmamış hikâye kaldı.", ""]
    kota = [k for k in kosular if k.get("durum") == "kota"]
    if kota:
        s += [f"Kotaya takılan üretim: {len(kota)} (pist tampon oldu, yayın kaçmadıysa alarm yok).", ""]
    hatalar = sorted({h for k in kosular for h in k.get("kaynak_hatalari", [])})
    if hatalar:
        s += ["Kaynak hataları: " + "; ".join(hatalar), ""]

    s += ["## Kanal", ""]
    if kanal_bu is None:
        s += [f"Analitik alınamadı: {analitik_hatasi or 'bilinmiyor'}", ""]
    else:
        s += [
            f"Bu hafta {_sayi(kanal_bu['views'])} görüntüleme (engaged {_sayi(kanal_bu['engaged_views'])}; ilk "
            f"saniyeleri geçen {_oran(kanal_bu['engaged_views'], kanal_bu['views'])}), "
            f"abone net {kanal_bu['abone_net']:+d}. Kanalda {kanal_bu['video_sayisi']} video, "
            f"{kanal_bu['abone_toplam']} abone.",
            "",
        ]
        if kanal_56:
            s += [
                f"Öldürme kriteri (Faz 8, ilk public videodan bu yana, en çok {OLDURME['gun']} gün; "
                f"{kanal_56.get('bas', '?')} – {kanal_56.get('son', '?')}): {_sayi(kanal_56['views'])} / "
                f"{_sayi(OLDURME['views'])} görüntüleme · {kanal_bu['abone_toplam']} / {OLDURME['abone']} abone.",
                "",
            ]

    od = haydut.oduller(db, son)
    olculen = db.execute(
        "SELECT video_id, yayin_gunu, views, engaged_views, ort_izlenme_yuzde FROM olcumler"
        " WHERE olculdu BETWEEN ? AND ?",
        (bas.isoformat(), son.isoformat()),
    ).fetchall()
    s += ["## Videolar (ödül penceresi: yayın günü + 2 gün)", ""]
    if not olculen:
        s += ["Bu hafta ölçümü olgunlaşan video yok.", ""]
    else:
        odul = {o["video_id"]: o["odul"] for o in od}
        sirali = sorted(olculen, key=lambda r: (odul.get(r[0], -1), r[3]), reverse=True)
        # "Kalan": ilk saniyeleri geçen görüntüleme oranı (engaged / görüntüleme). Pusula bu (10-14): nişte tutarlı
        # izlenen kanallar ~%70+, Earth'ün sahneli videoları %25-38'de kaldı
        s += ["| Video | Yayın | Görüntüleme | Engaged | Kalan | İzlenme % | Ödül |",
              "| --- | --- | --- | --- | --- | --- | --- |"]  # fmt: skip
        for v, g, w, e, y in sirali:
            s.append(f"| {v} | {g} | {_sayi(w)} | {_sayi(e)} | {_oran(e, w)} | {y:.1f} | {odul.get(v, '—')} |")
        s += ["", f"En iyi: {sirali[0][0]} · en kötü: {sirali[-1][0]}", ""]
        if any(y > 100 for *_, y in sirali):
            # Shorts görüntülemesi her yeniden oynatmayı sayar (2025-03), engaged saymaz: 8 sn kart döngüye girdikçe
            # Kalan düşer. Kartta Kalan tek başına pusula değil; İzlenme % 100'ü aşıyorsa izleyici videoyu döndürüyor
            s += ["İzlenme % 100'ü aşan video döngüye giriyor (kart): görüntüleme her tekrarı saydığı için Kalan "
                  "olduğundan düşük görünür.", ""]  # fmt: skip

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


def k14_araligi(son: dt.date) -> tuple[dt.date, dt.date] | None:
    """K-14 penceresi: formatın ilk public videosundan (portfoy.ilk_public) başlar, en çok 56 gün sürer, raporun
    haftasıyla biter. Eskiden haftanın son 56 günüydü: format öncesi geri çekilen veri videolarını ve Orbit'in 0
    izlenmeli çocuk dönemini de sayıyor, karar haftasında sınırı 6 gün aşıyordu. Sayaç başlamadıysa None."""
    from otomat.portfoy import ilk_public

    if (ilk := ilk_public(kanal.aktif())) is None or ilk > son:
        return None
    return ilk, min(son, ilk + dt.timedelta(days=OLDURME["gun"] - 1))


def yaz(db: sqlite3.Connection, yil: int, hafta: int, yt=None, ya=None, analitik_hatasi: str | None = None) -> Path:
    from otomat import analitik

    bas, son = hafta_araligi(yil, hafta)
    kanal_bu = kanal_56 = None
    if yt is not None and ya is not None:
        kanal_bu = analitik.kanal(yt, ya, bas, son)
        if aralik := k14_araligi(son):
            kanal_56 = {**analitik.kanal(yt, ya, *aralik), "bas": aralik[0].isoformat(), "son": aralik[1].isoformat()}
    yol = dosya(yil, hafta)
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(olustur(db, yil, hafta, kanal_bu, kanal_56, analitik_hatasi), encoding="utf-8")
    # portföy raporu (portfoy.py) kanalları yan yana koyar; analitik yalnız kanalın kendi token'ıyla okunur
    sayilar = {"kanal": kanal.aktif().id, "hafta": kanal_bu, "son_56_gun": kanal_56, "analitik_hatasi": analitik_hatasi,
               "yazildi": dt.datetime.now(dt.UTC).date().isoformat()}  # fmt: skip
    yol.with_suffix(".json").write_text(json.dumps(sayilar, ensure_ascii=False, indent=1), encoding="utf-8")
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
