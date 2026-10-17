"""Uzun video (film) hattı: kaynaklı senaryo → tutarlı karakterli sahneler (yerel FLUX.2 klein) → seçili sahnede gerçek
hareket (yerel Wan 2.2 5B) → anlatım (Chatterbox) → kurgu (PIL + ffmpeg) → kapak ve açıklama.

Shorts hattından (`otomat/hikaye`) bağımsız; GPU isteyen her adım bu makinedeki ComfyUI sunucusunda koşar, Actions'ta
değil. Karar ve ölçümler: docs/arastirma/11-uzun-video.md (K-26…).
"""
