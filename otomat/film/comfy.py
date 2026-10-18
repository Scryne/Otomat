"""Yerel ComfyUI sunucusu üzerinden görsel (FLUX.2 klein 4B, Apache-2.0) ve resimden video (Wan 2.2 TI2V-5B,
Apache-2.0).

Sunucu bu makinede ayrıca çalışır (`OTOMAT_COMFY`, varsayılan http://127.0.0.1:8188; kurulum `OTOMAT_COMFY_DIZIN`).
Ölçümler (RTX 4060 Laptop 8 GB, 10-17): 1344×768 görsel ~7 sn, tek referansla ~11 sn; Wan 832×480 49 kare 10 adım
~70 sn, 1280×704 73 kare 10 dakikayı aştı.
"""

import hashlib
import json
import os
import shutil
import time
import urllib.request
import uuid
from pathlib import Path

SUNUCU = os.environ.get("OTOMAT_COMFY", "http://127.0.0.1:8188")
DIZIN = Path(os.environ.get("OTOMAT_COMFY_DIZIN", Path.home() / "ComfyUI"))

FLUX = {"unet": "flux-2-klein-4b-fp8.safetensors", "clip": "qwen_3_4b.safetensors", "vae": "flux2-vae.safetensors"}
WAN = {
    "unet": "wan2.2_ti2v_5B_fp16.safetensors",
    "clip": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
    "vae": "wan2.2_vae.safetensors",
}
# Q4_K_M ile ComfyUI tepesi 17,4 GB (uzman + fp8 umt5), sistem arka plan işini kesti; Q3_K_M 14,6 GB, en az 4 GB boş
# kalıyor. Q3 tavuk sahnesinde elde ikinci çubuk çıkardı, Q4 temizdi: her klip yine elle incelenir (10-18)
WAN14_NICEM = os.environ.get("OTOMAT_WAN14_NICEM", "Q3_K_M")
WAN14 = {  # Wan 2.2 I2V-A14B: iki uzman (yüksek/düşük gürültü), GGUF + lightx2v 4 adım LoRA'ları
    "yuksek": f"Wan2.2-I2V-A14B-HighNoise-{WAN14_NICEM}.gguf",
    "dusuk": f"Wan2.2-I2V-A14B-LowNoise-{WAN14_NICEM}.gguf",
    "lora_yuksek": "wan2.2_i2v_A14b_high_noise_lora_rank64_lightx2v_4step_1022.safetensors",
    "lora_dusuk": "wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors",
    "vae": "wan_2.1_vae.safetensors",
}
WAN14_FPS = 16
WAN_NEGATIF = (
    "morphing, distortion, deformed face, extra limbs, extra fingers, blurry, flicker, text, letters, watermark, "
    "realistic, photo, 3d render"
)


class ComfyHatasi(RuntimeError):
    pass


def _istek(yol: str, veri: dict | None = None, zaman: float = 30):
    istek = urllib.request.Request(
        SUNUCU + yol,
        json.dumps(veri).encode() if veri is not None else None,
        {"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(istek, timeout=zaman) as y:
        govde = y.read()
    return json.loads(govde) if govde else {}


def hazir() -> bool:
    try:
        _istek("/system_stats", zaman=5)
        return True
    except OSError:
        return False


def bosalt() -> None:
    """Modelleri VRAM'den indir: Chatterbox aynı 8 GB'ı kullanacak."""
    try:
        _istek("/free", {"unload_models": True, "free_memory": True})
    except OSError:
        pass


def _yukle(yol: Path) -> str:
    """Girdi görselini ComfyUI'nin input klasörüne içerik adıyla koy (aynı adlı başka dosya üstüne yazılmasın)."""
    ad = f"otomat_{hashlib.sha1(yol.read_bytes()).hexdigest()[:16]}{yol.suffix}"
    hedef = DIZIN / "input" / ad
    if not hedef.exists():
        shutil.copy(yol, hedef)
    return ad


def gorsel_grafi(istem: str, w: int, h: int, tohum: int, referanslar: list[str]) -> dict:
    g = {
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": FLUX["unet"], "weight_dtype": "default"}},
        "clip": {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": FLUX["clip"], "type": "flux2", "device": "default"},
        },
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": FLUX["vae"]}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": istem}},
        "lat": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "sch": {"class_type": "Flux2Scheduler", "inputs": {"steps": 4, "width": w, "height": h}},
        "smp": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "noi": {"class_type": "RandomNoise", "inputs": {"noise_seed": tohum}},
    }
    kosul = ["pos", 0]
    for i, ad in enumerate(referanslar):
        g[f"ri{i}"] = {"class_type": "LoadImage", "inputs": {"image": ad}}
        g[f"rs{i}"] = {
            "class_type": "ImageScaleToTotalPixels",
            "inputs": {"image": [f"ri{i}", 0], "upscale_method": "lanczos", "megapixels": 1.0, "resolution_steps": 1},
        }
        g[f"re{i}"] = {"class_type": "VAEEncode", "inputs": {"pixels": [f"rs{i}", 0], "vae": ["vae", 0]}}
        g[f"rl{i}"] = {"class_type": "ReferenceLatent", "inputs": {"conditioning": kosul, "latent": [f"re{i}", 0]}}
        kosul = [f"rl{i}", 0]
    g["gui"] = {"class_type": "BasicGuider", "inputs": {"model": ["unet", 0], "conditioning": kosul}}
    g["sam"] = {
        "class_type": "SamplerCustomAdvanced",
        "inputs": {"noise": ["noi", 0], "guider": ["gui", 0], "sampler": ["smp", 0], "sigmas": ["sch", 0],
                   "latent_image": ["lat", 0]},
    }  # fmt: skip
    g["dec"] = {"class_type": "VAEDecode", "inputs": {"samples": ["sam", 0], "vae": ["vae", 0]}}
    g["kay"] = {"class_type": "SaveImage", "inputs": {"images": ["dec", 0], "filename_prefix": "otomat_film"}}
    return g


def i2v_grafi(gorsel_adi: str, istem: str, w: int, h: int, kare: int, adim: int, tohum: int) -> dict:
    return {
        # fp16 dosya yüklenirken fp8'e iner: RAM'de 9,3 → ~4,7 GB (10-17'de fp16 + önbellekteki FLUX belleği bitirdi)
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": WAN["unet"], "weight_dtype": "fp8_e4m3fn"}},
        "ms": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["unet", 0], "shift": 8.0}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": WAN["clip"], "type": "wan", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": WAN["vae"]}},
        "img": {"class_type": "LoadImage", "inputs": {"image": gorsel_adi}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": istem}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": WAN_NEGATIF}},
        "lat": {
            "class_type": "Wan22ImageToVideoLatent",
            "inputs": {"vae": ["vae", 0], "width": w, "height": h, "length": kare, "batch_size": 1,
                       "start_image": ["img", 0]},
        },
        "ks": {
            "class_type": "KSampler",
            "inputs": {"model": ["ms", 0], "seed": tohum, "steps": adim, "cfg": 5.0, "sampler_name": "uni_pc",
                       "scheduler": "simple", "positive": ["pos", 0], "negative": ["neg", 0],
                       "latent_image": ["lat", 0], "denoise": 1.0},
        },
        "dec": {"class_type": "VAEDecode", "inputs": {"samples": ["ks", 0], "vae": ["vae", 0]}},
        "kay": {"class_type": "SaveImage", "inputs": {"images": ["dec", 0], "filename_prefix": "otomat_i2v"}},
    }  # fmt: skip


def i2v14_grafi(
    gorsel_adi: str, istem: str, w: int, h: int, kare: int, tohum: int, uzman: str, latent_adi: str = ""
) -> dict:
    """Resmi ComfyUI şablonunun (video_wan2_2_14B_i2v) 4 adımlı LoRA yolu: cfg 1, shift 5, adım 0-2 yüksek, 2-4 düşük
    gürültü uzmanı. cfg 1'de negatif istem etkisizdir; istem neyin hareket edeceğini söyler.

    İki ayrı istek: tek istekte iki uzman birlikte RAM'de kalıp ComfyUI'yi 20 GB'a çıkardı (10-18). "yuksek" ara
    latent'i kaydeder; "dusuk" onu `latent_adi`ndan okuyup kareleri çıkarır."""
    yuksek = uzman == "yuksek"
    g = {
        # GGUF umt5 işlemcide açılıp RAM'i fp8 dosyadan çok şişirdi (10-18): fp8 kalır
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": WAN["clip"], "type": "wan", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": WAN14["vae"]}},
        "img": {"class_type": "LoadImage", "inputs": {"image": gorsel_adi}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": istem}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": WAN_NEGATIF}},
        "iv": {
            "class_type": "WanImageToVideo",
            "inputs": {"positive": ["pos", 0], "negative": ["neg", 0], "vae": ["vae", 0], "width": w, "height": h,
                       "length": kare, "batch_size": 1, "start_image": ["img", 0]},
        },
        "unet": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": WAN14[uzman]}},
        "lora": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {"model": ["unet", 0], "lora_name": WAN14[f"lora_{uzman}"], "strength_model": 1.0},
        },
        "ms": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["lora", 0], "shift": 5.0}},
        "ks": {
            "class_type": "KSamplerAdvanced",
            "inputs": {"model": ["ms", 0], "add_noise": "enable" if yuksek else "disable", "noise_seed": tohum,
                       "steps": 4, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple",
                       "positive": ["iv", 0], "negative": ["iv", 1],
                       "latent_image": ["iv", 2] if yuksek else ["ara", 0], "start_at_step": 0 if yuksek else 2,
                       "end_at_step": 2 if yuksek else 4,
                       "return_with_leftover_noise": "enable" if yuksek else "disable"},
        },
    }  # fmt: skip
    if yuksek:
        g["kay"] = {"class_type": "SaveLatent", "inputs": {"samples": ["ks", 0], "filename_prefix": "otomat_i2v14"}}
    else:
        g["ara"] = {"class_type": "LoadLatent", "inputs": {"latent": latent_adi}}
        g["dec"] = {"class_type": "VAEDecode", "inputs": {"samples": ["ks", 0], "vae": ["vae", 0]}}
        g["kay"] = {"class_type": "SaveImage", "inputs": {"images": ["dec", 0], "filename_prefix": "otomat_i2v"}}
    return g


def _calistir(g: dict, zaman_asimi: float) -> list[Path]:
    pid = _istek("/prompt", {"prompt": g, "client_id": str(uuid.uuid4())})["prompt_id"]
    bas = time.monotonic()
    while time.monotonic() - bas < zaman_asimi:
        h = _istek(f"/history/{pid}")
        if pid in h:
            durum = h[pid].get("status", {})
            if durum.get("status_str") == "error":
                raise ComfyHatasi(json.dumps(durum.get("messages", []))[-1500:])
            return [
                DIZIN / "output" / im.get("subfolder", "") / im["filename"]
                for cikti in h[pid]["outputs"].values()
                for anahtar in ("images", "latents")
                for im in cikti.get(anahtar, [])
            ]
        time.sleep(1)
    raise ComfyHatasi(f"zaman aşımı ({zaman_asimi:.0f} sn): {pid}")


def gorsel(istem: str, hedef: Path, w: int, h: int, tohum: int, referanslar: list[Path] = ()) -> Path:
    cikti = _calistir(gorsel_grafi(istem, w, h, tohum, [_yukle(r) for r in referanslar]), 600)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(cikti[0], hedef)
    return hedef


def i2v(gorsel_yolu: Path, istem: str, hedef_dizin: Path, w=832, h=480, kare=49, adim=10, tohum=3) -> list[Path]:
    """Kareleri `hedef_dizin`e 0000.png… diye taşır; kare sayısı 4n+1 olmalı (Wan)."""
    cikti = _calistir(i2v_grafi(_yukle(gorsel_yolu), istem, w, h, kare, adim, tohum), 1800)
    return _kareleri_tasi(cikti, hedef_dizin)


def i2v14(gorsel_yolu: Path, istem: str, hedef_dizin: Path, w=832, h=480, kare=33, tohum=3) -> list[Path]:
    """Wan 14B klibi; 16 fps olduğu için dizine `fps` dosyası yazılır, kurgu onu okur."""
    ad = _yukle(gorsel_yolu)
    (ara,) = _calistir(i2v14_grafi(ad, istem, w, h, kare, tohum, "yuksek"), 1800)
    bosalt()
    latent = ara.with_name(f"otomat_{uuid.uuid4().hex[:12]}.latent")
    shutil.move(ara, DIZIN / "input" / latent.name)
    try:
        cikti = _calistir(i2v14_grafi(ad, istem, w, h, kare, tohum, "dusuk", latent.name), 1800)
    finally:
        (DIZIN / "input" / latent.name).unlink(missing_ok=True)
        bosalt()
    yollar = _kareleri_tasi(cikti, hedef_dizin)
    (hedef_dizin / "fps").write_text(str(WAN14_FPS))
    return yollar


def _kareleri_tasi(cikti: list[Path], hedef_dizin: Path) -> list[Path]:
    hedef_dizin.mkdir(parents=True, exist_ok=True)
    yollar = []
    for i, k in enumerate(sorted(cikti)):
        yollar.append(shutil.move(k, hedef_dizin / f"{i:04d}.png"))
    return [Path(y) for y in yollar]
