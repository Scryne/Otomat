"""S4 spike: USGS son 30 gün M4.5+ depremlerini 9:16 animasyona çevir, render süresini ölç."""
import json, subprocess, time, urllib.request, datetime as dt
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import imageio_ffmpeg

OUT = Path(__file__).parent / "out"
W, H, FPS, SEC = 1080, 1920, 30, 30
FF = imageio_ffmpeg.get_ffmpeg_exe()

def get(url, name):
    p = OUT / name
    if not p.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "otomat-spike"})
        p.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    return json.loads(p.read_text(encoding="utf-8"))

quakes = get("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_month.geojson", "usgs.json")
land = get("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_land.geojson", "land.json")

ev = []
for f in quakes["features"]:
    lon, lat, _ = f["geometry"]["coordinates"]
    ev.append((f["properties"]["time"] / 1000, lon, lat, f["properties"]["mag"]))
ev.sort()
ev = np.array(ev)
t0, t1 = ev[0, 0], ev[-1, 0]

polys = []
for f in land["features"]:
    g = f["geometry"]
    rings = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    for poly in rings:
        polys.append(np.array(poly[0]))

BG, LAND, ACC, TXT = "#0b0f14", "#1c2530", "#ff5a36", "#e8edf2"
fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=BG)
ax = fig.add_axes([0.0, 0.33, 1.0, 0.34], facecolor=BG)
ax.add_collection(PolyCollection(polys, facecolor=LAND, edgecolor="none"))
ax.set_xlim(-180, 180); ax.set_ylim(-60, 85); ax.axis("off")
fig.text(0.5, 0.86, "Every M4.5+ earthquake", ha="center", color=TXT, fontsize=54, weight="bold")
fig.text(0.5, 0.815, "in the last 30 days", ha="center", color=TXT, fontsize=40, alpha=0.8)
cnt = fig.text(0.5, 0.22, "", ha="center", color=ACC, fontsize=110, weight="bold")
day = fig.text(0.5, 0.17, "", ha="center", color=TXT, fontsize=34, alpha=0.8)
fig.text(0.5, 0.04, "Data: USGS", ha="center", color=TXT, fontsize=22, alpha=0.5)
old = ax.scatter([], [], s=[], c=ACC, alpha=0.35, linewidths=0)
new = ax.scatter([], [], s=[], facecolors="none", edgecolors=ACC, linewidths=2)

n = FPS * SEC
proc = subprocess.Popen([FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS),
                         "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(OUT / "s4.mp4")],
                        stdin=subprocess.PIPE)
start = time.time()
for i in range(n):
    tc = t0 + (t1 - t0) * min(1, i / (n * 0.85))
    seen = ev[ev[:, 0] <= tc]
    size = (seen[:, 3] - 4) ** 2 * 60 + 8
    old.set_offsets(seen[:, 1:3]); old.set_sizes(size)
    fresh = seen[seen[:, 0] > tc - (t1 - t0) / 30]
    age = (tc - fresh[:, 0]) / ((t1 - t0) / 30)
    new.set_offsets(fresh[:, 1:3]); new.set_sizes(((fresh[:, 3] - 4) ** 2 * 60 + 8) * (1 + 6 * age))
    cnt.set_text(f"{len(seen)}")
    day.set_text(dt.datetime.utcfromtimestamp(tc).strftime("%b %d"))
    fig.canvas.draw()
    proc.stdin.write(fig.canvas.buffer_rgba().tobytes())
proc.stdin.close(); proc.wait()
print(f"{len(ev)} deprem, {n} kare, render {time.time() - start:.1f} sn")
