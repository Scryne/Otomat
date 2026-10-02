"""Spike: LLM sayı yazmaz, {yer_tutucu} yazar; kod doldurur. Kapı: bilinmeyen tutucu/çıplak sayı/yazıyla sayı."""
import json, re, sys, time, urllib.request
from collections import Counter
from pathlib import Path

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gemma3:4b"
q = json.loads((Path(__file__).parent / "out" / "usgs.json").read_text(encoding="utf-8"))["features"]
mags = [f["properties"]["mag"] for f in q]
places = Counter(f["properties"]["place"].split(", ")[-1] for f in q if f["properties"]["place"])
big = max(q, key=lambda f: f["properties"]["mag"])["properties"]
olgular = {
    "total_quakes": {"value": len(q), "meaning": "number of earthquakes of magnitude 4.5 or more worldwide"},
    "days": {"value": 30, "meaning": "length of the period"},
    "strongest_magnitude": {"value": big["mag"], "meaning": "magnitude of the strongest earthquake"},
    "strongest_country": {"value": big["place"].split(", ")[-1], "meaning": "country/region of the strongest earthquake"},
    "top_region": {"value": places.most_common(1)[0][0], "meaning": "country/region with the most earthquakes"},
    "top_region_count": {"value": places.most_common(1)[0][1], "meaning": "how many earthquakes happened in top_region"},
    "quakes_above_6": {"value": sum(m >= 6 for m in mags), "meaning": "earthquakes of magnitude 6 or more"},
}
desc = "\n".join(f"- {{{k}}}: {v['meaning']}" for k, v in olgular.items())
prompt = f"""Write narration for a 25-second vertical data video about worldwide earthquakes in the last month.
You must NOT write any number or number word. Insert facts only with these placeholders, exactly as written:
{desc}
Rules: 4-5 short sentences; sentence 1 is a curiosity hook; each placeholder must be used according to its meaning;
no greetings, no "subscribe". Output only the narration."""
SAYI_KELIME = r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|forty|fifty|hundred|thousand|dozen)s?\b"
t = time.time()
body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False, "think": False, "options": {"temperature": 0.7}}).encode()
ham = json.loads(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:11434/api/generate", body), timeout=600).read())["response"].strip()
ham = re.sub(r"<think>.*?</think>", "", ham, flags=re.S).strip()
hatalar = [f"bilinmeyen tutucu {{{k}}}" for k in re.findall(r"\{(\w+)\}", ham) if k not in olgular]
izinli = set(re.findall(r"\d+(?:\.\d+)?", desc))
ciplak = [x for x in re.findall(r"\d+(?:\.\d+)?", re.sub(r"\{\w+\}", "", ham)) if x not in izinli]
if ciplak: hatalar.append("çıplak rakam " + str(ciplak))
if re.search(SAYI_KELIME, ham, re.I): hatalar.append("yazıyla sayı: " + ", ".join(set(m.group(0) for m in re.finditer(SAYI_KELIME, ham, re.I))))
dolu = re.sub(r"\{(\w+)\}", lambda m: str(olgular[m.group(1)]["value"]) if m.group(1) in olgular else m.group(0), ham)
print(f"[{MODEL}] {time.time()-t:.1f} sn\nHAM: {ham}\nDOLU: {dolu}\nKAPI: {'GEÇTİ' if not hatalar else 'KALDI ' + '; '.join(hatalar)}")
