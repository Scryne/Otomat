"""Film üretimi uçtan uca, adım adım ve önbellekli: her adım çıktısını `calisma/film/<slug>/` altına yazar, var olanı
atlar. Böylece kusurlu tek sahne silinip yalnız o yeniden üretilir.

    uv run python -m otomat.film.uretim filmler/<slug>/senaryo.json [adım]

Adımlar: karakter, sahne, i2v, ses, kurgu, kapak (varsayılan: hepsi). GPU adımları için ComfyUI açık olmalı.
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from otomat.ayarlar import KOK
from otomat.film import anlatim, comfy, kurgu, senaryo

GORSEL = (1920, 1088)  # 16'nın katı; kurgu 1080'e kırpar
I2V = {"w": 832, "h": 480, "kare": 49, "adim": 10}
MUZIK_URL = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/{}.mp3"
MUZIK_DIZIN = KOK / "modeller" / "muzik"
MUZIK_ATIF = '"{}" Kevin MacLeod (incompetech.com), licensed under Creative Commons: By Attribution 4.0'
MUZIK = {  # Kevin MacLeod, CC BY 4.0; adları kanal profillerinde canlı doğrulanmış parçalar
    "tragic": ["Heartbreaking", "Lightless Dawn", "Gymnopedie No 1"],
    "mysterious": ["Spellbound", "Investigations", "Darkling", "Curse of the Scarab"],
    "epic": ["Sovereign", "Volatile Reaction"],
    "funny": ["Sneaky Snitch", "Fluffing a Duck", "Merry Go"],
}


def dizin(film: senaryo.Film) -> Path:
    return KOK / "calisma" / "film" / film.slug


def _log(*a) -> None:
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def karakterler(film: senaryo.Film, d: Path) -> dict[str, Path]:
    yollar = {}
    for ad in film.karakterler:
        yol = d / "karakter" / f"{ad}.png"
        if not yol.exists():
            comfy.gorsel(senaryo.karakter_istemi(film, ad), yol, 1024, 1024, tohum=1)
            _log("karakter", ad)
        yollar[ad] = yol
    return yollar


def sahne_yolu(d: Path, i: int) -> Path:
    return d / "sahne" / f"{i:03d}.png"


def sahneler(film: senaryo.Film, d: Path, kartlar: dict[str, Path]) -> None:
    for i, s in enumerate(film.sahneler()):
        yol = sahne_yolu(d, i)
        if yol.exists():
            continue
        comfy.gorsel(
            senaryo.sahne_istemi(film, s), yol, *GORSEL, tohum=1000 + i, referanslar=[kartlar[k] for k in s.kim]
        )
        _log("sahne", i)


def i2v_dizini(d: Path, i: int) -> Path:
    return d / "i2v" / f"{i:03d}"


def hareketler(film: senaryo.Film, d: Path) -> None:
    for i, s in enumerate(film.sahneler()):
        hedef = i2v_dizini(d, i)
        if s.hareket != "i2v" or (hedef / f"{I2V['kare'] - 1:04d}.png").exists():
            continue
        comfy.i2v(sahne_yolu(d, i), senaryo.i2v_istemi(s), hedef, tohum=3 + i, **I2V)
        _log("i2v", i)


def _muzik(ad: str) -> Path:
    yol = MUZIK_DIZIN / f"{ad}.mp3"
    if not yol.exists():
        yol.parent.mkdir(parents=True, exist_ok=True)
        istek = urllib.request.Request(MUZIK_URL.format(urllib.parse.quote(ad)), headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(istek, timeout=60) as y:
            veri = y.read()
        if len(veri) < 100_000:
            raise RuntimeError(f"{ad}: mp3 değil ({len(veri)} bayt)")
        yol.write_bytes(veri)
    return yol


def muzik_plani(film: senaryo.Film) -> list[str]:
    """Bölüm başına parça: aynı mood'da sıradaki, art arda aynı parça yok."""
    sayac: dict[str, int] = {}
    plan = []
    for bo in film.bolumler:
        liste = MUZIK[bo.mood]
        ad = liste[sayac.get(bo.mood, 0) % len(liste)]
        if plan and plan[-1] == ad:
            sayac[bo.mood] = sayac.get(bo.mood, 0) + 1
            ad = liste[sayac[bo.mood] % len(liste)]
        sayac[bo.mood] = sayac.get(bo.mood, 0) + 1
        plan.append(ad)
    return plan


def kurgula(film: senaryo.Film, d: Path) -> dict:
    bloklar = film.bloklar()
    denetim = d / "ses" / "denetim.json"
    try:
        wav, zamanlar, kayit = anlatim.seslendir([(bi, b.anlatim) for bi, b in bloklar], film.ses, d / "ses")
    except anlatim.AnlatimHatasi as h:
        denetim.write_text(json.dumps(h.kayit, ensure_ascii=False, indent=1), encoding="utf-8")
        raise
    denetim.write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
    sahne_no = 0
    blok_sahneleri = []
    for _, b in bloklar:
        liste = []
        for s in b.sahneler:
            kaynak = i2v_dizini(d, sahne_no) if s.hareket == "i2v" else sahne_yolu(d, sahne_no)
            liste.append((s.hareket, kaynak, s.yazi))
            sahne_no += 1
        blok_sahneleri.append(liste)
    bolum_no = [bi for bi, _ in bloklar]
    cekim = kurgu.cekimler(bolum_no, zamanlar, blok_sahneleri, [bo.ad for bo in film.bolumler])
    son = cekim[-1].son
    plan = muzik_plani(film)
    bolum_bas = [0.0] + [c.bas for c in cekim if c.tur == "kart"]
    muzikler = [
        (bas, bolum_bas[i + 1] if i + 1 < len(bolum_bas) else son, _muzik(ad))
        for i, (bas, ad) in enumerate(zip(bolum_bas, plan, strict=True))
    ]
    _log("render başlıyor", f"{son:.0f} sn", len(cekim), "çekim")
    sessiz = kurgu.sessiz_video(cekim, d / "sessiz.mp4", son)
    video = kurgu.miks(sessiz, wav, muzikler, son, d / "video.mp4")
    bilgi = {
        "sure": round(son, 2),
        "anlatim_sure": zamanlar[-1].son,
        "bolum_bas": bolum_bas,
        "muzik": plan,
        "en_kotu_parca": max((k["fark"] for k in kayit), default=0),
    }
    (d / "kurgu.json").write_text(json.dumps(bilgi, ensure_ascii=False, indent=1), encoding="utf-8")
    (d / "aciklama.txt").write_text(aciklama(film, bolum_bas, plan), encoding="utf-8")
    _log("video", video)
    return bilgi


def _zaman(sn: float) -> str:
    sn = int(sn)
    return f"{sn // 60:02d}:{sn % 60:02d}"


def aciklama(film: senaryo.Film, bolum_bas: list[float], muzik: list[str]) -> str:
    bolumler = "\n".join(f"{_zaman(b)} {bo.ad}" for b, bo in zip(bolum_bas, film.bolumler, strict=True))
    kaynaklar = "\n".join(f"- {k['ad']}: {k['url']}" for k in film.kaynaklar)
    atif = "\n".join(MUZIK_ATIF.format(ad) for ad in dict.fromkeys(muzik))
    return (
        f"{film.baslik}\n\nChapters\n{bolumler}\n\nSources\n{kaynaklar}\n\nMusic\n{atif}\n\n"
        "Illustrations, animation and narration were made with AI tools; the story and every fact in it follow the "
        "sources above.\n"
    )


def kapak(film: senaryo.Film, d: Path, kartlar: dict[str, Path]) -> Path:
    zemin = d / "kapak_zemin.png"
    if not zemin.exists():
        # sahnelerle aynı istem kuralı (kart tarifi dahil): ayrı istemle Klondike kapağında gözlük düştü, burun çıktı
        sahne = senaryo.Sahne(film.kapak_sahne, "iceri", film.kapak_kim, kisi=True)
        comfy.gorsel(
            senaryo.sahne_istemi(film, sahne),
            zemin,
            *GORSEL,
            tohum=77,
            referanslar=[kartlar[k] for k in film.kapak_kim],
        )
    img = Image.open(zemin).convert("RGB").resize((1280, 725), Image.Resampling.LANCZOS).crop((0, 2, 1280, 722))
    golge = Image.new("L", img.size, 0)
    ImageDraw.Draw(golge).rectangle((0, 0, 1280, 250), fill=170)
    img = Image.composite(Image.new("RGB", img.size), img, golge.filter(ImageFilter.GaussianBlur(60)))
    f = ImageFont.truetype(str(kurgu.FONT / "LuckiestGuy-Regular.ttf"), 150)
    while f.getlength(film.kapak_yazi) > 1180:
        f = ImageFont.truetype(str(kurgu.FONT / "LuckiestGuy-Regular.ttf"), f.size - 6)
    ImageDraw.Draw(img).text(
        (640, 125), film.kapak_yazi, font=f, fill="white", anchor="mm", stroke_width=8, stroke_fill="black"
    )
    yol = d / "kapak.jpg"
    img.save(yol, quality=92)
    return yol


def main() -> None:
    film = senaryo.oku(Path(sys.argv[1]))
    adim = sys.argv[2] if len(sys.argv) > 2 else "hepsi"
    d = dizin(film)
    d.mkdir(parents=True, exist_ok=True)
    _log(film.slug, f"{film.kelime()} kelime, {len(film.sahneler())} sahne")
    gpu = adim in ("hepsi", "karakter", "sahne", "i2v", "kapak")
    if gpu and not comfy.hazir():
        raise SystemExit(f"ComfyUI kapalı ({comfy.SUNUCU})")
    kartlar = karakterler(film, d) if gpu else {}
    if adim in ("hepsi", "sahne"):
        sahneler(film, d, kartlar)
    if adim in ("hepsi", "i2v"):
        # FLUX (+ Qwen 7,5 GB) ile Wan (+ UMT5 6,3 GB) aynı anda RAM'de kalınca 24 GB yetmiyor (10-17'de süreç öldü)
        comfy.bosalt()
        hareketler(film, d)
        comfy.bosalt()
    if adim in ("hepsi", "kapak"):
        _log("kapak", kapak(film, d, kartlar))
    if adim in ("hepsi", "ses", "kurgu"):
        comfy.bosalt()
        kurgula(film, d)


if __name__ == "__main__":
    main()
