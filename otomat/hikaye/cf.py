"""Cloudflare Workers AI istemcisi: metin (gpt-oss-120b, JSON şeması) ve görsel (flux-2-klein-4b).

Bedava kota günde 10.000 neuron (aşınca istek hata verir, fatura yok). Panel sayacı 00:00 UTC'de sıfırlanıyor ama
engel kayan 24 saat sürdü (10-09 ölçümü, docs/arastirma/09). Video başına ~1.250-2.100 neuron harcanır. Harcanan
miktar `NEURON`'da birikir ve meta.json'a yazılır.
Sırlar: CF_ACCOUNT_ID / CF_API_TOKEN (Actions secret) ya da yerelde sirlar/cloudflare.json.
"""

import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from otomat.ayarlar import KOK

METIN_MODELI = "@cf/openai/gpt-oss-120b"
GORSEL_MODELI = "@cf/black-forest-labs/flux-2-klein-4b"
GORSEL_BOYUT = (768, 1344)  # 9:16'ya en yakın; 6 karo × 26,05 neuron
GORSEL_NEURON = 6 * 26.05
FILTRE_KODU = b"3030"  # "output has been flagged": güvenlik filtresi
DUZ = {"‑": "-", "‐": "-", "–": "-", "—": " - ", "’": "'", "‘": "'",
       "“": '"', "”": '"', " ": " ", " ": " "}  # fmt: skip

NEURON = {"toplam": 0.0}


class CFHatasi(RuntimeError):
    pass


class KotaHatasi(CFHatasi):
    """Günlük bedava kota bitti (4006): yeniden denemek boşuna, kota dolduktan ~24 saat sonra açılır."""


class FiltreHatasi(CFHatasi):
    """Sahne görseli her denemede güvenlik filtresine takıldı (3030): hikâye düşer, sıradaki denenir."""


KOTA_KODU = b"4006"


def _kota_mi(e: urllib.error.HTTPError) -> bytes:
    govde = e.read()
    if e.code == 429 and KOTA_KODU in govde:
        raise KotaHatasi(
            "Cloudflare Workers AI günlük bedava kotası (10.000 neuron) bitti; dolduktan ~24 saat sonra açılır "
            "(kayan pencere). Bu slotun videosu üretilmedi; sonraki koşu kaldığı yerden devam eder."
        ) from e
    return govde


def kimlik() -> tuple[str, str]:
    if os.environ.get("CF_API_TOKEN"):
        return os.environ["CF_ACCOUNT_ID"], os.environ["CF_API_TOKEN"]
    yol = KOK / "sirlar" / "cloudflare.json"
    if not yol.exists():
        raise CFHatasi("Cloudflare kimliği yok: CF_ACCOUNT_ID/CF_API_TOKEN ya da sirlar/cloudflare.json")
    d = json.loads(yol.read_text(encoding="utf-8"))
    return d["account_id"], d["api_token"]


def duzelt(x):
    """Model çıktısındaki tipografik işaretleri düz ASCII'ye çevirir (TTS ve Windows konsolu takılıyordu)."""
    if isinstance(x, str):
        for a, b in DUZ.items():
            x = x.replace(a, b)
        return x
    if isinstance(x, list):
        return [duzelt(v) for v in x]
    if isinstance(x, dict):
        return {k: duzelt(v) for k, v in x.items()}
    return x


def _istek(yol: str, govde: bytes, tur: str, zaman_asimi: float = 180) -> dict:
    hesap, belirtec = kimlik()
    istek = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/accounts/{hesap}/ai/{yol}",
        govde,
        {"Authorization": f"Bearer {belirtec}", "Content-Type": tur},
    )
    return json.load(urllib.request.urlopen(istek, timeout=zaman_asimi))


def sohbet(istem: str, sema: dict, deneme: int = 3) -> dict:
    govde = json.dumps(
        {
            "model": METIN_MODELI,
            "messages": [{"role": "user", "content": istem}],
            "response_format": {"type": "json_schema", "json_schema": {"name": "cikti", "schema": sema}},
            "max_tokens": 8000,  # gpt-oss önce akıl yürütür; düşük sınırda içerik boş dönüyordu
            "reasoning_effort": "medium",
        }
    ).encode()
    son = None
    for i in range(deneme):
        try:
            y = _istek("v1/chat/completions", govde, "application/json")
            NEURON["toplam"] += y.get("usage", {}).get("neurons", 0)
            icerik = y["choices"][0]["message"].get("content")
            if not icerik:
                raise CFHatasi(f"boş yanıt: {y['choices'][0].get('finish_reason')}")
            return duzelt(json.loads(icerik))
        except urllib.error.HTTPError as e:
            son = f"HTTP {e.code}: {_kota_mi(e)[:200]!r}"
            time.sleep(4 * (i + 1))
        except (urllib.error.URLError, CFHatasi, json.JSONDecodeError, TimeoutError, KeyError, IndexError) as e:
            son = f"{type(e).__name__}: {e}"  # KeyError/IndexError: beklenmeyen yanıt biçimi (choices yok)
            time.sleep(4 * (i + 1))
    raise CFHatasi(f"metin modeli {deneme} denemede yanıt vermedi: {son}")


def gorsel(istem: str, yol: Path, tohum: int, deneme: int = 4) -> Path:
    """Sahne görselini `yol`a yazar (varsa yeniden üretmez). Güvenlik filtresine takılırsa tohum değişir ve istem
    yumuşatılır; ölüm sahneleri S11'de filtreye takılıyordu."""
    if yol.exists():
        return yol
    sinir = "----otomat"
    for i in range(deneme):
        alanlar = {"prompt": istem[:2000], "width": GORSEL_BOYUT[0], "height": GORSEL_BOYUT[1], "seed": tohum + i}
        parcalar = [
            f'--{sinir}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n' for k, v in alanlar.items()
        ]
        govde = ("".join(parcalar) + f"--{sinir}--\r\n").encode()
        try:
            y = _istek(f"run/{GORSEL_MODELI}", govde, f"multipart/form-data; boundary={sinir}")
            NEURON["toplam"] += GORSEL_NEURON
            resim = (y.get("result") or {}).get("image")
            if not resim:
                raise ValueError(f"yanıtta görsel yok: {str(y)[:200]}")
            # önce geçici dosya: yarım yazılmış görsel sonraki koşuda "var" sayılıp yeniden kullanılmasın
            gecici = yol.with_suffix(".tmp")
            gecici.write_bytes(base64.b64decode(resim))
            gecici.replace(yol)
            return yol
        except urllib.error.HTTPError as e:
            hata = _kota_mi(e)
            if i == deneme - 1:
                tur = FiltreHatasi if FILTRE_KODU in hata else CFHatasi
                raise tur(f"görsel üretilemedi ({e.code}): {hata[:200]!r}") from e
            if FILTRE_KODU in hata:
                istem += ". Calm, gentle, non-graphic, nobody hurt."
            time.sleep(3)
        except (urllib.error.URLError, TimeoutError, ValueError) as e:  # ValueError: bozuk base64 ya da görselsiz yanıt
            if i == deneme - 1:
                raise CFHatasi(f"görsel üretilemedi: {e}") from e
            time.sleep(5)
    raise CFHatasi("görsel üretilemedi")
