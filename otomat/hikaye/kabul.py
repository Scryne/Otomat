"""Hikâye videosunun yayın kabulü: üretim klasörü yayına hazır mı? (Faz 14 kabul kriteri, yayından önce son kapı)

    uv run python -m otomat.hikaye.kabul calisma/gunluk/<tarih>/<anahtar>/meta.json [--dizin <video klasörü>]

Reddederken `RED: <neden>` ile çıkar (çıkış kodu 1). Kontroller meta.json'un değerlerine ve yanındaki dosyalara bakar:
boş/yer tutucu/yarım/tekrarlı meta, sessiz ya da yanlış boyutlu video, eksik sahne görseli, hakemden geçmemiş senaryo,
kaynak ve müzik atfı olmayan açıklama, kanalın MFK ayarıyla çelişen bayrak yayına çıkamaz.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

from otomat import kanal

SURE = (20.0, 60.0)  # Shorts: 60 sn altı; 20 sn altı hikâye olamaz
SATIR = (6, 9)
SEMBOL = re.compile(r"[°%&$€£#@/+=<>~^*|]")
CAGRI = re.compile(r"\b(subscribe|like (?:and|&) subscribe|comment below|link in (?:the )?bio)\b", re.I)


class Red(Exception):
    pass


def bilgi_ayikla(cikti: str) -> dict:
    """`ffmpeg -i` dökümünden ffprobe biçiminde özet: akışlar (tür, codec, boyut) ve süre."""
    akislar = []
    for tur, codec, kalan in re.findall(r"Stream #\S+: (Video|Audio): (\w+)(.*)", cikti):
        akis = {"codec_type": tur.lower(), "codec_name": codec}
        if tur == "Video" and (b := re.search(r", (\d{2,5})x(\d{2,5})\b", kalan)):
            akis |= {"width": int(b[1]), "height": int(b[2])}
        akislar.append(akis)
    s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", cikti)
    sure = int(s[1]) * 3600 + int(s[2]) * 60 + float(s[3]) if s else 0.0
    return {"streams": akislar, "format": {"duration": str(sure)}}


def _ffprobe(video: Path) -> dict:
    """imageio-ffmpeg'in ffmpeg'iyle okunur: Actions sunucusunda ffprobe yok (2026-10-09'da 5 hikâye bu yüzden
    reddedildi)."""
    import imageio_ffmpeg

    if not video.exists():
        raise FileNotFoundError(video)
    cikti = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(video)], capture_output=True, text=True
    ).stderr  # çıktı dosyası verilmediği için çıkış kodu 1, döküm yine de tam
    return bilgi_ayikla(cikti)


def denetle(meta_yolu: Path, video_bilgisi=_ffprobe, dizin: Path | None = None) -> list[str]:
    """Hata listesi (boşsa kabul). `dizin`: video ve sahne dosyalarının klasörü (varsayılan meta.json'un klasörü)."""
    d = dizin or meta_yolu.parent
    try:
        meta = json.loads(meta_yolu.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [f"meta.json okunamadı: {e}"]
    if not isinstance(meta, dict):
        return ["meta.json bir nesne değil"]
    h: list[str] = []
    k = kanal.aktif()

    baslik = meta.get("baslik")
    if not isinstance(baslik, str) or not 10 <= len(baslik.strip()) <= 100:
        h.append(f"başlık 10-100 karakter olmalı: {baslik!r}")
    satirlar = meta.get("cumleler")
    if not isinstance(satirlar, list) or not all(isinstance(s, str) and len(s.split()) >= 3 for s in satirlar):
        return [*h, "cümleler eksik ya da 3 kelimeden kısa"]
    if not SATIR[0] <= len(satirlar) <= SATIR[1]:
        h.append(f"{len(satirlar)} satır; {SATIR[0]}-{SATIR[1]} olmalı")
    if len({s.lower() for s in satirlar}) != len(satirlar):
        h.append("tekrarlanan satır var")
    if any(SEMBOL.search(s) for s in satirlar):
        h.append("anlatıcının okuyamayacağı sembol var")
    if any(CAGRI.search(s) for s in [baslik or "", *satirlar]):
        h.append("abone/yorum çağrısı var")
    if meta.get("kanca") != satirlar[0]:
        h.append("kanca ilk satır değil")

    turlar = (meta.get("senaryo") or {}).get("hakem_turlari")
    if not isinstance(turlar, list) or not turlar or turlar[-1] != []:
        h.append("senaryo hakemden temiz geçmemiş (son tur boş değil)")

    aciklama = meta.get("aciklama")
    if not isinstance(aciklama, str) or "https://" not in aciklama:
        h.append("açıklamada kaynak bağlantısı yok")
    elif "Kevin MacLeod" not in aciklama or "creativecommons.org/licenses/by/4.0" not in aciklama:
        h.append("açıklamada müzik atfı (CC BY 4.0) yok")
    if not meta.get("etiketler"):
        h.append("etiket yok")
    if meta.get("mfk") is not k.mfk:
        h.append(f"MFK bayrağı ({meta.get('mfk')!r}) kanalla ({k.mfk}) çelişiyor")

    altyazi = meta.get("altyazi")
    if not isinstance(altyazi, list) or len(altyazi) != len(satirlar):
        h.append("altyazı parçası sayısı satır sayısıyla aynı değil")
    else:
        try:
            zaman = [(float(p["bas"]), float(p["son"])) for p in altyazi]
        except (KeyError, TypeError, ValueError):
            zaman = []
            h.append("altyazı zamanları bozuk")
        if zaman and not all(b < s for b, s in zaman):
            h.append("altyazıda süresi sıfır ya da ters parça var")
        if zaman and not all(zaman[i][1] <= zaman[i + 1][0] for i in range(len(zaman) - 1)):
            h.append("altyazı parçaları üst üste biniyor")
        if [p.get("metin") for p in altyazi] != satirlar:
            h.append("altyazı metni cümlelerle aynı değil")

    sure = meta.get("sure_sn")
    if not isinstance(sure, (int, float)) or not SURE[0] <= sure <= SURE[1]:
        h.append(f"süre {sure!r}; {SURE[0]:.0f}-{SURE[1]:.0f} sn olmalı")

    sahneler = sorted(d.glob("sahne_*.jpg"))
    if len(sahneler) != len(satirlar):
        h.append(f"{len(sahneler)} sahne görseli, {len(satirlar)} satır")

    video = d / "video.mp4"
    if not video.exists() or video.stat().st_size < 200_000:
        h.append("video.mp4 yok ya da çok küçük")
        return h
    try:
        v = video_bilgisi(video)
    except Exception as e:  # noqa: BLE001
        return [*h, f"video okunamadı: {e}"]
    akislar = {s["codec_type"]: s for s in v.get("streams", [])}
    g = akislar.get("video", {})
    if (g.get("width"), g.get("height")) != (1080, 1920):
        h.append(f"video {g.get('width')}x{g.get('height')}; 1080x1920 olmalı")
    if "audio" not in akislar:
        h.append("video sessiz")
    vsure = float(v.get("format", {}).get("duration", 0))
    if isinstance(sure, (int, float)) and abs(vsure - sure) > 0.5:
        h.append(f"video {vsure:.1f} sn, meta {sure} sn")
    return h


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("meta", type=Path)
    p.add_argument("--dizin", type=Path, help="video ve sahne dosyalarının klasörü (varsayılan meta'nın klasörü)")
    a = p.parse_args()
    hatalar = denetle(a.meta, dizin=a.dizin)
    if hatalar:
        sys.exit("RED: " + "; ".join(hatalar))
    print("KABUL")


if __name__ == "__main__":
    main()
