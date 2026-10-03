"""Audit formu kanıtları: site ekran görüntülerine URL şeridi ekle + OAuth/yükleme/analitik açıklama PDF'i.

Çalıştır: uv run python docs/rehber/kanit_uret.py
Ham ekran görüntüleri Edge headless ile alınır (docs/rehber/kanit/ham-*.png).
"""

import json
import subprocess
from pathlib import Path

import imageio_ffmpeg
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

KOK = Path(__file__).resolve().parents[2]
KANIT = Path(__file__).with_name("kanit")
SITE = "https://scryne.github.io/otomat-site/"
SAYFALAR = {"ana-sayfa": "", "gizlilik-politikasi": "privacy.html", "hizmet-sartlari": "terms.html"}


def url_seridi() -> None:
    font = ImageFont.truetype(str(KOK / "otomat/varliklar/fontlar/Barlow-Medium.ttf"), 26)
    for ad, yol in SAYFALAR.items():
        ham = Image.open(KANIT / f"ham-{ad}.png").convert("RGB")
        serit = 56
        yeni = Image.new("RGB", (ham.width, ham.height + serit), "#e5e7eb")
        yeni.paste(ham, (0, serit))
        d = ImageDraw.Draw(yeni)
        d.text((24, 14), f"Page URL: {SITE}{yol}", fill="#111827", font=font)
        yeni.save(KANIT / f"{ad}.png")


def kare(video: Path, saniye: float, cikti: Path) -> Path:
    subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y", "-ss", str(saniye), "-i", str(video),
         "-frames:v", "1", str(cikti)],
        check=True,
    )  # fmt: skip
    return cikti


def sayfa(pdf: PdfPages, baslik: str, paragraflar: list[str], gorsel: Path | None = None) -> None:
    fig = plt.figure(figsize=(11.69, 8.27), dpi=150)  # A4 yatay
    fig.text(0.05, 0.93, baslik, fontsize=20, weight="bold", color="#111827")
    y = 0.86
    genislik = 0.55 if gorsel else 0.9
    for p in paragraflar:
        import textwrap

        satirlar = textwrap.wrap(p, int(150 * genislik)) or [""]
        fig.text(0.05, y, "\n".join(satirlar), fontsize=10.5, va="top", color="#1f2937", family="monospace"
                 if p.startswith("  ") else "sans-serif", linespacing=1.45)  # fmt: skip
        y -= 0.028 * len(satirlar) + 0.02
    if gorsel:
        ax = fig.add_axes((0.64, 0.06, 0.32, 0.82))
        ax.imshow(Image.open(gorsel))
        ax.axis("off")
        ax.set_title("Frame of a generated video (1080×1920)", fontsize=9, color="#4b5563")
    pdf.savefig(fig)
    plt.close(fig)


def pdf_uret() -> Path:
    ornek = KOK / "calisma/uretim/2026-10-02/04_eurostat_en_dusuk_10_sdg_08_10_2025"
    meta = json.loads((ornek / "meta.json").read_text(encoding="utf-8"))
    karesi = kare(ornek / "video.mp4", 15, KANIT / "ornek-kare.png")
    cikti = KANIT / "otomat-oauth-yukleme-analitik.pdf"
    with PdfPages(cikti) as pdf:
        sayfa(
            pdf,
            "Otomat: OAuth 2.0 flow, scopes and revocation",
            [
                "Otomat is a private command-line tool with exactly one user: the channel owner. There is no sign-up, "
                "no web or mobile interface and no other accounts.",
                "Authorization: the owner runs the tool once on their own computer. It opens Google's standard OAuth "
                "consent screen (OAuth client type: Desktop app; installed-app flow with offline access). The owner "
                "signs in, selects the brand account of the channel Earth in Numbers and approves. The refresh token is "
                "stored as an encrypted GitHub Actions secret in the owner's private repository and is used only to act "
                "on that channel.",
                "Scopes requested and why:",
                "  youtube.upload              upload one video per day to the owner's channel",
                "  youtube.force-ssl           add caption tracks and localized titles/descriptions",
                "  yt-analytics.readonly       read the channel's own analytics to choose future topics",
                "Revocation: the owner can revoke access at any time at https://myaccount.google.com/connections "
                "(Third-party apps & services → Otomat → Delete all connections). The privacy policy explains this and "
                "the deletion of stored data: " + SITE + "privacy.html",
            ],
        )
        sayfa(
            pdf,
            "Otomat: upload (automated, no user interface)",
            [
                "There is no upload screen. A scheduled GitHub Actions job runs once a day: it reads open data (USGS, "
                "World Bank, Eurostat), computes the facts in code, renders a 9:16 map/chart animation with synthetic "
                "narration and captions, checks the text with fact-check gates, then calls videos.insert once.",
                "Example of the request body sent for one generated video:",
                f"  title:        {meta['baslik']}",
                "  categoryId:   28 (Science & Technology)",
                "  privacyStatus: private, publishAt: next day 14:00 UTC",
                "  defaultLanguage / defaultAudioLanguage: en",
                "  localizations: es, pt, de, fr (title + description)",
                f"  tags:         {', '.join(meta['etiketler'])}",
                "Then captions.insert is called once per language (en, es, pt, de, fr). Description excerpt:",
                "  " + meta["aciklama"].split("\n\n")[0][:110],
                "Every video credits its data source and license on screen and in the description.",
            ],
            karesi,
        )
        sayfa(
            pdf,
            "Otomat: analytics and reporting (internal only)",
            [
                "Otomat reads the YouTube Analytics API for the owner's own channel only: views, engagedViews and "
                "averageViewPercentage per video (dimension: video; filter: creatorContentType==SHORTS).",
                "Purpose: decide which topics and opening styles to make next. The numbers are stored in aggregated form "
                "in the owner's private repository and summarized in an internal weekly text report read only by the "
                "owner. No analytics data is displayed publicly, shared, or combined with data about other channels.",
                "No data about viewers is collected. No other channel is accessed.",
            ],
        )
    return cikti


if __name__ == "__main__":
    url_seridi()
    print(pdf_uret())
