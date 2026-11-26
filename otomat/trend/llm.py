"""Metin modeli istemcisi: OpenCode Go (Anthropic biçimli uç), Scryne'ın aboneliği.

Neden: trend hattı her gün araştırma özeti, senaryo, olgu denetimi ve başlık yazar. Cloudflare'in bedava 10.000 neuron'u
spor kanalına bile yetmiyor (Faz 19), Claude limiti ise geliştirme için korunuyor. Go'nun uç noktası belgeli
("applications calling Go directly", opencode.ai/v2/docs/console/go); istenen iki şey: kendi User-Agent'ı ve konuşma
başına sabit `x-opencode-session`. Limit: 5 saatte aylık hakkın %20'si, haftada %50'si.

Anahtar Kokpit'in DPAPI ile şifreli ayar dosyasından (~/.kokpit/usta.json) çözülür; `OTOMAT_GO_ANAHTAR` ortam
değişkeni varsa o kullanılır. Anahtar log'a, dosyaya, hata mesajına yazılmaz.
"""

from __future__ import annotations

import base64
import ctypes
import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

UC = "https://opencode.ai/inference/go/anthropic/v1/messages"
UA = "otomat-trend/1.0"
AYAR = Path.home() / ".kokpit" / "usta.json"
ENTROPI = b"kokpit-usta"
VARSAYILAN = "kimi-k3"  # senaryo ve editörlük; yedekleri sırayla denenir
YEDEKLER = ("glm-5.3", "qwen4-max")


class LLMHatasi(RuntimeError):
    pass


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi_coz(b64: str) -> str:
    veri = base64.b64decode(b64)
    vbuf = ctypes.create_string_buffer(veri, len(veri))
    ebuf = ctypes.create_string_buffer(ENTROPI, len(ENTROPI))
    giris = _Blob(len(veri), ctypes.cast(vbuf, ctypes.POINTER(ctypes.c_char)))
    ent = _Blob(len(ENTROPI), ctypes.cast(ebuf, ctypes.POINTER(ctypes.c_char)))
    cikis = _Blob()
    crypt32 = ctypes.windll.crypt32  # type: ignore[attr-defined]
    if not crypt32.CryptUnprotectData(ctypes.byref(giris), None, ctypes.byref(ent), None, None, 1, ctypes.byref(cikis)):
        raise LLMHatasi("Go anahtarı çözülemedi (Kokpit > Ayarlar > Usta)")
    try:
        return ctypes.string_at(cikis.pbData, cikis.cbData).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(cikis.pbData)  # type: ignore[attr-defined]


_ANAHTAR: str | None = None


def anahtar() -> str:
    global _ANAHTAR
    if _ANAHTAR:
        return _ANAHTAR
    if a := os.environ.get("OTOMAT_GO_ANAHTAR"):
        _ANAHTAR = a
        return a
    try:
        k = json.loads(AYAR.read_text(encoding="utf-8"))["anahtar"]["dpapi"]
    except (OSError, KeyError, ValueError) as e:
        raise LLMHatasi(f"Go anahtarı yok: {AYAR}") from e
    _ANAHTAR = _dpapi_coz(k)
    return _ANAHTAR


class Oturum:
    """Bir iş (ör. bir video) boyunca sabit oturum kimliği: Go yönlendirme ve önbellek için ister."""

    def __init__(self, ad: str = ""):
        self.kimlik = f"otomat-{ad or 'trend'}-{uuid.uuid4().hex[:12]}"
        self.kullanim: list[dict] = []

    def sor(self, sistem: str, mesaj: str, model: str = VARSAYILAN, en_cok: int = 8000, sicaklik: float = 0.7,
            deneme: int = 3, dusun: bool = True) -> str:  # fmt: skip
        """dusun=False: modelin akıl yürütme token'ları kapatılır (glm/kimi'de çıktı 4-5 kat kısalıyor, 11-20 ölçümü);
        uzun yapılandırılmış çıktıda (sahne JSON'u) kesilmeyi ve abonelik payını önler."""
        govde = {"model": model, "max_tokens": en_cok, "temperature": sicaklik, "system": sistem,
                 "messages": [{"role": "user", "content": mesaj}]}  # fmt: skip
        if not dusun:
            govde["thinking"] = {"type": "disabled"}
        modeller = [model, *[m for m in YEDEKLER if m != model]]
        son = None
        for m in modeller:
            govde["model"] = m
            for d in range(deneme):
                try:
                    r = self._akis(govde)
                except LLMHatasi as e:
                    son = e
                    print(f"llm {m} deneme {d + 1}: {str(e)[:160]}", flush=True)
                    if "429" in str(e) or "5" == str(e)[:1]:
                        time.sleep(8 * (d + 1))
                    else:
                        time.sleep(2)
                    continue
                metin = "".join(c.get("text", "") for c in r.get("content", []) if c.get("type") == "text").strip()
                u = r.get("usage", {})
                self.kullanim.append({"model": m, "girdi": u.get("input_tokens"), "cikti": u.get("output_tokens"),
                                      "pay": (u.get("opencode") or {}).get("allowance")})  # fmt: skip
                if metin:
                    return metin
                son = LLMHatasi(f"{m}: boş yanıt (stop={r.get('stop_reason')})")
        raise LLMHatasi(f"model yanıt vermedi: {son}")

    def json_sor(self, sistem: str, mesaj: str, **kw) -> dict | list:
        """Yanıttan JSON çıkarır (```json bloğu ya da ilk { … son }); bozuksa onarım ister, o da bozuksa soruyu bir kez
        baştan sorar (11-26: glm-5.3 bölüm yazımında tırnak kaçışı bozuk geldi, tek onarım da düzeltemedi, koşu düştü)."""
        son_hata: ValueError | None = None
        for _ in range(2):
            metin = self.sor(sistem, mesaj, **kw)
            try:
                return json_cikar(metin)
            except ValueError:
                pass
            onar = self.sor("You fix malformed JSON. Return only valid JSON, nothing else.",
                            f"Fix this into valid JSON with the same content:\n\n{metin}", model=kw.get("model", VARSAYILAN),
                            en_cok=kw.get("en_cok", 8000), sicaklik=0.0, dusun=False)  # fmt: skip
            try:
                return json_cikar(onar)
            except ValueError as e:
                son_hata = e
        raise LLMHatasi(f"geçerli JSON alınamadı: {son_hata}")

    def _akis(self, govde: dict) -> dict:
        """Akışlı (SSE) istek: uzun senaryolar 10 dk'yı aşabiliyor; veri aktıkça okuma zaman aşımı işlemez.
        Dönüş akışsız yanıtla aynı biçimde: {"content": [{"type": "text", "text"}], "usage", "stop_reason"}."""
        istek = urllib.request.Request(UC, json.dumps({**govde, "stream": True}).encode("utf-8"), {
            "content-type": "application/json", "x-api-key": anahtar(), "anthropic-version": "2023-06-01",
            "user-agent": UA, "x-opencode-session": self.kimlik, "accept": "text/event-stream"})  # fmt: skip
        parcalar: list[str] = []
        usage: dict = {}
        dur = None
        bas = time.time()
        try:
            with urllib.request.urlopen(istek, timeout=180) as y:  # olaylar arası en çok 3 dk sessizlik
                for ham in y:
                    satir = ham.decode("utf-8", "replace").strip()
                    if not satir.startswith("data:"):
                        continue
                    veri = satir[5:].strip()
                    if not veri or veri == "[DONE]":
                        continue
                    try:
                        o = json.loads(veri)
                    except ValueError:
                        continue
                    t = o.get("type")
                    if t == "content_block_delta" and o.get("delta", {}).get("type") == "text_delta":
                        parcalar.append(o["delta"].get("text", ""))
                    elif t == "message_start":
                        usage.update(o.get("message", {}).get("usage") or {})
                    elif t == "message_delta":
                        usage.update(o.get("usage") or {})
                        dur = (o.get("delta") or {}).get("stop_reason") or dur
                    elif t == "error":
                        raise LLMHatasi(f"akış hatası: {str(o.get('error'))[:300]}")
        except urllib.error.HTTPError as e:
            raise LLMHatasi(f"{e.code} {e.read()[:400].decode('utf-8', 'replace')}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            raise LLMHatasi(f"5xx bağlantı: {e}") from None
        print(
            f"llm {govde['model']}: {usage.get('output_tokens')} token, {time.time() - bas:.0f} sn, {dur}, "
            f"pay {(usage.get('opencode') or {}).get('allowance')}",
            flush=True,
        )
        return {"content": [{"type": "text", "text": "".join(parcalar)}], "usage": usage, "stop_reason": dur}

    def _istek(self, govde: dict, toplam_sure: float = 900) -> dict:
        """Tek istek; `toplam_sure` sonunda yanıt gelmemişse vazgeçilir. 11-26: eleştirmen çağrısı 25 dk yanıtsız
        kaldı; urlopen zaman aşımı okuma başına işlediği için bağlantı açık kaldıkça koşu bekliyordu. İstek bir
        artalan iş parçacığında koşar; süre dolunca iş parçacığı bırakılır (süreç çıkışını tutmaz)."""
        import threading

        istek = urllib.request.Request(UC, json.dumps(govde).encode("utf-8"), {
            "content-type": "application/json", "x-api-key": anahtar(), "anthropic-version": "2023-06-01",
            "user-agent": UA, "x-opencode-session": self.kimlik})  # fmt: skip
        sonuc: dict = {}

        def _cagir() -> None:
            try:
                with urllib.request.urlopen(istek, timeout=600) as y:
                    sonuc["yanit"] = json.loads(y.read())
            except urllib.error.HTTPError as e:
                govde_hata = e.read()[:400].decode("utf-8", "replace")
                sonuc["hata"] = LLMHatasi(f"{e.code} {govde_hata}")
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
                sonuc["hata"] = LLMHatasi(f"5xx bağlantı: {e}")

        t = threading.Thread(target=_cagir, daemon=True)
        t.start()
        t.join(toplam_sure)
        if t.is_alive():
            raise LLMHatasi(f"5xx bağlantı: {toplam_sure:.0f} sn'de yanıt yok")
        if "hata" in sonuc:
            raise sonuc["hata"]
        return sonuc["yanit"]


def json_cikar(metin: str) -> dict | list:
    if m := re.search(r"```(?:json)?\s*(.+?)```", metin, re.S):
        metin = m.group(1)
    bas = min([i for i in (metin.find("{"), metin.find("[")) if i >= 0], default=-1)
    if bas < 0:
        raise ValueError("JSON yok")
    son = max(metin.rfind("}"), metin.rfind("]"))
    return json.loads(metin[bas : son + 1])
