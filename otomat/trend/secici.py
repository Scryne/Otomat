"""Günün konusu: radar adayları → zenginleştirme → TypeSafe (Jev) sert eleme → LLM editör (hikâye + açı).

Ayrım (global kural "AI kararları: TypeSafe"): "bu konu bir ölüm/felaket haberi mi, siyaset mi, açıklanabilir mi,
küresel mi" anlam kararıdır ve tipli olasılık ister → Jev. Hangi hikâyenin bugün en iyi video olduğu ve hangi açıdan
anlatılacağı ise üretken editörlüktür → LLM. Jev sürümü sabit (tekrar üretilebilirlik); `ts.py kontrol` izler.

Neden bu eleme: radar ham sıralamasında ölüm haberiyle sıçrayan kişiler ve bot kaynaklı sıçramalar üstte çıkıyor
(2026-11-20 canlı koşu: Larry Poindexter ×2463). Yeni yüzsüz kanal son dakika haber raflarına giremiyor (YouTube
support 9057101: otorite sinyalleri), trajedi ve siyaset hem dağıtım hem politika riski.
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import os
import socket
import time
import urllib.error
import urllib.request
from dataclasses import asdict
from pathlib import Path

from otomat.trend import kaynak, radar
from otomat.trend.llm import Oturum

TS_MODEL = "jev-1.14.0"
TS_URL = "https://api.typesafe.ai/v1/systemone"
KATEGORILER = ["video_game", "film_tv", "music", "technology_ai", "science_space", "sports", "celebrity",
               "internet_viral", "business_money", "history_culture", "other"]  # fmt: skip
SORULAR = {
    "trajedi": {"type": "noul", "instructions": (
        "Using `topic.description`, `topic.summary` and `topic.headlines`: is the main reason this topic is in the news "
        "right now a death, a killing, an accident, a disaster, a terror attack, a crime, an illness, or another "
        "tragedy?")},
    "siyaset": {"type": "noul", "instructions": (
        "Is `topic` mainly about electoral politics, a government, a politician, a war, or a political conflict between "
        "states?")},
    "yetiskin": {"type": "noul", "instructions": (
        "Is `topic` mainly about sexual or adult content, pornography, or explicit material?")},
    "kuresel": {"type": "noul", "instructions": (
        "Would curious people in many English-speaking countries care about `topic`, rather than only fans of one local "
        "team or followers of one country's domestic news?")},
    "aciklama": {"type": "score", "instructions": (
        "How well would `topic` work as a 6-10 minute YouTube explainer for a general global audience who has heard the "
        "name and wonders what it is and why everyone is talking about it?"),
        "criteria": [
            {"label": "none", "description": "Nothing to explain: a routine result, a minor update, or a name with no story."},
            {"label": "thin", "description": "Some interest but too little backstory or stakes for more than a minute."},
            {"label": "good", "description": "A clear story with backstory, stakes and open questions; a curious viewer "
                                             "would click and learn something."},
            {"label": "great", "description": "A big cultural moment with rich history, surprising facts and a debate; "
                                              "people will search for an explanation for days."}]},
    "kategori": {"type": "choice", "instructions": "Which category best fits `topic`?",
                 "criteria": {k: k.replace("_", " ") for k in KATEGORILER}},
}  # fmt: skip


def _ipv4():
    asil = socket.getaddrinfo
    if getattr(asil, "_ipv4", False):
        return

    def f(host, port, family=0, *a, **k):
        return asil(host, port, family or socket.AF_INET, *a, **k)

    f._ipv4 = True  # type: ignore[attr-defined]
    socket.getaddrinfo = f  # bu makinede IPv6 çözümlemesi ~12 sn bekliyor (ts.py notu)


def ts_sor(durum: dict, sorular: dict = SORULAR) -> dict:
    _ipv4()
    anahtar = os.environ.get("TYPESAFE_API_KEY")
    if not anahtar:
        raise RuntimeError("TYPESAFE_API_KEY yok")
    govde = {"model": TS_MODEL, "state": durum, "questions": sorular}
    istek = urllib.request.Request(TS_URL, json.dumps(govde).encode(), headers={
        "Authorization": f"Bearer {anahtar}", "Content-Type": "application/json"})  # fmt: skip
    for d in range(4):
        try:
            with urllib.request.urlopen(istek, timeout=60) as y:
                return json.load(y)["answers"]
        except (urllib.error.URLError, TimeoutError):
            if d == 3:
                raise
            time.sleep(3 * (d + 1))
    raise RuntimeError("TypeSafe yanıt vermedi")


def zenginlestir(k: radar.Konu) -> dict:
    d = {"ad": k.ad, "skor": k.skor, "wiki": k.wiki_makale, "goruntuleme": k.wiki_goruntuleme, "artis": k.wiki_artis,
         "gt_trafik": k.gt_trafik, "geolar": k.gt_geolar, "aciklama": "", "ozet": "",
         "haberler": [h["baslik"] for h in k.haberler][:6]}  # fmt: skip
    if k.wiki_makale:
        try:
            ham = radar._getir(f"https://en.wikipedia.org/api/rest_v1/page/summary/{k.wiki_makale}")
            d["aciklama"], d["ozet"] = kaynak.wiki_ozet_ayristir(ham)
        except Exception:  # noqa: BLE001 — özet yoksa aday yine değerlendirilir
            pass
    try:
        hs = kaynak.haberler(k.ad, gun=3, en_cok=8)
        d["haberler"] = list(dict.fromkeys(d["haberler"] + [f"{h.baslik} ({h.yayinci})" for h in hs]))[:8]
    except Exception:  # noqa: BLE001
        pass
    return d


def adaylar(n: int = 36, konular: list[radar.Konu] | None = None) -> list[dict]:
    konular = konular if konular is not None else radar.topla()
    with cf.ThreadPoolExecutor(6) as ex:
        zengin = list(ex.map(zenginlestir, konular[:n]))
    for d in zengin:
        durum = {"topic": {"name": d["ad"], "description": d["aciklama"], "summary": d["ozet"][:1500],
                           "headlines": d["haberler"]}}  # fmt: skip
        try:
            c = ts_sor(durum)
            d["ts"] = {"trajedi": round(c["trajedi"]["noul"], 2), "siyaset": round(c["siyaset"]["noul"], 2),
                       "yetiskin": round(c["yetiskin"]["noul"], 2), "kuresel": round(c["kuresel"]["noul"], 2),
                       "aciklama": round(c["aciklama"]["score"], 2), "kategori": c["kategori"]["choice"]}  # fmt: skip
        except Exception as e:  # noqa: BLE001
            d["ts"] = {"hata": str(e)[:200]}
    return zengin


def uygun(d: dict) -> bool:
    t = d.get("ts") or {}
    if "hata" in t or not t:
        return False
    return (t["trajedi"] < 0.5 and t["siyaset"] < 0.5 and t["yetiskin"] < 0.3 and t["kuresel"] >= 0.4
            and t["aciklama"] >= 1.4 and (d["haberler"] or d["ozet"]))  # fmt: skip


SISTEM_EDITOR = """You are the editor-in-chief of a YouTube channel that explains what the whole world is talking about
right now (global, English, general curious audience, faceless motion-graphics explainers, 6-10 minutes, plus Shorts).
You get today's trending candidates (from Google Trends, Wikipedia pageview spikes and news), already filtered for
tragedy/politics. Several candidates are often the same story (a game, its characters, its studio, its voice actor).

Pick the ONE story that will make the best video today. Criteria, in order:
1. Many people will search "what is X / why is everyone talking about X" over the next 3-7 days (staying power).
2. There is real substance to explain: backstory, numbers, a surprising angle, a debate — enough for 8 minutes.
3. A Wikipedia article exists with real content (it's our main source).
4. Not in the RECENTLY COVERED list.
5. We can illustrate it with freely licensed photos (people at events, places, products in public, ads, crowds) —
   prefer stories about real-world things over stories that only exist as copyrighted footage.

Then propose the angle: one sentence thesis that makes the video more than a news summary.
Return ONLY JSON: {"secim": {"hikaye": short story name, "wiki_baslik": exact main Wikipedia article title from the
candidates, "ilgili": [other candidate Wikipedia titles in the same story], "neden": why it is trending now (1-2
sentences, from the headlines), "aci": the thesis, "gorsel_aramalari": [4-8 short Wikimedia Commons search queries for
real photos related to the story (people, places, events, objects)]}, "yedekler": [up to 3 more stories, same fields; the pipeline falls back to them when a story
has too few free photos]}"""


def sec(oturum: Oturum, zengin: list[dict], gecmis: list[str], model: str = "kimi-k3") -> dict:
    aday = [d for d in zengin if uygun(d)]
    aday.sort(key=lambda d: -(d["ts"]["aciklama"] * 2 + d["skor"] / 10))
    sade = [{k: d[k] for k in ("ad", "wiki", "goruntuleme", "artis", "aciklama", "haberler")} |
            {"ozet": d["ozet"][:500], "kategori": d["ts"]["kategori"], "aciklanabilirlik": d["ts"]["aciklama"]}
            for d in aday[:18]]  # fmt: skip
    mesaj = (f"RECENTLY COVERED: {json.dumps(gecmis, ensure_ascii=False)}\n\nCANDIDATES:\n"
             f"{json.dumps(sade, ensure_ascii=False, indent=1)}")  # fmt: skip
    return oturum.json_sor(
        SISTEM_EDITOR, mesaj, model=model, en_cok=9000, sicaklik=0.4
    )  # 3 yedekle 4000 yetmedi (11-27)


def kaydet(yol: Path, zengin: list[dict], secim: dict) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps({"adaylar": zengin, "secim": secim}, ensure_ascii=False, indent=1, default=str),
                   encoding="utf-8")  # fmt: skip


__all__ = ["adaylar", "uygun", "sec", "kaydet", "ts_sor", "asdict"]
