import json, math, os
from gen import f
NAVY, BLUE, ORANGE, INK, SEQ1 = "#0b1220", "#4a8fe6", "#ee5a2a", "#f2f5f9", "#184f95"
TITLE = "<title>Earth in Numbers</title>"
os.makedirs("out", exist_ok=True)

def bands(n, band, gap, cx=112, cy=128, end=244):
    """Şeritli küre: n bant, ortadaki bant küreden taşar. (yollar, taşan bant yolu)"""
    R = (n*band + (n-1)*gap)/2
    xs = lambda y: math.sqrt(max(0.0, R*R-(y-cy)**2))
    norm, acc = [], None
    for i in range(n):
        y1 = cy - R + i*(band+gap); y2 = y1 + band; l1, l2 = xs(y1), xs(y2)
        if i == n//2:
            r = band/2
            acc = (f"M{f(cx-l1)} {f(y1)}H{f(end-r)}A{f(r)} {f(r)} 0 0 1 {f(end-r)} {f(y2)}"
                   f"H{f(cx-l2)}A{f(R)} {f(R)} 0 0 1 {f(cx-l1)} {f(y1)}Z")
        else:
            norm.append(f"M{f(cx-l1)} {f(y1)}H{f(cx+l1)}A{f(R)} {f(R)} 0 0 1 {f(cx+l2)} {f(y2)}"
                        f"H{f(cx-l2)}A{f(R)} {f(R)} 0 0 1 {f(cx-l1)} {f(y1)}Z")
    return " ".join(norm), acc

FULL = bands(5, 28, 13)        # ana çizim
SMALL = bands(3, 46, 19)       # 32 px ve altı için kesim

def sym_g(b, base, accent):
    return f'<path fill="{base}" d="{b[0]}"/><path fill="{accent}" d="{b[1]}"/>'

def svgw(body, vb):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">{TITLE}{body}</svg>\n'

def write(name, s): open(f"out/{name}", "w", encoding="utf-8").write(s)

# Sembol: siyah master, renkli (koyu zemin / açık zemin), küçük kesim
write("sembol-siyah.svg", svgw(f'<path d="{FULL[0]} {FULL[1]}"/>', "0 0 256 256"))
write("sembol-kucuk-siyah.svg", svgw(f'<path d="{SMALL[0]} {SMALL[1]}"/>', "0 0 256 256"))
write("sembol-koyu-zemin.svg", svgw(sym_g(FULL, BLUE, ORANGE), "0 0 256 256"))
write("sembol-acik-zemin.svg", svgw(sym_g(FULL, SEQ1, ORANGE), "0 0 256 256"))
write("sembol-kucuk-koyu-zemin.svg", svgw(sym_g(SMALL, BLUE, ORANGE), "0 0 256 256"))

# Yazı: Barlow Condensed SemiBold, yollar
wm = json.load(open("wm.json")); tg = json.load(open("tag.json"))
def text_g(j, cap_px, x, y_base, fill):
    s = cap_px / j["cap"]
    return f'<path fill="{fill}" transform="translate({f(x)} {f(y_base)}) scale({f(s)})" d="{j["d"]}"/>', j["width"]*s

def lockup(base, accent, ink, bg=None):
    cap = 96; gap = 52
    t, w = text_g(wm, cap, 244 + gap, 128 + cap/2, ink)
    W = 244 + gap + w - 16 + 8
    body = (f'<rect x="16" y="0" width="{f(W)}" height="256" fill="{bg}"/>' if bg else "") + sym_g(FULL, base, accent) + t
    return svgw(body, f"16 0 {f(W)} 256"), W
for name, args in (("yatay-koyu-zemin.svg", (BLUE, ORANGE, INK)), ("yatay-acik-zemin.svg", (SEQ1, ORANGE, NAVY)),
                   ("yatay-siyah.svg", ("#000", "#000", "#000"))):
    write(name, lockup(*args)[0])

def stacked(base, accent, ink):
    cap = 64; t, w = text_g(wm, cap, 0, 0, ink)
    W = max(w, 228) + 0
    sx = (W - 228)/2 - 16
    body = f'<g transform="translate({f(sx)} 0)">{sym_g(FULL, base, accent)}</g>'
    t, _ = text_g(wm, cap, 0, 256 + 40 + cap, ink)
    pad = 24
    return svgw(body + t, f"{-pad} {32 - pad} {f(W + 2*pad)} {f(256 + 40 + cap - 32 + 2 + 2*pad)}")
write("dikey-koyu-zemin.svg", stacked(BLUE, ORANGE, INK)); write("dikey-acik-zemin.svg", stacked(SEQ1, ORANGE, NAVY))

# YouTube profil resmi 800×800 (daireye kırpılır): lacivert zemin, sembol daire içinde optik merkezde
s = 2.1; bw, bh = 228*s, 192*s
tx, ty = 400 - (16 + 114)*s, 400 - 128*s - 6
write("youtube-profil.svg", f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800">{TITLE}<rect width="800" height="800" fill="{NAVY}"/>'
      f'<g transform="translate({f(tx)} {f(ty)}) scale({s})">{sym_g(FULL, BLUE, ORANGE)}</g></svg>\n')

# YouTube banner 2560×1440; her cihazda görünen güvenli alan ortadaki 1546×423
L, LW = lockup(BLUE, ORANGE, INK)
lh = 150; ls = lh/256; lw = LW*ls
tcap = 30; tagw = tg["width"] * tcap/tg["cap"]
blk = lh + 34 + tcap
y0 = 720 - blk/2
inner = L.split(TITLE)[1].rsplit("</svg>", 1)[0]
tag, _ = text_g(tg, tcap, 1280 - tagw/2, y0 + lh + 34 + tcap, "#a9b4c4")
write("youtube-banner.svg", f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2560 1440">{TITLE}<rect width="2560" height="1440" fill="{NAVY}"/>'
      f'<g transform="translate({f(1280 - lw/2)} {f(y0)}) scale({f(ls)}) translate(-16 0)">{inner}</g>{tag}</svg>\n')
print("lockup W", LW, "banner lockup w", lw, "tag w", tagw)
