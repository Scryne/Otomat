"""Plan B haftalık yükleme sayfası: haftanın Release'indeki tüm `*_YUKLE.md` dosyalarından tek bir `HAFTA.md`.

Scryne haftada bir toplu yükler; günlük dosyadaki "üretimin ertesi günü" saati o ana kadar geçmiş olur. Bu yüzden
H hafta videoları H+1 haftasına günde bir planlanır (pazartesiden başlayarak, YAYIN_SAATI_UTC; Studio TR saati ister,
Türkiye UTC+3 sabit). Başlık birebir kopyalanmalı: analitik videoyu seçimle başlıktan eşleştirir (analitik.py).

Kullanım (Actions): `python -m otomat.yayin.hafta <YUKLE.md klasörü> teslim-2026-H40 > HAFTA.md`
"""

import datetime as dt
import re
import sys
from pathlib import Path

from otomat import kanal

YAYIN_SAATI_UTC = kanal.aktif().yayin_saati_utc  # kanal profili (earth: 14 UTC = 17:00 TR)
TR = dt.timezone(dt.timedelta(hours=3))
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def oku(metin: str) -> dict:
    """teslime_koy'un yazdığı YUKLE.md'yi ayrıştırır (eski başlık satırı "# <tarih>: yayın …" da olur)."""
    tarih = re.match(r"# (\d{4}-\d{2}-\d{2})", metin)
    baslik = re.search(r"^\*\*Başlık:\*\* (.+)$", metin, re.M)
    aciklama = re.search(r"\*\*Açıklama:\*\*\n\n```\n(.*?)\n```", metin, re.S)
    etiket = re.search(r"^\*\*Etiketler:\*\* (.*)$", metin, re.M)
    if not (tarih and baslik and aciklama and etiket):
        raise ValueError("YUKLE.md biçimi tanınmadı")
    return {
        "tarih": tarih[1],
        "baslik": baslik[1].strip(),
        "aciklama": aciklama[1],
        "etiketler": etiket[1].strip(),
    }


def takvim(etiket: str, adet: int) -> list[dt.datetime]:
    """teslim[-<kanal>]-YYYY-HWW → bir sonraki ISO haftasının pazartesisinden başlayarak günde bir yayın anı (UTC)."""
    m = re.fullmatch(r"teslim(?:-[a-z]+)?-(\d{4})-H(\d{2})", etiket)
    if not m:
        raise ValueError(f"etiket tanınmadı: {etiket}")
    pazartesi = dt.date.fromisocalendar(int(m[1]), int(m[2]), 1) + dt.timedelta(days=7)
    return [
        dt.datetime.combine(pazartesi + dt.timedelta(days=i), dt.time(YAYIN_SAATI_UTC), dt.UTC) for i in range(adet)
    ]


def olustur(yukleler: list[dict], etiket: str) -> str:
    videolar = sorted(yukleler, key=lambda y: y["tarih"])
    anlar = takvim(etiket, len(videolar))
    s = [
        f"# Bu haftanın yüklemesi ({etiket}): {len(videolar)} video",
        "",
        "Her video için: Studio → **Oluştur → Video yükle** → `<tarih>_video.mp4`. **Başlığı birebir yapıştır** (bot "
        "videoyu başlıktan tanır), açıklamayı yapıştır. Kitle: **Hayır, çocuklara özel değil**. Değiştirilmiş/yapay "
        "içerik: **Hayır** (veri animasyonu, gerçekçi değil). **Görünürlük → Planla** ile aşağıdaki TR saatini gir. "
        "Altyazı isteğe bağlı: Altyazılar → Dosya yükle → `<tarih>_<dil>.srt`.",
        "",
        "Planlanan saat geçmişse o videoyu **Herkese açık** yap (hemen yayınla); sıradakiler kendi saatinde kalır.",
        "",
    ]
    for i, (v, an) in enumerate(zip(videolar, anlar, strict=True), 1):
        tr = an.astimezone(TR)
        s += [
            f"## {i}. `{v['tarih']}_video.mp4` → {GUNLER[tr.weekday()]} {tr.strftime('%d.%m.%Y %H:%M')} (TR)",
            "",
            "Başlık:",
            "",
            "```",
            v["baslik"],
            "```",
            "",
            "Açıklama:",
            "",
            "```",
            v["aciklama"],
            "```",
            "",
            f"Etiketler (isteğe bağlı, Daha fazla göster → Etiketler): `{v['etiketler']}`",
            "",
        ]
    return "\n".join(s)


def main() -> None:
    kaynak, etiket = Path(sys.argv[1]), sys.argv[2]
    yukleler = [oku(p.read_text(encoding="utf-8")) for p in sorted(kaynak.glob("*_YUKLE.md"))]
    sys.stdout.reconfigure(encoding="utf-8")
    print(olustur(yukleler, etiket), end="")


if __name__ == "__main__":
    main()
