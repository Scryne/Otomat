"""Yerel LLM (Ollama) istemcisi: yapılandırılmış JSON çıktı, düşünme metni koruması."""

import json
import os
import re
import urllib.request

from otomat.ayarlar import modeller

ADRES = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
DUSUNME = re.compile(r"^\s*(<think>|hmm\b|okay, the user|alright, the user|let me think)", re.I)


class LLMHatasi(RuntimeError):
    pass


def model_adi() -> str:
    return os.environ.get("OTOMAT_LLM", modeller()["llm"]["model"])


def json_uret(
    istem: str, sema: dict, sicaklik: float = 0.8, tohum: int | None = None, zaman_asimi: float = 300
) -> dict:
    secenek = {"temperature": sicaklik}
    if tohum is not None:
        secenek["seed"] = tohum
    govde = {
        "model": model_adi(),
        "prompt": istem,
        "stream": False,
        "think": False,
        "format": sema,
        "options": secenek,
    }
    istek = urllib.request.Request(f"{ADRES}/api/generate", json.dumps(govde).encode())
    with urllib.request.urlopen(istek, timeout=zaman_asimi) as yanit:
        ham = json.loads(yanit.read())["response"]
    if DUSUNME.match(ham):  # Faz 1 dersi: bazı etiketler think:false'u yok sayıyor
        raise LLMHatasi(f"model düşünme metni üretti: {ham[:80]!r}")
    try:
        return json.loads(ham)
    except json.JSONDecodeError as e:
        raise LLMHatasi(f"JSON değil: {ham[:120]!r}") from e
