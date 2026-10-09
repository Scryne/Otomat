"""Portföy raporu (Faz 13, K-14): matristeki kanallar yan yana, haftalık → raporlar/portfoy/YYYY-HWW.md.

Her kanal kendi işinde, kendi token'ıyla haftalık raporunu yazar (rapor.py; sayılar YYYY-HWW.json'da). Bu modül token
istemez: kanalların günlük kayıtlarını (gunluk.jsonl), durum veritabanlarını ve haftalık sayılarını birleştirir.
Kanallar dört kotayı paylaşır; rapor hangi kanalın ne kadar harcadığını gösterir:
- Cloudflare Workers AI: günde 10.000 neuron (hesap başına; kayan 24 saat).
- Buffer: 30 günde 3.000 istek (API anahtarı başına).
- YouTube Data API: günde 10.000 birim (Cloud projesi başına). Tahmin: kanala çıkan video başına videos.update 50 +
  altyazı izi başına captions.insert 400, koşu başına okumalar ~10.
- GitHub Actions: ayda 2.000 dakika (private repo). İşler dakikaya yukarı yuvarlanır; GH_TOKEN yoksa satır boş kalır.

Actions'ta günlük iş akışının `portfoy` işi kanal işlerinden sonra koşar. Elle: `uv run python -m otomat.portfoy`
(biten son hafta) ya da `uv run python -m otomat.portfoy 2026-H41`.
"""

import datetime as dt
import http.client
import json
import math
import os
import sqlite3
import subprocess
from pathlib import Path

import yaml

from otomat import kanal
from otomat.ayarlar import KOK

PORTFOY = KOK / "raporlar" / "portfoy"
IS_AKISI = KOK / ".github" / "workflows" / "gunluk.yml"
ILK_HAFTA = (2026, 41)  # portföy raporu bu haftadan başlar (hikâye formatının ilk tam haftası)
OLDURME = {"views": 1_200_000, "abone": 200, "gun": 56}  # Faz 8, kanal başına (K-14)
SINIR = {"neuron_gun": 10_000, "buffer_30_gun": 3_000, "api_gun": 10_000, "actions_ay": 2_000}
API_VIDEO, API_ALTYAZI, API_KOSU = 50, 400, 10
REPO = "Scryne/Otomat"


def aktif_kanallar() -> list[kanal.Kanal]:
    """Günlük iş akışının matrisindeki kanallar (yayında olanlar; arşiv profilleri değil)."""
    matris = yaml.safe_load(IS_AKISI.read_text(encoding="utf-8"))["jobs"]["uret"]["strategy"]["matrix"]["include"]
    return [kanal.yukle(s["kanal"]) for s in matris]


def hafta_araligi(yil: int, hafta: int) -> tuple[dt.date, dt.date]:
    bas = dt.date.fromisocalendar(yil, hafta, 1)
    return bas, bas + dt.timedelta(days=6)


def dosya(yil: int, hafta: int) -> Path:
    return PORTFOY / f"{yil}-H{hafta:02d}.md"


def _sayi(n: float | None) -> str:
    return "—" if n is None else f"{n:,.0f}".replace(",", ".")


def _kayitlar(k: kanal.Kanal) -> list[dict]:
    yol = k.raporlar / "gunluk.jsonl"
    if not yol.exists():
        return []
    return [json.loads(s) for s in yol.read_text(encoding="utf-8").splitlines() if s.strip()]


def _kosu_gunu(r: dict) -> str:
    """Kotanın harcandığı gün: pist modunda `tarih` videonun slot günüdür, koşu günü `kosu`."""
    return r.get("kosu", r["tarih"])


def _neuron(r: dict) -> int:
    return r.get("neuron", 0) + sum(d.get("neuron", 0) for d in r.get("dusen_hikayeler", []))


def _api_birimi(r: dict) -> int:
    if not r.get("video_id"):
        return 0
    return API_VIDEO + API_ALTYAZI * (1 + len(r.get("diller", [])))


def ilk_public(k: kanal.Kanal) -> dt.date | None:
    """Kanalın şimdiki formatının ilk yayın günü: geri çekilmemiş, kanala çıkmış en erken video (K-14 sayacı)."""
    if not k.durum.exists():
        return None
    db = sqlite3.connect(f"file:{k.durum.as_posix()}?mode=ro", uri=True)
    try:
        an = db.execute(
            "SELECT min(yayin_ani) FROM secimler WHERE video_id IS NOT NULL"
            " AND video_id NOT IN (SELECT video_id FROM geri_cekilen)"
        ).fetchone()[0]
    finally:
        db.close()
    return dt.datetime.fromisoformat(an).date() if an else None


def kanal_ozeti(k: kanal.Kanal, yil: int, hafta: int) -> dict:
    bas, son = hafta_araligi(yil, hafta)
    tum = _kayitlar(k)
    kosu = [r for r in tum if bas.isoformat() <= _kosu_gunu(r) <= son.isoformat()]
    ay_bas = (son - dt.timedelta(days=29)).isoformat()
    sayilar_yolu = k.raporlar / f"{yil}-H{hafta:02d}.json"
    sayilar = json.loads(sayilar_yolu.read_text(encoding="utf-8")) if sayilar_yolu.exists() else {}
    ilk = ilk_public(k)
    havuz = [r["havuz_kalan"] for r in kosu if "havuz_kalan" in r]
    gunluk_neuron: dict[str, int] = {}
    gunluk_api: dict[str, int] = {}
    for r in kosu:
        gunluk_neuron[_kosu_gunu(r)] = gunluk_neuron.get(_kosu_gunu(r), 0) + _neuron(r)
        gunluk_api[_kosu_gunu(r)] = gunluk_api.get(_kosu_gunu(r), 0) + _api_birimi(r)
    for gun in {_kosu_gunu(r) for r in kosu}:
        gunluk_api[gun] += API_KOSU
    return {
        "id": k.id,
        "ad": k.ad,
        "uretilen": sum(r.get("durum") == "tamam" for r in kosu),
        "kanala_cikan": sum(bool(r.get("video_id")) for r in kosu),
        "dusen_hikaye": sum(len(r.get("dusen_hikayeler", [])) for r in kosu),
        "kota": sum(r.get("durum") == "kota" for r in kosu),
        "hata": sum(r.get("durum") == "hata" for r in kosu),
        "neuron": sum(gunluk_neuron.values()),
        "gunluk_neuron": gunluk_neuron,
        "gunluk_api": gunluk_api,
        "buffer_istek": sum(r.get("buffer_istek", 0) for r in kosu),
        "buffer_30_gun": sum(r.get("buffer_istek", 0) for r in tum if ay_bas <= _kosu_gunu(r) <= son.isoformat()),
        "havuz": havuz[-1] if havuz else None,
        "hafta": sayilar.get("hafta"),
        "son_56_gun": sayilar.get("son_56_gun"),
        "analitik_hatasi": sayilar.get("analitik_hatasi"),
        "rapor_var": (k.raporlar / f"{yil}-H{hafta:02d}.md").exists(),
        "kayit_var": bool(kosu),
        "ilk_public": ilk,
    }


def _gh_token() -> str | None:
    if t := os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"):
        return t
    try:
        return subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


_BAGLANTI: list[http.client.HTTPSConnection] = []


def _gh(yol: str, belirtec: str) -> dict:
    """GitHub REST; tek, açık tutulan bağlantı (her istekte yeni bağlantı bu makinede istek başı ~3 sn sürüyordu)."""
    if not _BAGLANTI:
        _BAGLANTI.append(http.client.HTTPSConnection("api.github.com", timeout=30))
    baglanti = _BAGLANTI[0]
    baglanti.request(
        "GET",
        f"/repos/{os.environ.get('GITHUB_REPOSITORY', REPO)}/{yol}",
        headers={
            "Authorization": f"Bearer {belirtec}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "otomat",
        },
    )
    yanit = baglanti.getresponse()
    govde = yanit.read()
    if yanit.status != 200:
        raise OSError(f"GitHub API {yanit.status}: {govde[:200]!r}")
    return json.loads(govde)


def is_dakikasi(is_: dict) -> int:
    """Faturalanan dakika: atlanan iş 0, gerisi yukarı yuvarlanır (GitHub iş başına dakikaya yuvarlar)."""
    if is_.get("conclusion") == "skipped" or not is_.get("started_at") or not is_.get("completed_at"):
        return 0
    bas = dt.datetime.fromisoformat(is_["started_at"].replace("Z", "+00:00"))
    son = dt.datetime.fromisoformat(is_["completed_at"].replace("Z", "+00:00"))
    return max(1, math.ceil((son - bas).total_seconds() / 60))


def actions_dakikasi(bas: dt.date, son: dt.date, kanallar: list[str]) -> dict[str, int] | None:
    """Kanal başına (günlük üretim işi) ve ortak (CI, portföy, diğer iş akışları) Actions dakikası. İş ayrıntısı yalnız
    günlük üretim koşularında istenir (kanallara bölmek için); tek işli koşular (CI) koşu süresinden sayılır."""
    belirtec = _gh_token()
    if not belirtec:
        return None
    dakika = {k: 0 for k in [*kanallar, "ortak"]}
    try:
        sayfa = 1
        while True:
            y = _gh(f"actions/runs?created={bas.isoformat()}..{son.isoformat()}&per_page=100&page={sayfa}", belirtec)
            for kosu in y.get("workflow_runs", []):
                if not kosu.get("path", "").endswith("/gunluk.yml"):
                    dakika["ortak"] += is_dakikasi(
                        {
                            "started_at": kosu.get("run_started_at"),
                            "completed_at": kosu.get("updated_at"),
                            "conclusion": kosu.get("conclusion"),
                        }  # fmt: skip
                    )
                    continue
                for is_ in _gh(f"actions/runs/{kosu['id']}/jobs?per_page=100", belirtec).get("jobs", []):
                    ad = is_.get("name", "")
                    sahibi = next((k for k in kanallar if ad.startswith(f"uret ({k},")), "ortak")
                    dakika[sahibi] += is_dakikasi(is_)
            if len(y.get("workflow_runs", [])) < 100:
                return dakika
            sayfa += 1
    except (OSError, ValueError, KeyError):
        return None


def olustur(yil: int, hafta: int, ozetler: list[dict], dakika: dict[str, int] | None) -> str:
    bas, son = hafta_araligi(yil, hafta)
    baslik = "| | " + " | ".join(f"{o['ad']} (`{o['id']}`)" for o in ozetler) + " |"
    s = [
        f"# Portföy: {yil} / hafta {hafta} ({bas.isoformat()} – {son.isoformat()})",
        "",
        "Kanal raporları: " + ", ".join(f"`raporlar/{o['id']}`" for o in ozetler) + " (kanalın kendi haftalık raporu "
        "üretim tablosunu, ödül ölçümlerini ve haydudu ayrıntılı verir).",
        "",
        "## Kanallar",
        "",
        baslik,
        "| --- |" + " --- |" * len(ozetler),
    ]

    def satir(ad: str, f) -> None:
        s.append(f"| {ad} | " + " | ".join(f(o) for o in ozetler) + " |")

    def analitik(o: dict, alan: str, f) -> str:
        if o["hafta"] is None:
            return "—" if not o["analitik_hatasi"] else "analitik yok"
        return f(o[alan])

    satir("Üretilen · kanala çıkan", lambda o: f"{o['uretilen']} · {o['kanala_cikan']}")
    satir("Düşen hikâye · kota · hata", lambda o: f"{o['dusen_hikaye']} · {o['kota']} · {o['hata']}")
    satir("Görüntüleme (hafta)", lambda o: analitik(o, "hafta", lambda h: _sayi(h["views"])))
    satir(
        "Abone (net · toplam)",
        lambda o: analitik(o, "hafta", lambda h: f"{h['abone_net']:+d} · {_sayi(h['abone_toplam'])}"),
    )
    satir("Hikâye havuzu (kalan)", lambda o: _sayi(o["havuz"]))
    satir("Cloudflare neuron", lambda o: _sayi(o["neuron"]))
    satir("Buffer isteği (hafta · 30 gün)", lambda o: f"{_sayi(o['buffer_istek'])} · {_sayi(o['buffer_30_gun'])}")
    satir("YouTube API birimi (tahmin)", lambda o: _sayi(sum(o["gunluk_api"].values())))
    satir("Actions dakikası", lambda o: _sayi(dakika.get(o["id"])) if dakika else "—")

    s += ["", "## Öldürme kriteri (K-14: kanal başına, ilk public videodan 56 gün sonra)", ""]
    for o in ozetler:
        if o["ilk_public"] is None:
            s.append(f"- **{o['ad']}**: kanalda henüz yeni formatta video yok; sayaç başlamadı.")
            continue
        karar = o["ilk_public"] + dt.timedelta(days=OLDURME["gun"])
        gecen = (son - o["ilk_public"]).days + 1
        if o["son_56_gun"] is None:
            olcum = "analitik bu hafta okunamadı"
        else:
            olcum = (
                f"son {OLDURME['gun']} günde {_sayi(o['son_56_gun']['views'])} / {_sayi(OLDURME['views'])} "
                "görüntüleme, "
                f"{_sayi(o['hafta']['abone_toplam'])} / {OLDURME['abone']} abone"
            )
        s.append(
            f"- **{o['ad']}**: ilk public {o['ilk_public'].isoformat()}, karar günü {karar.isoformat()} "
            f"({min(gecen, OLDURME['gun'])}/{OLDURME['gun']} gün); {olcum}."
        )

    neuron_gun: dict[str, int] = {}
    api_gun: dict[str, int] = {}
    for o in ozetler:
        for g, n in o["gunluk_neuron"].items():
            neuron_gun[g] = neuron_gun.get(g, 0) + n
        for g, n in o["gunluk_api"].items():
            api_gun[g] = api_gun.get(g, 0) + n
    s += ["", "## Paylaşılan kotalar", ""]

    def zirve(gunler: dict[str, int], sinir: int, ad: str) -> str:
        if not gunler:
            return f"- {ad}: bu hafta harcama yok (sınır günde {_sayi(sinir)})."
        g, n = max(gunler.items(), key=lambda x: x[1])
        toplam = _sayi(sum(gunler.values()))
        return f"- {ad}: haftada {toplam}; en yoğun gün {g} {_sayi(n)} (sınır günde {_sayi(sinir)})."

    s.append(zirve(neuron_gun, SINIR["neuron_gun"], "Cloudflare neuron"))
    s.append(
        f"- Buffer: son 30 günde {_sayi(sum(o['buffer_30_gun'] for o in ozetler))} istek "
        f"(sınır {_sayi(SINIR['buffer_30_gun'])}, anahtar başına)."
    )
    s.append(zirve(api_gun, SINIR["api_gun"], "YouTube API birimi (tahmin)"))
    if dakika is None:
        s.append("- Actions: GitHub belirteci yoktu, dakika okunamadı.")
    else:
        toplam = sum(dakika.values())
        s.append(
            f"- Actions: haftada {_sayi(toplam)} dk (ortak işler {_sayi(dakika['ortak'])}); ay tahmini "
            f"~{_sayi(toplam * 30 / 7)} / {_sayi(SINIR['actions_ay'])} dk."
        )
    return "\n".join(s) + "\n"


def bekleyen(bugun: dt.date) -> tuple[int, int] | None:
    """Biten son haftanın portföy raporu yoksa ve kayıtlı her kanalın haftalık raporu yazıldıysa (yıl, hafta)."""
    yil, hafta, _ = (bugun - dt.timedelta(days=7)).isocalendar()
    if (yil, hafta) < ILK_HAFTA or dosya(yil, hafta).exists():
        return None
    ozetler = [kanal_ozeti(k, yil, hafta) for k in aktif_kanallar()]
    hazir = all(o["rapor_var"] or not o["kayit_var"] for o in ozetler) and any(o["kayit_var"] for o in ozetler)
    return (yil, hafta) if hazir else None


def yaz(yil: int, hafta: int) -> Path:
    kanallar = aktif_kanallar()
    ozetler = [kanal_ozeti(k, yil, hafta) for k in kanallar]
    dakika = actions_dakikasi(*hafta_araligi(yil, hafta), [k.id for k in kanallar])
    yol = dosya(yil, hafta)
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(olustur(yil, hafta, ozetler, dakika), encoding="utf-8")
    return yol


def main() -> None:
    import sys

    if len(sys.argv) > 1:
        yil, hafta = (int(x) for x in sys.argv[1].split("-H"))
    elif (b := bekleyen(dt.datetime.now(dt.UTC).date())) is not None:
        yil, hafta = b
    else:
        print("portföy: yazılacak rapor yok (yazılmış ya da kanal raporları eksik)")
        return
    print(yaz(yil, hafta).relative_to(KOK))


if __name__ == "__main__":
    main()
