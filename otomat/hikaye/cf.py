"""Cloudflare Workers AI istemcisi: metin (gpt-oss-120b, JSON şeması), görsel (flux-2-klein-4b, isteğe bağlı referans
görsellerle) ve kare denetimi (llama-4-scout, evet/hayır).

Bedava kota günde 10.000 neuron (aşınca istek hata verir, fatura yok). Panel sayacı 00:00 UTC'de sıfırlanıyor ama
engel kayan 24 saat sürdü (10-09 ölçümü, docs/arastirma/09). Video başına ~1.250-2.100 neuron harcanır. Harcanan
miktar `NEURON`'da birikir ve meta.json'a yazılır (görseller 4 thread'den çizilir: sayaç kilitli).
Sırlar: CF_ACCOUNT_ID / CF_API_TOKEN (Actions secret) ya da yerelde sirlar/cloudflare.json.
"""

import base64
import http.client
import io
import json
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from otomat.ayarlar import KOK

METIN_MODELI = "@cf/openai/gpt-oss-120b"
GORSEL_MODELI = "@cf/black-forest-labs/flux-2-klein-4b"
# S13 (10-13): kuyruklu/kuyruksuz tilki 11 karenin 10'unda doğru, ~51 neuron; mistral-small JSON'u bozdu
GORME_MODELI = "@cf/meta/llama-4-scout-17b-16e-instruct"
GORSEL_BOYUT = (768, 1344)  # 9:16'ya en yakın; 6 karo × 26,05 neuron
GORSEL_NEURON = 6 * 26.05
REFERANS_NEURON = 5.37  # 512² altı girdi görseli başına (Workers AI fiyat sayfası, 10-13)
REFERANS_KENAR = 504  # klein girdi görselleri 512x512'den küçük olmalı
REFERANS_EN_COK = 4  # input_image_0..3
FILTRE_KODU = b"3030"  # "output has been flagged": güvenlik filtresi
KOTA_KODU = b"4006"
KALICI = (400, 401, 403, 404)  # yeniden denemek boşuna (yetki, model adı, şema); 3030 ayrıca ele alınır
DUZ = {"‑": "-", "‐": "-", "–": "-", "—": " - ", "’": "'", "‘": "'",
       "“": '"', "”": '"', " ": " ", " ": " "}  # fmt: skip

NEURON = {"toplam": 0.0}
_KILIT = threading.Lock()
# ağ katmanı hataları: URLError OSError'dır; okurken kopan bağlantı (IncompleteRead) HTTPException
AG_HATALARI = (OSError, http.client.HTTPException, TimeoutError)


class CFHatasi(RuntimeError):
    pass


class KotaHatasi(CFHatasi):
    """Günlük bedava kota bitti (4006): yeniden denemek boşuna, kota dolduktan ~24 saat sonra açılır."""


class FiltreHatasi(CFHatasi):
    """Sahne görseli her denemede güvenlik filtresine takıldı (3030): hikâye düşer, sıradaki denenir."""


def harca(neuron: float) -> None:
    with _KILIT:
        NEURON["toplam"] += neuron


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
    with urllib.request.urlopen(istek, timeout=zaman_asimi) as yanit:
        return json.load(yanit)


def _bekle(i: int, deneme: int, sure: float) -> None:
    if i < deneme - 1:  # son denemeden sonra uyumak yalnız koşuyu uzatıyordu
        time.sleep(sure)


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
            harca(y.get("usage", {}).get("neurons", 0))
            icerik = y["choices"][0]["message"].get("content")
            if not icerik:
                raise CFHatasi(f"boş yanıt: {y['choices'][0].get('finish_reason')}")
            return duzelt(json.loads(icerik))
        except urllib.error.HTTPError as e:
            son = f"HTTP {e.code}: {_kota_mi(e)[:200]!r}"
            if e.code in KALICI:
                break
        except (*AG_HATALARI, CFHatasi, ValueError, KeyError, IndexError, TypeError) as e:
            son = f"{type(e).__name__}: {e}"  # KeyError/IndexError: beklenmeyen yanıt biçimi (choices yok)
        _bekle(i, deneme, 4 * (i + 1))
    raise CFHatasi(f"metin modeli {deneme} denemede yanıt vermedi: {son}")


def _referans_baytlari(yol: Path) -> bytes:
    """Referans görsel klein sınırının (512²) altına küçültülür, JPEG."""
    from PIL import Image

    with Image.open(yol) as img:
        img = img.convert("RGB")
        img.thumbnail((REFERANS_KENAR, REFERANS_KENAR))
        tampon = io.BytesIO()
        img.save(tampon, "JPEG", quality=90)
    return tampon.getvalue()


def _cok_parcali(alanlar: dict, dosyalar: dict[str, bytes], sinir: str) -> bytes:
    parcalar = [
        f'--{sinir}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in alanlar.items()
    ]
    for ad, veri in dosyalar.items():
        bas = (
            f'--{sinir}\r\nContent-Disposition: form-data; name="{ad}"; filename="{ad}.jpg"\r\n'
            "Content-Type: image/jpeg\r\n\r\n"
        )
        parcalar.append(bas.encode() + veri + b"\r\n")
    return b"".join(parcalar) + f"--{sinir}--\r\n".encode()


def gorsel(istem: str, yol: Path, tohum: int, deneme: int = 4, referanslar: tuple[Path, ...] = ()) -> Path:
    """Sahne görselini `yol`a yazar (varsa yeniden üretmez). Güvenlik filtresine takılırsa tohum değişir ve istem
    yumuşatılır; ölüm sahneleri S11'de filtreye takılıyordu. `referanslar`: karakterin önceden çizilmiş karesi gibi
    girdi görselleri (en çok 4; istem onlara "the reference image" diye atıf yapar)."""
    if yol.exists():
        return yol
    sinir = "----otomat"
    dosyalar = {f"input_image_{i}": _referans_baytlari(r) for i, r in enumerate(referanslar[:REFERANS_EN_COK])}
    maliyet = GORSEL_NEURON + REFERANS_NEURON * len(dosyalar)
    son = None
    for i in range(deneme):
        alanlar = {"prompt": istem[:2000], "width": GORSEL_BOYUT[0], "height": GORSEL_BOYUT[1], "seed": tohum + i}
        try:
            y = _istek(f"run/{GORSEL_MODELI}", _cok_parcali(alanlar, dosyalar, sinir),
                       f"multipart/form-data; boundary={sinir}")  # fmt: skip
            harca(maliyet)
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
            son = f"({e.code}): {hata[:200]!r}"
            if FILTRE_KODU in hata:
                if i == deneme - 1:
                    raise FiltreHatasi(f"görsel üretilemedi {son}") from e
                istem += ". Calm, gentle, non-graphic, nobody hurt."
            elif e.code in KALICI:
                break
            _bekle(i, deneme, 3)
        except (*AG_HATALARI, ValueError) as e:  # ValueError: bozuk base64 ya da görselsiz yanıt
            son = f"{type(e).__name__}: {e}"
            _bekle(i, deneme, 5)
    raise CFHatasi(f"görsel üretilemedi {son}")


GORME_SEMA = {
    "type": "object",
    "properties": {"answer": {"type": "boolean"}, "confidence": {"type": "number"}},
    "required": ["answer", "confidence"],
}


def gorsel_sor(yol: Path, soru: str, deneme: int = 2) -> tuple[bool, float]:
    """Karedeki görünüm hakkında evet/hayır sorusu: (cevap, güven 0-1; model yüzde dönerse ölçeklenir)."""
    resim = base64.b64encode(yol.read_bytes()).decode()
    govde = json.dumps(
        {
            "model": GORME_MODELI,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{soru} Answer about this picture only, as JSON."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{resim}"}},
                    ],
                }
            ],
            "response_format": {"type": "json_schema", "json_schema": {"name": "cevap", "schema": GORME_SEMA}},
            "max_tokens": 100,
        }
    ).encode()
    son = None
    for i in range(deneme):
        try:
            y = _istek("v1/chat/completions", govde, "application/json", 60)
            harca(y.get("usage", {}).get("neurons", 0))
            c = json.loads(y["choices"][0]["message"].get("content") or "")
            guven = float(c["confidence"])
            return bool(c["answer"]), min(1.0, max(0.0, guven / 100 if guven > 1 else guven))
        except urllib.error.HTTPError as e:
            son = f"HTTP {e.code}: {_kota_mi(e)[:200]!r}"
            if e.code in KALICI:
                break
        except (*AG_HATALARI, KeyError, IndexError, TypeError, ValueError) as e:
            son = f"{type(e).__name__}: {e}"
        _bekle(i, deneme, 3 * (i + 1))
    raise CFHatasi(f"görme modeli {deneme} denemede yanıt vermedi: {son}")
