import math
def f(v): return f"{v:.2f}".rstrip("0").rstrip(".")
def svg(body, w=256, h=256):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">{body}</svg>\n'

# ---- A: ufuk çubukları — dünya kavsi + üzerinde radyal üç çubuk, ortadaki en uzun (vurgu)
def concept_a(accent="#000"):
    cx, cy, R = 128, 404, 200
    parts = [f'<circle cx="{cx}" cy="{cy}" r="{R}"/>']
    w = 28
    for ang, h, col in ((-16, 58, "#000"), (0, 118, accent), (16, 84, "#000")):
        a = math.radians(ang)
        # çubuk tabanı kavsin 10 birim içinde, yönü merkezden dışarı
        bx, by = cx + (R-10)*math.sin(a), cy - (R-10)*math.cos(a)
        parts.append(f'<rect x="{f(bx-w/2)}" y="{f(by-(h+10))}" width="{w}" height="{h+10}" rx="5" '
                     f'transform="rotate({ang} {f(bx)} {f(by)})" fill="{col}"/>')
    return svg("".join(parts))

# ---- B: şeritli küre — 5 bant, orta bant küreden taşar (ölçek dışı sayı)
def concept_b(accent="#000", base=None):
    cx, cy, R = 112, 128, 96
    band, gap = 28, 13
    tops = [cy-R + i*(band+gap) for i in range(5)]
    out = []
    for i, y1 in enumerate(tops):
        y2 = y1 + band
        def xs(y): 
            d = max(0.0, R*R-(y-cy)**2); return math.sqrt(d)
        l1, l2 = xs(y1), xs(y2)
        if i == 2:  # orta bant: sol kavis, sağda yuvarlak uçlu uzun çubuk
            end = 244; r = band/2
            d = (f"M{f(cx-l1)} {f(y1)}H{f(end-r)}A{f(r)} {f(r)} 0 0 1 {f(end-r)} {f(y2)}"
                 f"H{f(cx-l2)}A{R} {R} 0 0 1 {f(cx-l1)} {f(y1)}Z")
            out.append(f'<path d="{d}" fill="{accent}"/>')
        else:
            d = (f"M{f(cx-l1)} {f(y1)}H{f(cx+l1)}A{R} {R} 0 0 1 {f(cx+l2)} {f(y2)}"
                 f"H{f(cx-l2)}A{R} {R} 0 0 1 {f(cx-l1)} {f(y1)}Z")
            out.append(f'<path d="{d}"' + (f' fill="{base}"' if base else '') + '/>')
    return svg("".join(out))

# ---- C: grid-diyez — dünyanın enlem/boylam ızgarası bir # (sayı işareti)
def concept_c(accent=None):
    cx = cy = 128; Ro, Ri = 102, 80
    ring = (f'<path fill-rule="evenodd" d="M{cx} {cy-Ro}A{Ro} {Ro} 0 1 1 {cx} {cy+Ro}A{Ro} {Ro} 0 1 1 {cx} {cy-Ro}Z'
            f'M{cx} {cy-Ri}A{Ri} {Ri} 0 1 0 {cx} {cy+Ri}A{Ri} {Ri} 0 1 0 {cx} {cy-Ri}Z"/>')
    t, off, ext = 20, 27, 90  # bar kalınlığı, merkezden uzaklık, uç yarıçapı (halkanın içinde biter)
    bars = []
    for s in (-1, 1):  # yatay çubuklar
        y = cy + s*off
        half = math.sqrt(ext**2 - (off)**2)
        bars.append(f'<rect x="{f(cx-half)}" y="{f(y-t/2)}" width="{f(2*half)}" height="{t}"/>')
    sl = math.radians(14)
    for s in (-1, 1):  # eğik dikey çubuklar (# gibi), uçları yatay kesik
        x0 = cx + s*off
        # merkez çizgisi: x = x0 + (cy - y)*tan(sl)
        L = 86
        y1, y2 = cy - L, cy + L
        def xx(y): return x0 + (cy - y)*math.tan(sl)
        hw = t/2/math.cos(sl)
        d = (f"M{f(xx(y1)-hw)} {f(y1)}H{f(xx(y1)+hw)}L{f(xx(y2)+hw)} {f(y2)}H{f(xx(y2)-hw)}Z")
        bars.append(f'<path d="{d}"/>')
    return svg(ring + "".join(bars))

if __name__ == "__main__":
    for n, fn in (("a", concept_a), ("b", concept_b), ("c", concept_c)):
        open(f"concept-{n}-v1.svg", "w").write(fn())

def concept_c2(accent=None):
    """C v2: eğik çubukların her ucu ayrı ayrı halkanın ortasında (r≈91) biter; yatay uçlar da öyle."""
    cx = cy = 128; Ro, Ri = 102, 80; mid = 91
    ring = (f'<path fill-rule="evenodd" d="M{cx} {cy-Ro}A{Ro} {Ro} 0 1 1 {cx} {cy+Ro}A{Ro} {Ro} 0 1 1 {cx} {cy-Ro}Z'
            f'M{cx} {cy-Ri}A{Ri} {Ri} 0 1 0 {cx} {cy+Ri}A{Ri} {Ri} 0 1 0 {cx} {cy-Ri}Z"/>')
    t, off = 20, 27
    parts = []
    for s in (-1, 1):
        y = cy + s*off
        half = math.sqrt(mid**2 - off**2)
        parts.append(f'<rect x="{f(cx-half)}" y="{f(y-t/2)}" width="{f(2*half)}" height="{t}"/>')
    sl = math.radians(15); hw = t/2/math.cos(sl)
    for s in (-1, 1):
        x0 = cx + s*off
        xx = lambda y: x0 + (cy - y)*math.tan(sl)
        def end(sign):  # sign=-1 üst, +1 alt: çubuk merkez çizgisinin r=mid'i kestiği y
            lo, hi = 0.0, 120.0
            for _ in range(60):
                m = (lo+hi)/2; y = cy + sign*m
                r = math.hypot(xx(y)-cx, y-cy)
                lo, hi = (m, hi) if r < mid else (lo, m)
            return cy + sign*lo
        y1, y2 = end(-1), end(1)
        parts.append(f'<path d="M{f(xx(y1)-hw)} {f(y1)}H{f(xx(y1)+hw)}L{f(xx(y2)+hw)} {f(y2)}H{f(xx(y2)-hw)}Z"/>')
        for y in (y1, y2):
            for x in (xx(y)-hw, xx(y)+hw):
                r = math.hypot(x-cx, y-cy); assert Ri < r < Ro, (s, y, r)
    return svg(ring + "".join(parts))

def concept_a2(accent="#000"):
    """A v2: ufuk kavsi üstünde dikey üç çubuk (sıralama), ortadaki en uzun."""
    cx, cy, R = 128, 380, 176
    parts = [f'<circle cx="{cx}" cy="{cy}" r="{R}"/>']
    w, g = 34, 14
    for i, (h, col) in enumerate(((70, "#000"), (128, accent), (98, "#000"))):
        x = cx + (i-1)*(w+g)
        base = cy - math.sqrt(R*R - (x-cx)**2) + 14
        parts.append(f'<rect x="{f(x-w/2)}" y="{f(base-h-14-g)}" width="{w}" height="{f(h)}" rx="4" fill="{col}"/>')
    return svg("".join(parts))

if __name__ == "__main__":
    open("concept-c-v2.svg","w").write(concept_c2()); open("concept-a-v2.svg","w").write(concept_a2())
