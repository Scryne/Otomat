"""S13: hikâyede değişen karakter durumu (Fox Without A Tail, 10-15 Orbit) çizilebiliyor ve denetlenebiliyor mu?

1. Görme: Workers AI'daki bir görsel-anlama modeli karede "tilkinin kuyruğu var mı" sorusunu doğru cevaplıyor mu, kaç
   neuron? Kareler: 10-15 koşusunun artifact'ı (0-1: kuyruklu, doğru; 2-6: kuyruk koptuktan sonra, kuyruklu çizilmiş).
2. Çizim: görünen şeyi olumlu söyleyen istem ("tailless fox, round bare rump, pink bandage") flux-2-klein'da kuyruksuz
   tilki çiziyor mu; olumsuz istem ("his tail gone") ile karşılaştırma.

Sonuç (2026-10-13):
- Çizim: olumsuz 2/2 kuyruklu, olumlu 2/2 kuyruksuz (gözle de doğrulandı).
- llama-4-scout-17b: 11 karenin 10'u doğru, ~51 neuron/kare. Kaçırdığı: kuyruğun gövde arkasında yarı saklı olduğu
  kalabalık kare (sahne 4). mistral-small-3.1-24b: JSON şemasında 7/11 yanıt boşlukla bozuldu, elendi.
- Karar: senaryo değişen görünüşü olumlu tarifle bildirir, kod sonraki sahnelerin istemine ekler, kare llama-4-scout
  ile denetlenir (otomat/hikaye/uretim.py `durumlari_denetle`).

Çalıştırma: uv run python spikes/s13_karakter_durumu.py <artifact_sahne_klasoru> <cikti_klasoru>
"""

import base64
import json
import sys
import urllib.error
from pathlib import Path

from otomat.hikaye import cf

GORSEL_MODELLER = ["@cf/meta/llama-4-scout-17b-16e-instruct", "@cf/mistralai/mistral-small-3.1-24b-instruct"]
SORU = (
    "Look at the orange fox wearing a red scarf. Is a tail visible attached to this orange fox (a bushy tail behind "
    "or beside its body)? Answer as JSON."
)
SEMA = {
    "type": "object",
    "properties": {"tail_visible": {"type": "boolean"}, "confidence": {"type": "number"}, "why": {"type": "string"}},
    "required": ["tail_visible", "confidence", "why"],
}

STIL = (
    "Soft children's picture book illustration, gouache and colored pencil, rounded friendly shapes, warm pastel "
    "palette, cute animals with big kind eyes, cozy and gentle, full-bleed edge-to-edge artwork with no border or "
    "frame, no text, no letters. A single full-frame scene, not a comic, no panels. A sunny forest clearing in a "
    "gentle pastel world, with soft greens and warm golds."
)
CIZIMLER = {
    "olumsuz": "Felix the fox is a bright orange fox with big round eyes, wearing striped blue and yellow socks, a "
    "small red scarf. Felix the fluffy fox sitting on a fallen log, his tail gone, head bowed.",
    "olumlu": "Felix the fox is a bright orange tailless fox with big round eyes, wearing striped blue and yellow "
    "socks, a small red scarf; his rump is round and bare with only a tiny pink bandage where a tail would be. Felix "
    "the tailless fox sitting on a fallen log, seen from behind and the side so his bare bandaged rump shows, head "
    "bowed.",
}


def sor(model: str, resim: Path) -> tuple[dict | None, float, str]:
    b64 = base64.b64encode(resim.read_bytes()).decode()
    govde = json.dumps(
        {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": SORU},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    ],
                }
            ],
            "response_format": {"type": "json_schema", "json_schema": {"name": "c", "schema": SEMA}},
            "max_tokens": 300,
        }
    ).encode()
    try:
        y = cf._istek("v1/chat/completions", govde, "application/json")
    except urllib.error.HTTPError as e:
        return None, 0, f"HTTP {e.code} {e.read()[:300]!r}"
    n = y.get("usage", {}).get("neurons", 0)
    icerik = y["choices"][0]["message"].get("content") or ""
    try:
        return json.loads(icerik), n, ""
    except json.JSONDecodeError:
        return None, n, icerik[:200]


def main():
    kaynak, cikti = Path(sys.argv[1]), Path(sys.argv[2])
    cikti.mkdir(parents=True, exist_ok=True)
    for ad, istem in CIZIMLER.items():
        for t in (0, 1):
            cf.gorsel(f"{STIL} {istem}", cikti / f"{ad}_{t}.jpg", 1300 + 7 * t)
    print("flux neuron:", cf.NEURON["toplam"])
    kareler = sorted(kaynak.glob("sahne_*.jpg")) + sorted(cikti.glob("*.jpg"))
    for model in GORSEL_MODELLER:
        for k in kareler:
            c, n, hata = sor(model, k)
            print(model.split("/")[-1], k.name, c and (c["tail_visible"], c["confidence"]), round(n, 1), hata or "",
                  (c or {}).get("why", "")[:90])  # fmt: skip


if __name__ == "__main__":
    main()
