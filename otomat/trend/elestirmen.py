"""Görsel eleştirmen: render öncesi inceleme sayfalarını (HyperFrames `snapshot --review`) ayrı bir modele gösterir.

Neden ayrı model: üretici kendi işini iyi görür (motion-video-kit "gauntlet", claude-motion-design: eleştirmen yalnız
kareleri ve brifi görür). gemini-4-argon (OpenCode Go) görüntü okuyor; spike sayfasında benim gördüğüm kusurların
aynısını buldu (2026-11-20). Bulgu türleri kapalı küme: kod bunlardan bazılarını kuralla düzeltir, kalanı rapora girer.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from otomat.trend.llm import Oturum, json_cikar

MODEL = "gemini-4-argon"
TURLER = ("okunmuyor", "kontrast", "bos_kadraj", "kirpik", "yazi_tasma", "anlamsiz_gorsel", "tekrar", "diger")

SISTEM = """You are a harsh motion-graphics director reviewing frames of a narrated YouTube explainer before render.
You see a contact sheet: numbered frames with timestamps. Judge only what is visible. For each real problem give:
{"t": seconds from the label, "tur": one of [okunmuyor (text unreadable/too small), kontrast (text fights the
background), bos_kadraj (frame mostly empty, small elements floating), kirpik (important element cut off at the edge),
yazi_tasma (text overflows or overlaps other text), anlamsiz_gorsel (photo has nothing to do with the on-screen words or
shows a wrong/irrelevant subject), tekrar (looks identical to another frame), diger], "siddet": "P0" (breaks the read)
or "P1" (weakens the film), "not": one short sentence}.
Do not report style preferences. Do not report problems that are not visible. Return ONLY JSON: {"bulgular": [...]}."""


def incele(sayfalar: list[Path], baglam: str = "", oturum: Oturum | None = None) -> list[dict]:
    oturum = oturum or Oturum("elestirmen")
    bulgular: list[dict] = []
    for s in sayfalar:
        if s.stat().st_size > 4_500_000:
            continue
        b64 = base64.b64encode(s.read_bytes()).decode()
        tip = "image/png" if s.suffix.lower() == ".png" else "image/jpeg"
        govde = {"model": MODEL, "max_tokens": 3000, "temperature": 0, "system": SISTEM, "messages": [{
            "role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": tip, "data": b64}},
                {"type": "text", "text": f"Sheet: {s.name}. Video context: {baglam[:600]}"}]}]}  # fmt: skip
        try:
            y = oturum._istek(govde)
            metin = "".join(c.get("text", "") for c in y.get("content", []) if c.get("type") == "text")
            for b in (json_cikar(metin) or {}).get("bulgular", []):
                if b.get("tur") in TURLER:
                    bulgular.append({**b, "sayfa": s.name})
        except Exception as e:  # noqa: BLE001 — eleştirmen düşerse render durmaz; rapora girer
            bulgular.append({"tur": "diger", "siddet": "P1", "not": f"eleştirmen çalışmadı: {str(e)[:120]}",
                             "sayfa": s.name})  # fmt: skip
    return bulgular


def sahneye_bagla(bulgular: list[dict], plan: dict) -> list[dict]:
    for b in bulgular:
        try:
            t = float(b.get("t"))
        except (TypeError, ValueError):
            continue
        for sh in plan["sahneler"]:
            if sh["bas"] <= t < sh["bas"] + sh["sure"]:
                b["sahne"] = sh["id"]
                b["sahne_tur"] = sh["tur"]
                break
    return bulgular


def duzelt(plan: dict, bulgular: list[dict]) -> list[str]:
    """Kural tabanlı onarım: fotoğraf üstü başlıkta kontrast/okunmama → koyu kat; anlamsız görsel → ifade
    (fotoğraf flu zeminde kalır).
    Dönüş: uygulanan değişikliklerin listesi."""
    yapilan = []
    sahne = {sh["id"]: sh for sh in plan["sahneler"]}
    for b in bulgular:
        sh = sahne.get(b.get("sahne", ""))
        if not sh or b.get("siddet") != "P0":
            continue
        if b["tur"] in ("kontrast", "okunmuyor") and sh["tur"] in ("foto", "ifade", "manset") and not sh.get("koyu"):
            sh["koyu"] = True
            yapilan.append(f"{sh['id']}: koyu kat ({b['tur']})")
        elif b["tur"] == "anlamsiz_gorsel" and sh["tur"] == "foto" and sh.get("baslik"):
            # fotoğraf zemin olarak kalır: ifade onu karartıp flulaştırır (v2'de düz renk zemin yok, K-44)
            sh.update(tur="ifade", metin=sh["baslik"])
            yapilan.append(f"{sh['id']}: foto → ifade (anlamsız görsel)")
    return yapilan


def rapor(bulgular: list[dict]) -> str:
    return json.dumps(bulgular, ensure_ascii=False, indent=1)
