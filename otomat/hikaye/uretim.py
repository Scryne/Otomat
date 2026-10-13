"""Hikâye videosu: senaryo → sahne görselleri (paralel) → ses → kelime vurgulu altyazılı Ken Burns render → müzik.

Çıktı veri motoruyla aynı sözleşmededir (`calisma/gunluk/<tarih>/<anahtar>/`): video.mp4, ses.wav, meta.json
(baslik, aciklama, etiketler, altyazi, sure_sn …); yayin/hazirla.py ve yayın adımları değişmeden çalışır.
"""

import datetime as dt
import json
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from otomat import kanal
from otomat.ayarlar import KOK
from otomat.hikaye import cf, hizala, kaynaklar, senaryo, yazi
from otomat.ses import Parca, _kokoro
from otomat.veri import OlguPaketi

G, Y, FPS = 1080, 1920, 30
ARA = 0.3  # satırlar arası sessizlik (sn)
KUYRUK = 1.2  # son satırdan sonra son kare
KIRPMA = 1.16  # suluboya kâğıt kenarı kadrajın dışında kalsın
ZOOM = 0.10
ALTYAZI_Y = 0.66
GRUP = 3  # ekranda aynı anda en çok kelime
PARALEL = 4  # aynı anda görsel isteği
MUZIK_URL = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/{}.mp3"
MUZIK_ATIF = '"{}" Kevin MacLeod (incompetech.com), licensed under Creative Commons: By Attribution 4.0'
MUZIK_DIZIN = KOK / "modeller" / "muzik"  # Actions'ta modeller önbelleğinde


def seslendir(satirlar: list[str], cikti: Path) -> tuple[float, list[Parca]]:
    k = kanal.aktif()
    kokoro = _kokoro()
    dil = "en-gb" if k.ses.startswith("b") else "en-us"
    parcalar, sesler, an, sr = [], [], 0.0, 24000
    for i, s in enumerate(satirlar):
        ornek, sr = kokoro.create(s, voice=k.ses, speed=k.hiz, lang=dil)
        sure = len(ornek) / sr
        parcalar.append(Parca(round(an, 3), round(an + sure, 3), s))
        ara = ARA if i < len(satirlar) - 1 else KUYRUK
        sesler += [ornek, np.zeros(int(ara * sr), dtype=np.float32)]
        an += sure + ara
    tum = np.concatenate(sesler)
    cikti.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(cikti), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(tum, -1, 1) * 32767).astype(np.int16).tobytes())
    return len(tum) / sr, parcalar


def kelime_zamanlari(
    parcalar: list[Parca], gercek: list[tuple[float, str]] | None = None
) -> list[tuple[float, float, list[str], int]]:
    """(baş, son, grup kelimeleri, vurgulu kelime sırası). `gercek`: Whisper kelimeleri (hizala.py); yoksa satır içinde
    harf sayısıyla orantılı."""
    sonuc = []
    for p, bas in zip(parcalar, hizala.baslangiclar(parcalar, gercek), strict=True):
        kelimeler = p.metin.split()
        bit = [*bas[1:], p.son]
        for g in range(0, len(kelimeler), GRUP):
            grup = kelimeler[g : g + GRUP]
            for j in range(len(grup)):
                sonuc.append((bas[g + j], bit[g + j], grup, j))
    return sonuc


def _font(boyut: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(KOK / kanal.aktif().font), boyut)


def altyazi_yaz(kare: Image.Image, grup: list[str], vurgu: int, font: ImageFont.FreeTypeFont, renk: str) -> None:
    d = ImageDraw.Draw(kare)
    kelimeler = [w.upper() for w in grup]
    bosluk = d.textlength(" ", font=font)
    genislik = sum(d.textlength(w, font=font) for w in kelimeler) + bosluk * (len(kelimeler) - 1)
    if genislik > G - 90:
        font = _font(int(font.size * (G - 90) / genislik))
        bosluk = d.textlength(" ", font=font)
        genislik = sum(d.textlength(w, font=font) for w in kelimeler) + bosluk * (len(kelimeler) - 1)
    x = (G - genislik) / 2
    kalin = max(6, font.size // 9)
    for j, w in enumerate(kelimeler):
        d.text((x, Y * ALTYAZI_Y), w, font=font, fill=renk if j == vurgu else "white", stroke_width=kalin,
               stroke_fill="black")  # fmt: skip
        x += d.textlength(w, font=font) + bosluk


def kenar_kirp(img: Image.Image, esik: int = 228, pay: int = 6) -> Image.Image:
    """Suluboya modelinin çizdiği açık renkli kâğıt kenarını keser: kenardan içeri, ortalaması kâğıt kadar açık olan
    satır/sütunlar atılır (kırpma tek başına yetmiyordu, S12). Resmin yarısından fazlası gidecekse dokunmaz."""
    a = np.asarray(img.convert("L"), dtype=np.float32)
    satir, sutun = a.mean(axis=1) < esik, a.mean(axis=0) < esik
    if not satir.any() or not sutun.any():
        return img
    y0, y1 = satir.argmax(), len(satir) - satir[::-1].argmax()
    x0, x1 = sutun.argmax(), len(sutun) - sutun[::-1].argmax()
    if (y1 - y0) * (x1 - x0) < 0.5 * a.size:
        return img
    return img.crop((x0 + pay, y0 + pay, x1 - pay, y1 - pay))


# Kamera hareketi: (zoom başı, zoom sonu, yatay kayma başı→sonu, dikey kayma başı→sonu); kayma, kadraj dışında kalan
# payın oranı (-1 sol/üst kenar, +1 sağ/alt kenar). Hep aynı merkez zoom'u tekdüze görünüyordu; ilk sahne hep içeri
# girer (kanca), gerisi sahne sırasıyla döner.
HAREKETLER = {
    "iceri": (0.0, 1.0, (0, 0), (0, 0)),
    "disari": (1.0, 0.0, (0, 0), (0, 0)),
    "saga": (0.5, 0.5, (-0.9, 0.9), (0, 0)),
    "sola": (0.5, 0.5, (0.9, -0.9), (0, 0)),
    "asagi": (0.3, 0.7, (0, 0), (-0.9, 0.6)),
}
SIRA = ["iceri", "saga", "disari", "asagi", "sola"]


def hareket(i: int) -> str:
    return SIRA[i % len(SIRA)]


def sahne_kareleri(img: Image.Image, n: int, ad: str = "iceri"):
    z0, z1, (x0, x1), (y0, y1) = HAREKETLER[ad]
    img = kenar_kirp(img.convert("RGB"))
    o = max(G / img.width, Y / img.height) * KIRPMA
    buyuk = img.resize((round(img.width * o), round(img.height * o)), Image.LANCZOS)
    for k in range(n):
        t = k / max(n - 1, 1)
        t = t * t * (3 - 2 * t)
        z = 1.0 + ZOOM * (z0 + (z1 - z0) * t)
        w, h = round(G * KIRPMA / z), round(Y * KIRPMA / z)
        px, py = (buyuk.width - w) / 2, (buyuk.height - h) / 2
        sx, sy = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        cx, cy = round(px * (1 + sx)), round(py * (1 + sy))
        yield buyuk.crop((cx, cy, cx + w, cy + h)).resize((G, Y), Image.BILINEAR)


def render(
    gorseller: list[Path],
    parcalar: list[Parca],
    sure: float,
    cikti: Path,
    gercek: list[tuple[float, str]] | None = None,
) -> Path:
    k = kanal.aktif()
    kelimeler = kelime_zamanlari(parcalar, gercek)
    font = _font(k.font_boyu)
    proc = subprocess.Popen(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
         f"{G}x{Y}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(cikti)],
        stdin=subprocess.PIPE,
    )  # fmt: skip
    kare_no, ki = 0, 0
    for i in range(len(parcalar)):
        son = parcalar[i + 1].bas if i + 1 < len(parcalar) else sure
        with Image.open(gorseller[i]) as img:
            for kare in sahne_kareleri(img, round(son * FPS) - kare_no, hareket(i)):
                an = kare_no / FPS
                while ki < len(kelimeler) - 1 and kelimeler[ki][1] <= an:
                    ki += 1
                bas, bit, grup, vurgu = kelimeler[ki]
                if bas <= an < bit:
                    altyazi_yaz(kare, grup, vurgu, font, k.vurgu)
                proc.stdin.write(kare.tobytes())
                kare_no += 1
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg render hatası")
    return cikti


def muzik_sec(mood: str, tohum: str) -> tuple[Path, str]:
    """Tohumun seçtiği parça; indirilemezse (incompetech kapalı) aynı mood'un sıradaki parçası. Video müziksiz çıkmaz:
    açıklamadaki atıf hangi parça çaldıysa onu yazar."""
    parcalar = kanal.aktif().muzik[mood]
    bas = sum(map(ord, tohum)) % len(parcalar)
    son = None
    for ad in parcalar[bas:] + parcalar[:bas]:
        yol = MUZIK_DIZIN / f"{ad}.mp3"
        if yol.exists():
            return yol, ad
        yol.parent.mkdir(parents=True, exist_ok=True)
        istek = urllib.request.Request(MUZIK_URL.format(urllib.parse.quote(ad)), headers={"User-Agent": "Mozilla/5.0"})
        try:
            veri = urllib.request.urlopen(istek, timeout=60).read()
        except (urllib.error.URLError, TimeoutError) as e:
            son = e
            continue
        gecici = yol.with_suffix(".tmp")
        gecici.write_bytes(veri)
        gecici.replace(yol)
        return yol, ad
    raise RuntimeError(f"'{mood}' müziklerinin hiçbiri indirilemedi: {son}")


SES_LUFS = -14.0  # anlatıcı; limiter sonrası karışım ≈ -14 LUFS (YouTube'un oynatma hedefi; sessiz video yükseltilmez)


def birlestir(sessiz: Path, wav: Path, muzik: Path, sure: float, cikti: Path) -> Path:
    """Anlatıcı ve müzik ayrı ayrı loudness hedefine çekilir: parçaların kendi seviyeleri çok farklı (sabit çarpanla
    "Heartbreaking" -47,5 LUFS'ta kalıp duyulmuyordu, video da -21,6 LUFS'tu; 2026-10-08 ölçümü)."""
    hedef = kanal.aktif().muzik_lufs
    subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-v", "error", "-i", str(sessiz), "-i", str(wav), "-stream_loop", "-1",
         "-i", str(muzik), "-filter_complex",
         f"[1:a]loudnorm=I={SES_LUFS}:TP=-2:LRA=7[v];"
         f"[2:a]atrim=0:{sure + 1:.2f},loudnorm=I={hedef}:TP=-8:LRA=11,afade=t=in:d=0.4,"
         f"afade=t=out:st={max(sure - 1.6, 0):.2f}:d=1.5[m];"
         "[v][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89:level=false,aresample=48000[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", f"{sure:.2f}",
         str(cikti)],
        check=True,
    )  # fmt: skip
    return cikti


def aciklama(paket: OlguPaketi, sc: senaryo.Senaryo, muzik_adi: str) -> str:
    etiket = " ".join(dict.fromkeys("#" + "".join(w[:1].upper() + w[1:] for w in e.split()) for e in paket.etiketler))
    ad = paket.gorsel["baslik"]
    if paket.tur == "masal":
        govde = f'{sc.satirlar[-1]}\n\nA gentle retelling of Aesop\'s fable "{ad}" (public domain).'
    else:
        govde = f'{sc.satirlar[0]}\n\nSource: Wikipedia, "{ad}" ({paket.kaynak.lisans}) {paket.kaynak.url}'
    return (
        f"{govde}\nIllustrations made with AI. Narration: Kokoro TTS.\n"
        f"Music: {MUZIK_ATIF.format(muzik_adi)}\nhttps://creativecommons.org/licenses/by/4.0/\n\n{etiket}"
    )


def _sahnede(ad: str, sahne: str) -> bool:
    return bool(re.search(rf"\b{re.escape(ad.strip())}\b", sahne, re.I))


def gorsel_istemi(
    stil: str, dunya: str, oyuncular: list[str], sahne: str, durumlar: dict[str, str] | None = None
) -> str:
    """Sahnede adı geçen her karakterin sabit tarifi istemde durur: model tarifi sahneye kopyalamayı unutunca horoz her
    karede başka renk çıkıyordu (Orbit, 10-09). `durumlar` (ad → o sahnedeki yeni görünüş) tariften sonra gelir:
    sahne metni "his tail gone" deyince klein kuyruğu yine çiziyordu (S13)."""
    tarifler = []
    for o in oyuncular:
        ad, _, tarif = o.partition(":")
        if tarif.strip() and _sahnede(ad, sahne) and tarif.strip() not in sahne:
            tarifler.append(f"{ad.strip()} is {tarif.strip().rstrip('.')}.")
    for ad, gorunum in (durumlar or {}).items():
        if _sahnede(ad, sahne):
            tarifler.append(f"{ad} is now {gorunum}.")
    # klein ara sıra iki panelli (çizgi roman) görsel çiziyordu: tek kare olduğu açıkça söylenir
    return " ".join([f"{stil}. A single full-frame scene, not a comic, no panels. {dunya}", *tarifler, sahne])


def istemleri_kur(stil: str, sc: senaryo.Senaryo) -> list[str]:
    istemler = []
    for i, g in enumerate(sc.gorseller, 1):
        durumlar = {d["kim"]: d["gorunum"] for d in sc.degisimler if i >= d["sahne"]}
        istemler.append(gorsel_istemi(stil, sc.dunya, sc.oyuncular, g, durumlar))
    return istemler


SENARYO = "senaryo.json"
ESKI_CIKTILAR = (
    "sahne_*.jpg",
    "sahne_*.tmp",
    "yazili_*.jpg",
    "*.srt",
    "yerel.json",
    "meta.json",
    "video.mp4",
    "ses.wav",
)


def senaryo_al(paket: OlguPaketi, kalip: str, dizin: Path) -> tuple[senaryo.Senaryo, str, list[str]]:
    """(senaryo, kalıp, görsel istemleri). Hakemden geçmiş senaryo klasörde duruyorsa (kota kesintisi; gunluk önceki
    koşunun artifact'ından getirir) yeniden kullanılır ve aynı istemle çizilmiş sahne görselleri kalır: kota ikinci kez
    harcanmaz. Yoksa yeni senaryo yazılır ve klasördeki eski çıktılar silinir: önceki senaryonun görselleri yeni
    senaryonun sahnelerine karışmasın (aynı slot aynı hikâyeyi yeniden seçince öyle olacaktı)."""
    k = kanal.aktif()
    yol = dizin / SENARYO
    try:
        d = json.loads(yol.read_text(encoding="utf-8"))
        if (d["anahtar"], d["hash"]) == (paket.anahtar, paket.hash):
            sc = senaryo.Senaryo(**d["senaryo"])
            istemler = istemleri_kur(k.stil, sc)
            for i, eski in enumerate(d.get("istemler", [])):
                if i >= len(istemler) or eski != istemler[i]:  # kanal stili değişmiş: o sahne yeniden çizilir
                    (dizin / f"sahne_{i}.jpg").unlink(missing_ok=True)
            return sc, d.get("kalip", kalip), istemler
    except (OSError, ValueError, KeyError, TypeError):
        pass
    for desen in ESKI_CIKTILAR:
        for eski in dizin.glob(desen):
            eski.unlink()
    kaynak = kaynaklar.metin(paket)
    sc = senaryo.yaz(paket.tur, paket.gorsel["baslik"], kaynak, paket.konu, kalip, list(k.muzik))
    istemler = istemleri_kur(k.stil, sc)
    kayit = {"anahtar": paket.anahtar, "hash": paket.hash, "kalip": kalip, "senaryo": asdict(sc), "istemler": istemler}
    yol.write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
    return sc, kalip, istemler


YAZI_YENIDEN = 3  # video başına en çok yeniden çizim (kare ~156 neuron)
YAZISIZ = "Every surface in the picture is blank and wordless."


def yazilari_ayikla(istemler: list[str], dizin: Path, taban: int) -> dict:
    """OCR'da yazı çıkan sahne yeni tohumla yeniden çizilir (hak sahne sırasıyla). Yeniden çizim de yazılıysa daha az
    yazılı olan kalır. Kayıt meta.json'a: `ilk` (çizimde yazı çıkanlar), `son` (videoda kalanlar), `yeniden`."""
    kayit: dict = {"ilk": {}, "son": {}, "yeniden": 0}
    for i, istem in enumerate(istemler):
        yol = dizin / f"sahne_{i}.jpg"
        bulgu = yazi.oku(yol)
        if bulgu is None:
            return {"ocr": "yok"}
        if not bulgu:
            continue
        kayit["ilk"][i] = bulgu
        if kayit["yeniden"] >= YAZI_YENIDEN:
            kayit["son"][i] = bulgu
            continue
        kayit["yeniden"] += 1
        eski = dizin / f"yazili_{i}.jpg"  # sahne_* değil: kabul ve yarım üretim sahne dosyalarını sayıyor
        yol.replace(eski)
        try:
            # istem aynı nesneyi istedikçe ek cümle tutmuyor (Bartman skor tabelası, 10-12): o yan cümle düşer
            cf.gorsel(f"{senaryo.yazisiz(istem)} {YAZISIZ}", yol, taban + 10 * i + 5)
        except cf.KotaHatasi:
            eski.replace(yol)  # sonraki koşu senaryoyu sürdürür, bu sahneyi yeniden dener
            raise
        except cf.CFHatasi:
            eski.replace(yol)
            kayit["son"][i] = bulgu
            continue
        yeni = yazi.oku(yol) or []
        if yeni and len("".join(yeni)) >= len("".join(bulgu)):
            eski.replace(yol)
            yeni = bulgu
        else:
            eski.unlink()
        if yeni:
            kayit["son"][i] = yeni
    return kayit


DURUM_YENIDEN = 3  # video başına en çok yeniden çizim (değişen görünüş tutmadı)
DURUM_GUVEN = 0.6  # görme modeli bundan az eminse kare reddedilmez


class DurumHatasi(RuntimeError):
    """Hikâyede değişen görünüş yeniden çizimden sonra da karede tutmadı: hikâye düşer, sıradaki denenir. Tutmayan
    kare masalın konusunu bozar (10-15 Orbit: kuyruğunu kaybeden tilkinin kuyruğu 3 karede yerindeydi)."""


def durumlari_denetle(sc: senaryo.Senaryo, istemler: list[str], dizin: Path, taban: int) -> dict:
    """Değişimden sonraki, karakterin adının geçtiği her sahne görme modeline sorulur; beklenmeyen cevap (yeterince
    emin) → yeni tohumla yeniden çizim. Önce soru değişimden önceki son karede sınanır: orada da beklenen cevap
    çıkıyorsa soru iki görünüşü ayırmıyor (ya da `expected` ters yazılmış), o değişim denetlenmez; yoksa doğru kareler
    boşuna yeniden çizilip hikâye düşerdi. Model yanıt vermezse kare denetlenmemiş sayılır, video yine çıkar."""
    kayit: dict = {"soru": 0, "yeniden": 0, "tutmayan": {}, "hata": 0, "ayirmayan": []}

    def sor(yol: Path, soru: str) -> tuple[bool, float] | None:
        kayit["soru"] += 1
        try:
            return cf.gorsel_sor(yol, soru)
        except cf.KotaHatasi:
            raise
        except cf.CFHatasi:
            kayit["hata"] += 1
            return None

    for d in sc.degisimler:
        onceki = [i for i in range(d["sahne"] - 1) if _sahnede(d["kim"], sc.gorseller[i])]
        if onceki and (c := sor(dizin / f"sahne_{onceki[-1]}.jpg", d["soru"])) and c[0] == d["beklenen"]:
            kayit["ayirmayan"].append(d["soru"])
            continue
        for i in range(d["sahne"] - 1, len(sc.gorseller)):
            if not _sahnede(d["kim"], sc.gorseller[i]):
                continue
            yol, deneme = dizin / f"sahne_{i}.jpg", 0
            while True:
                if (c := sor(yol, d["soru"])) is None:
                    break
                cevap, guven = c
                if cevap == d["beklenen"] or guven < DURUM_GUVEN:
                    kayit["tutmayan"].pop(str(i), None)
                    break
                kayit["tutmayan"][str(i)] = d["soru"]
                if kayit["yeniden"] >= DURUM_YENIDEN:
                    break
                kayit["yeniden"] += 1
                deneme += 1
                yol.unlink()
                cf.gorsel(istemler[i], yol, taban + 10 * i + 7 + deneme)
    if kayit["tutmayan"]:
        raise DurumHatasi(f"değişen görünüş karede tutmadı: {kayit['tutmayan']}")
    return kayit


def uret(paket: OlguPaketi, kalip: str, sablon: str, dizin: Path, tohum: str) -> dict:
    k = kanal.aktif()
    dizin.mkdir(parents=True, exist_ok=True)
    cf.NEURON["toplam"] = 0.0
    t0 = time.time()
    sc, kalip, istemler = senaryo_al(paket, kalip, dizin)
    t_senaryo = time.time()
    taban = sum(map(ord, paket.anahtar)) % 100_000
    with ThreadPoolExecutor(PARALEL) as ex:
        gorseller = list(
            ex.map(lambda a: cf.gorsel(a[1], dizin / f"sahne_{a[0]}.jpg", taban + 10 * a[0]), enumerate(istemler))
        )
    yazi_kaydi = yazilari_ayikla(istemler, dizin, taban)
    durum_kaydi = durumlari_denetle(sc, istemler, dizin, taban)
    t_gorsel = time.time()
    sure, parcalar = seslendir(sc.satirlar, dizin / "ses.wav")
    try:
        gercek = hizala.whisper_kelimeleri(dizin / "ses.wav")
    except Exception:  # noqa: BLE001 — vurgu orantılı tahmine döner, video yine çıkar
        gercek = None
    sessiz = render(gorseller, parcalar, sure, dizin / "sessiz.mp4", gercek)
    muzik, muzik_adi = muzik_sec(sc.mood, tohum + paket.anahtar)
    video = birlestir(sessiz, dizin / "ses.wav", muzik, sure, dizin / "video.mp4")
    sessiz.unlink()
    meta = {
        "baslik": sc.baslik,
        "aciklama": aciklama(paket, sc, muzik_adi),
        "etiketler": paket.etiketler,
        "mfk": k.mfk,
        "paket": {"anahtar": paket.anahtar, "hash": paket.hash, "kol": paket.kol, "tur": paket.tur},
        "secim": {"kalip": kalip, "sablon": sablon, "kaynak": {"senaryo": cf.METIN_MODELI, "gorsel": cf.GORSEL_MODELI}},
        "kanca": sc.satirlar[0],
        "cumleler": sc.satirlar,
        "senaryo": {
            "mood": sc.mood,
            "dunya": sc.dunya,
            "oyuncular": sc.oyuncular,
            "gorseller": sc.gorseller,
            "hakem_turlari": sc.turlar,
            "gorsel_onarim": sc.gorsel_onarim,
            "cikarilan": sc.cikarilan,
            "degisimler": sc.degisimler,
        },  # fmt: skip
        "muzik": muzik_adi,
        "yazi": yazi_kaydi,
        "durum": durum_kaydi,
        "vurgu": "whisper" if gercek else "orantili",
        "altyazi": [asdict(p) for p in parcalar],
        "sure_sn": round(sure, 2),
        "neuron": round(cf.NEURON["toplam"]),
        "zaman_sn": {
            "senaryo": round(t_senaryo - t0, 1),
            "gorsel": round(t_gorsel - t_senaryo, 1),
            "ses_render": round(time.time() - t_gorsel, 1),
        },
        "uretildi": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "video": str(video.relative_to(KOK)) if video.is_relative_to(KOK) else str(video),
    }
    (dizin / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta


def main() -> None:
    """Yerel deneme (yayın yok):
    `OTOMAT_KANAL=uzay uv run python -m otomat.hikaye.uretim "ezop:The Fox And The Grapes"`."""
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("anahtar", help="ör. 'wiki:Dancing plague of 1518' ya da 'ezop:The Lion And The Mouse'")
    p.add_argument("--kalip", default=None)
    p.add_argument("--dizin", type=Path, default=KOK / "calisma" / "hikaye_deneme")
    a = p.parse_args()
    paketler, _ = kaynaklar.topla()
    paket = next((x for x in paketler if x.anahtar == a.anahtar), None)
    if paket is None:
        raise SystemExit(f"havuzda (ya da süzgeçten geçen) yok: {a.anahtar}")
    kalip = a.kalip or kanal.aktif().kaliplar[0]
    dizin = a.dizin / kanal.aktif().id / "".join(c if c.isalnum() else "_" for c in a.anahtar)[:60]
    try:
        meta = uret(paket, kalip, "illustrasyon", dizin, "deneme")
    except senaryo.SenaryoHatasi as e:
        for i, tur in enumerate(e.sorunlar):
            print(f"tur {i}:", *(f"\n   {n}: {r}" for n, r in tur))
        raise SystemExit(f"senaryo düştü: {a.anahtar}") from e
    print(json.dumps({k: meta[k] for k in ("baslik", "cumleler", "sure_sn", "neuron", "zaman_sn", "muzik")},
                     ensure_ascii=False, indent=1))  # fmt: skip
    print(dizin / "video.mp4")


if __name__ == "__main__":
    main()
