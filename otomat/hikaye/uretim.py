"""Hikâye videosu: senaryo → sahne görselleri (paralel) → ses → kelime vurgulu altyazılı Ken Burns render → müzik.

Çıktı veri motoruyla aynı sözleşmededir (`calisma/gunluk/<tarih>/<anahtar>/`): video.mp4, ses.wav, meta.json
(baslik, aciklama, etiketler, altyazi, sure_sn …); yayin/hazirla.py ve yayın adımları değişmeden çalışır.
"""

import datetime as dt
import hashlib
import http.client
import json
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from concurrent.futures import FIRST_EXCEPTION, ThreadPoolExecutor, wait
from dataclasses import asdict
from functools import lru_cache
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
MUZIK_EN_AZ = 100_000  # bayt; incompetech parçaları birkaç MB


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
    return _font_yukle(str(KOK / kanal.aktif().font), boyut)


@lru_cache(maxsize=64)
def _font_yukle(yol: str, boyut: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(yol, boyut)  # uzun grupta küçültülmüş font her karede yeniden yükleniyordu


def altyazi_yaz(kare: Image.Image, grup: list[str], vurgu: int, font: ImageFont.FreeTypeFont, renk: str) -> None:
    d = ImageDraw.Draw(kare)
    kelimeler = [w.upper() for w in grup]

    def olc(f: ImageFont.FreeTypeFont) -> tuple[int, float, float]:
        kalin = max(6, f.size // 9)
        # kontur kelimenin iki yanına taşar: boşluk kontur kadar açılır (IM Fell'in dar boşluğunda kelimeler bitişti)
        bosluk = d.textlength(" ", font=f) + kalin
        return kalin, bosluk, sum(d.textlength(w, font=f) for w in kelimeler) + bosluk * (len(kelimeler) - 1)

    kalin, bosluk, genislik = olc(font)
    if genislik > G - 90:
        font = _font(int(font.size * (G - 90) / genislik))
        kalin, bosluk, genislik = olc(font)
    x = (G - genislik) / 2
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
    try:
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
    except BaseException:
        # bozuk kare ya da kopan boru: ffmpeg açık stdin'le asılı kalmasın, yarım dosya bir sonraki koşuya kalmasın
        proc.kill()
        proc.wait()
        cikti.unlink(missing_ok=True)
        raise
    return cikti


def muzik_sec(mood: str, tohum: str) -> tuple[Path, str]:
    """Tohumun seçtiği parça; indirilemezse (incompetech kapalı) aynı mood'un sıradaki parçası. Video müziksiz çıkmaz:
    açıklamadaki atıf hangi parça çaldıysa onu yazar. Kanalda olmayan mood (format değişiminden önce yazılmış senaryo:
    Orbit'in çocuk dönemindeki "playful") ilk mood'a düşer: KeyError render'dan sonra bütün koşuyu düşürüyordu."""
    muzik = kanal.aktif().muzik
    parcalar = muzik.get(mood) or next(iter(muzik.values()))
    bas = sum(map(ord, tohum)) % len(parcalar)
    son = None
    for ad in parcalar[bas:] + parcalar[:bas]:
        yol = MUZIK_DIZIN / f"{ad}.mp3"
        if yol.exists():
            return yol, ad
        yol.parent.mkdir(parents=True, exist_ok=True)
        istek = urllib.request.Request(MUZIK_URL.format(urllib.parse.quote(ad)), headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(istek, timeout=60) as yanit:
                veri = yanit.read()
        except (OSError, http.client.HTTPException) as e:  # URLError, zaman aşımı, kopan bağlantı
            son = e
            continue
        # hata sayfası ya da kesik gövde mp3 diye önbelleğe girerse birleştirme o parçada hep düşerdi
        if len(veri) < MUZIK_EN_AZ or not (veri[:3] == b"ID3" or veri[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")):
            son = RuntimeError(f"{ad}: mp3 değil ({len(veri)} bayt)")
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
        govde = f'{sc.satirlar[-1]}\n\nAesop\'s fable "{ad}", retold (public domain).'
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
    """Karakter başına o sahnedeki en son görünüş. Senaryo istemi ikinci değişimin görünüşüne birincinin hâlâ geçerli
    olanını da yazdırır ("a tailless red fox wearing a small golden crown"): sahne sırasıyla son değişim kazanır, model
    çıktısının sırası değil."""
    istemler = []
    sirali = sorted(sc.degisimler, key=lambda d: d["sahne"])
    for i, g in enumerate(sc.gorseller, 1):
        durumlar = {d["kim"]: d["gorunum"] for d in sirali if i >= d["sahne"]}
        istemler.append(gorsel_istemi(stil, sc.dunya, sc.oyuncular, g, durumlar))
    return istemler


def bicim_imzasi(tur: str, k: kanal.Kanal) -> str:
    """Senaryoyu üreten istemlerin ve kanalın mood kümesinin imzası. Kayıtlı senaryo yalnız aynı imzayla sürdürülür:
    format değişince (K-24'te Orbit çocuk masalından genel kitleye döndü) eski istemle yazılmış senaryo yeni kanala
    çıkmasın, eski mood'u müzik seçimini düşürmesin."""
    parcalar = [senaryo.ISTEM[tur], senaryo.SAHNE_ISTEMI, senaryo.GORSEL_KURALI[tur], senaryo.HAKEM_ISTEM[tur],
                *sorted(k.muzik), *k.kaliplar]  # fmt: skip
    return hashlib.sha256("\0".join(parcalar).encode()).hexdigest()[:12]


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
    imza = bicim_imzasi(paket.tur, k)
    try:
        d = json.loads(yol.read_text(encoding="utf-8"))
        if (d["anahtar"], d["hash"], d.get("bicim")) == (paket.anahtar, paket.hash, imza):
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
    kayit = {"anahtar": paket.anahtar, "hash": paket.hash, "bicim": imza, "kalip": kalip, "senaryo": asdict(sc),
             "istemler": istemler}  # fmt: skip
    yol.write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
    return sc, kalip, istemler


YAZI_YENIDEN = 3  # video başına en çok yeniden çizim (kare ~156 neuron)
YAZISIZ = "Every surface in the picture is blank and wordless."


def yeniden_ciz(istemler: list[str], i: int, yol: Path, tohum: int, dizin: Path, plan=None) -> Path:
    """Görünüş ya da yazı yüzünden yeniden çizim: yazı taşıyan yan cümle düşer (Bartman skor tabelası, 10-12) ve
    sahne ilk çizimdeki karakter referansını yine alır; yoksa yeniden çizilen kare referanstan kayardı."""
    cumle, ek = _referans_eki(plan, dizin, i)
    return cf.gorsel(f"{senaryo.yazisiz(istemler[i])}{cumle} {YAZISIZ}", yol, tohum, **ek)


def yazilari_ayikla(istemler: list[str], dizin: Path, taban: int, plan=None) -> dict:
    """OCR'da yazı çıkan sahne yeni tohumla yeniden çizilir (hak sahne sırasıyla). Yeniden çizim de yazılıysa daha az
    yazılı olan kalır. Kayıt meta.json'a: `ilk` (çizimde yazı çıkanlar), `son` (videoda kalanlar), `yeniden`,
    `cizilen` (karesi değişen sahneler: görünüş denetimi onlara yeniden bakar)."""
    kayit: dict = {"ilk": {}, "son": {}, "yeniden": 0, "cizilen": []}
    for i in range(len(istemler)):
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
            yeniden_ciz(istemler, i, yol, taban + 10 * i + 5, dizin, plan)
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
            kayit["cizilen"].append(i)
        if yeni:
            kayit["son"][i] = yeni
    return kayit


DURUM_YENIDEN = 3  # video başına en çok yeniden çizim (değişen görünüş tutmadı)
DURUM_GUVEN = 0.6  # görme modeli bundan az eminse kare reddedilmez


class DurumHatasi(RuntimeError):
    """Hikâyede değişen görünüş yeniden çizimden sonra da karede tutmadı: hikâye düşer, sıradaki denenir. Tutmayan
    kare masalın konusunu bozar (10-15 Orbit: kuyruğunu kaybeden tilkinin kuyruğu 3 karede yerindeydi)."""


def _ayni_soru(a: dict, b: dict) -> bool:
    return a["soru"].strip().lower() == b["soru"].strip().lower()


def etkin_sorular(sc: senaryo.Senaryo) -> dict[int, list[dict]]:
    """Sahne (0'dan) → o karede sınanacak değişimler. Görünüş birikir: tilki 3. sahnede kuyruğunu kaybedip 4.'de taç
    takınca 4-7'de ikisi de sorulur (eskiden taç başlayınca kuyruk sorusu bırakılıyordu, Felix hatası geri gelirdi).
    Aynı karakterin sonraki değişimi aynı soruyu soruyorsa (görünüşü geri alıyor) öncekinin penceresi orada biter."""
    etkin: dict[int, list[dict]] = {}
    for d in sc.degisimler:
        bitis = min((e["sahne"] for e in sc.degisimler if e["kim"] == d["kim"] and e["sahne"] > d["sahne"]
                     and _ayni_soru(e, d)), default=len(sc.gorseller) + 1)  # fmt: skip
        for i in range(d["sahne"] - 1, bitis - 1):
            if _sahnede(d["kim"], sc.gorseller[i]):
                etkin.setdefault(i, []).append(d)
    return etkin


def durumlari_denetle(
    sc: senaryo.Senaryo,
    istemler: list[str],
    dizin: Path,
    taban: int,
    plan=None,
    sahneler: set[int] | None = None,
    ayirmayan: list[str] | None = None,
) -> dict:
    """Değişimden sonraki, karakterin adının geçtiği her sahne görme modeline sorulur; beklenmeyen cevap (yeterince
    emin) → yeni tohumla yeniden çizim, sonra o karenin BÜTÜN etkin soruları yeniden sorulur (bir değişimin geçmesi
    öbürünün tutmayan kaydını silmesin; yeniden çizim öbür görünüşü bozabilir). Önce soru değişimden önceki son karede
    sınanır: orada da beklenen cevap emin çıkıyorsa soru iki görünüşü ayırmıyor (ya da `expected` ters), o değişim
    denetlenmez; yoksa doğru kareler boşuna yeniden çizilip hikâye düşerdi. Model yanıt vermezse soru denetlenmemiş
    sayılır, video yine çıkar. `sahneler` + `ayirmayan`: yalnız bu sahnelere yeniden bakılır, sınama yapılmaz (OCR'ın
    yeniden çizdiği kareler)."""
    kayit: dict = {"soru": 0, "yeniden": 0, "tutmayan": {}, "hata": 0, "ayirmayan": list(ayirmayan or [])}

    def sor(yol: Path, soru: str) -> tuple[bool, float] | None:
        kayit["soru"] += 1
        try:
            return cf.gorsel_sor(yol, soru)
        except cf.KotaHatasi:
            raise
        except cf.CFHatasi:
            kayit["hata"] += 1
            return None

    if sahneler is None:
        for d in sc.degisimler:
            onceki = [i for i in range(d["sahne"] - 1) if _sahnede(d["kim"], sc.gorseller[i])]
            if not onceki or d["soru"] in kayit["ayirmayan"]:
                continue
            c = sor(dizin / f"sahne_{onceki[-1]}.jpg", d["soru"])
            # az emin tek cevap bütün değişimin denetimini kapatmasın (kare denetimi de az emin cevabı saymıyor)
            if c and c[0] == d["beklenen"] and c[1] >= DURUM_GUVEN:
                kayit["ayirmayan"].append(d["soru"])
    for i, degisimler in sorted(etkin_sorular(sc).items()):
        sorular = [d for d in degisimler if d["soru"] not in kayit["ayirmayan"]]
        if not sorular or (sahneler is not None and i not in sahneler):
            continue
        yol, deneme = dizin / f"sahne_{i}.jpg", 0
        while True:
            tutmayan = []
            for d in sorular:
                c = sor(yol, d["soru"])
                if c is not None and c[0] != d["beklenen"] and c[1] >= DURUM_GUVEN:
                    tutmayan.append(d["soru"])
            if not tutmayan:
                kayit["tutmayan"].pop(str(i), None)
                break
            kayit["tutmayan"][str(i)] = tutmayan
            if kayit["yeniden"] >= DURUM_YENIDEN:
                break
            kayit["yeniden"] += 1
            deneme += 1
            yol.unlink()
            # OCR yeniden çizimiyle aynı yazısız istem: yazı taşıyan yan cümle geri gelmesin
            yeniden_ciz(istemler, i, yol, taban + 10 * i + 7 + deneme, dizin, plan)
    if kayit["tutmayan"]:
        raise DurumHatasi(f"değişen görünüş karede tutmadı: {kayit['tutmayan']}")
    return kayit


REFERANS_CUMLESI = (
    "{ad} looks exactly as in the reference image: same species, face, colors and clothes; only the pose, action, "
    "camera and setting change."
)


def referans_plani(sc: senaryo.Senaryo) -> tuple[int, str, frozenset[int]] | None:
    """(kaynak sahne, ana karakter, referansla çizilecek sahneler) ya da None. Ana karakter kadronun ilki; kaynak,
    adının geçtiği ilk sahne (masalda ilk kare zaten onun yakın portresi). Profilde `referans` kapalıysa None.
    Karakterin görünüşü değiştikten sonraki sahneler referans almaz: "looks exactly as in the reference" kuyruklu ilk
    kareyi kuyruksuz sahneye dayatırdı."""
    if not kanal.aktif().referans or not sc.oyuncular:
        return None
    ad = sc.oyuncular[0].partition(":")[0].strip()
    degisim = min((d["sahne"] - 1 for d in sc.degisimler if d["kim"] == ad), default=len(sc.gorseller))
    gecen = [i for i, g in enumerate(sc.gorseller) if _sahnede(ad, g)]
    if len(gecen) < 2 or not (refli := frozenset(i for i in gecen[1:] if i < degisim)):
        return None
    return gecen[0], ad, refli


def _referans_eki(plan, dizin: Path, i: int) -> tuple[str, dict]:
    """(istem eki, cf.gorsel argümanı): `i` planda referanslı sahneyse kaynak kare ve referans cümlesi."""
    if not plan or i not in plan[2]:
        return "", {}
    return " " + REFERANS_CUMLESI.format(ad=plan[1]), {"referanslar": (dizin / f"sahne_{plan[0]}.jpg",)}


def sahneleri_ciz(
    istemler: list[str], dizin: Path, taban: int, plan: tuple[int, str, frozenset[int]] | None = None
) -> list[Path]:
    """Sahneler PARALEL çizilir. Biri kota ya da filtreye takılınca kuyruktaki çizimler iptal edilir: `ex.map` hata
    sonrasında da kalan istekleri gönderiyordu (kota doluyken boşa istek, filtrede boşa neuron). `plan` varsa önce
    ana karakterin ilk karesi çizilir, karakterin geçtiği sonraki sahneler onu referans alır (tür, renk ve kıyafet
    kareden kareye kayıyordu; Cock and Jewel'de tavuk her karede başkaydı)."""
    ex = ThreadPoolExecutor(PARALEL)
    try:
        if plan:
            cf.gorsel(istemler[plan[0]], dizin / f"sahne_{plan[0]}.jpg", taban + 10 * plan[0])
        isler = []
        for i, istem in enumerate(istemler):
            cumle, ek = _referans_eki(plan, dizin, i)
            isler.append(ex.submit(cf.gorsel, istem + cumle, dizin / f"sahne_{i}.jpg", taban + 10 * i, **ek))
        # ilk hatada dön: sırayla `result()` beklemek, sıradaki işin hatasını görene kadar kuyruğu çalıştırıyordu
        wait(isler, return_when=FIRST_EXCEPTION)
        return [f.result() for f in isler]
    except BaseException:
        ex.shutdown(wait=True, cancel_futures=True)
        raise
    finally:
        ex.shutdown(wait=True)


def uret(paket: OlguPaketi, kalip: str, sablon: str, dizin: Path, tohum: str) -> dict:
    k = kanal.aktif()
    dizin.mkdir(parents=True, exist_ok=True)
    cf.NEURON["toplam"] = 0.0
    t0 = time.time()
    sc, kalip, istemler = senaryo_al(paket, kalip, dizin)
    t_senaryo = time.time()
    taban = sum(map(ord, paket.anahtar)) % 100_000
    plan = referans_plani(sc)
    gorseller = sahneleri_ciz(istemler, dizin, taban, plan)
    # önce görünüş, sonra yazı: OCR son kareye bakar (görünüş yeniden çizimi yazıyı geri getirebiliyordu). OCR'ın
    # yeniden çizdiği kare görünüşü bozabilir (yeni tohumda kuyruk geri gelir): o kareler bir kez daha sorulur
    durum_kaydi = durumlari_denetle(sc, istemler, dizin, taban, plan)
    yazi_kaydi = yazilari_ayikla(istemler, dizin, taban, plan)
    if yazi_kaydi.get("cizilen") and sc.degisimler:
        ek = durumlari_denetle(sc, istemler, dizin, taban + 1, plan, set(yazi_kaydi["cizilen"]),
                               durum_kaydi["ayirmayan"])  # fmt: skip
        for alan in ("soru", "yeniden", "hata"):
            durum_kaydi[alan] += ek[alan]
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
        "referans": {"kaynak": plan[0], "ad": plan[1], "sahneler": sorted(plan[2])} if plan else None,
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
