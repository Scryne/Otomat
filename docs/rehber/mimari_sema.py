"""Denetim formu için mimari şeması (PNG, 1600×900). Çalıştır: uv run python docs/rehber/mimari_sema.py"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ZEMIN, KUTU, KENAR, YAZI, SOLUK, VURGU = "#ffffff", "#eef3fb", "#3987e5", "#111827", "#4b5563", "#ee5a2a"

fig = plt.figure(figsize=(16, 9), dpi=100, facecolor=ZEMIN)
ax = fig.add_axes((0, 0, 1, 1))
ax.set_xlim(0, 16)
ax.set_ylim(0, 9)
ax.axis("off")


def kutu(x, y, w, h, baslik, alt, renk=KENAR):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.15", fc=KUTU, ec=renk, lw=2))
    ax.text(x + w / 2, y + h - 0.35, baslik, ha="center", va="top", fontsize=15, weight="bold", color=YAZI)
    ax.text(x + w / 2, y + h - 0.85, alt, ha="center", va="top", fontsize=11.5, color=SOLUK, linespacing=1.4)


def ok(x1, y1, x2, y2, etiket=""):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=18, lw=1.8, color=SOLUK))
    if etiket:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.18, etiket, ha="center", fontsize=10.5, color=SOLUK)


ax.text(0.5, 8.55, "Otomat: architecture (single user, single channel)", fontsize=22, weight="bold", color=YAZI)
ax.text(
    0.5,
    8.1,
    "Runs once a day in the operator's private GitHub Actions workflow. No user interface, no other users.",
    fontsize=12.5,
    color=SOLUK,
)

kutu(
    0.5,
    4.6,
    3.2,
    2.6,
    "Open data sources",
    "USGS earthquake catalog\nWorld Bank WDI\nEurostat\n(public, licensed, credited)",
)
kutu(
    4.5,
    4.6,
    3.4,
    2.6,
    "Data + script",
    "Facts computed by code\nLocal language model writes\nhook and title only\nFact-check gates",
)
kutu(8.7, 4.6, 3.2, 2.6, "Video renderer", "Map / chart animation\nSynthetic narration\nCaptions (5 languages)")
kutu(
    12.6, 4.6, 3.0, 2.6, "Operator's channel", "Earth in Numbers\n(one YouTube channel,\nowned by the operator)", VURGU
)

ok(3.7, 5.9, 4.5, 5.9, "fetch")
ok(7.9, 5.9, 8.7, 5.9)
ok(11.9, 5.9, 12.6, 5.9)

kutu(
    4.5,
    0.9,
    7.4,
    2.6,
    "YouTube API Services (operator's own OAuth token)",
    "videos.insert (scheduled upload) · videos.update (localized title/description)\n"
    "captions.insert (caption tracks) · channels.list (own channel only)\n"
    "YouTube Analytics reports.query: own videos' views, average view %",
    VURGU,
)
ok(10.3, 4.6, 9.3, 3.5, "upload")
ok(14.1, 4.6, 11.2, 3.0, "")
ok(5.6, 3.5, 6.0, 4.6, "own analytics → next topic")

kutu(12.6, 0.9, 3.0, 2.6, "Stored", "Own video IDs\nAggregated own analytics\nCredentials: encrypted\nGitHub secrets")

out = Path(__file__).with_name("otomat-mimari.png")
fig.savefig(out, facecolor=ZEMIN)
print(out)
