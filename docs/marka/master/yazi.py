"""Barlow Condensed glifleri -> SVG path (canlı <text> yok). Kullanım: yazi.py FONT METIN IZ_BIRIM"""
import sys, json
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
font, text, track = sys.argv[1], sys.argv[2], float(sys.argv[3])
f = TTFont(font); gs = f.getGlyphSet(); cmap = f.getBestCmap(); upm = f["head"].unitsPerEm
kern = {}
x = 0; d = []; prev = None
for ch in text:
    gn = cmap[ord(ch)]
    if ch == " ":
        x += gs[gn].width + track; prev = None; continue
    pen = SVGPathPen(gs)
    tp = TransformPen(pen, (1, 0, 0, -1, x, 0))
    gs[gn].draw(tp); d.append(pen.getCommands())
    x += gs[gn].width + track; prev = gn
x -= track
cap = f["OS/2"].sCapHeight
print(json.dumps({"d": " ".join(d), "width": x, "cap": cap, "upm": upm}))
