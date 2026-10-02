"""Spike: veriden olgular -> yerel LLM anlatımı -> sayı doğrulama kapısı."""
import json, re, sys, time, urllib.request
from collections import Counter
from pathlib import Path

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gemma3:4b"
q = json.loads((Path(__file__).parent / "out" / "usgs.json").read_text(encoding="utf-8"))["features"]
mags = [f["properties"]["mag"] for f in q]
places = Counter(f["properties"]["place"].split(", ")[-1] for f in q if f["properties"]["place"])
big = max(q, key=lambda f: f["properties"]["mag"])["properties"]
olgular = {
    "total_quakes": len(q),
    "days": 30,
    "min_magnitude": 4.5,
    "strongest_magnitude": big["mag"],
    "strongest_place": big["place"],
    "top_region": places.most_common(1)[0][0],
    "top_region_count": places.most_common(1)[0][1],
    "quakes_above_6": sum(m >= 6 for m in mags),
}
prompt = f"""Write narration for a 25-second vertical data video. Facts (use ONLY these numbers, write numbers as digits):
{json.dumps(olgular)}
Rules: 4-5 short sentences, first sentence is a hook that creates curiosity, no greetings, no "subscribe", no numbers that are not in the facts. Output only the narration."""
t = time.time()
body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False, "think": False, "options": {"temperature": 0.7}}).encode()
r = json.loads(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:11434/api/generate", body), timeout=300).read())
metin = r["response"].strip()
izinli = {float(v) for v in olgular.values() if isinstance(v, (int, float))}
bulunan = [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*\.?\d*", metin)]
yabanci = [x for x in bulunan if x not in izinli]
print(f"[{MODEL}] {time.time()-t:.1f} sn\nOLGULAR: {olgular}\nMETİN: {metin}\nKAPI: {'GEÇTİ' if not yabanci else 'KALDI ' + str(yabanci)}")
