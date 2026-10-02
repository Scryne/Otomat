---
proje: Otomat
created: 2026-10-02
type: arastirma
---
# Referans video: "Yattığı yerden para kazananların otomasyon taktiği"

Kaynak: Scryne'ın verdiği `Downloads\Download.mp4` (TikTok @rahatyasam, 10 dk, 576×1024). İnceleme: 15 sn
aralıklı kareler + faster-whisper (medium, CPU) Türkçe döküm, 2026-10-02.

## Boru hattı (ekrandan okunan)
1. Konu seçimi (İngilizce bilim sorusu: "Why do mirrors swap left and right?")
2. Senaryo: "Yerel Qwen" (büyük ihtimalle Ollama), sahne sahne
3. Bilimsel iddia denetimi: yine yerel Qwen, iddia başına geçti/kaldı
4. Seslendirme
5. "Video First Pexels v6": anlamsal arama + nesne filtresi, aynı Pexels ID ve aynı üretici tekrarına yasak,
   benzerlik eşiği %91, alakasız klip yerine AI görsel fallback
6. Hibrit montaj → Whisper altyazı + CTA ("More science & fascinating facts / Like & Subscribe")
7. Metadata (başlık, açıklama, etiket)
8. YouTube Data API: PRIVATE upload + `publishAt` ile 2 saat arayla planlı public
Ekranda "OpenAI API maliyeti: $0".

## Kanal sayıları (videodaki kendi ekranı)
- 335 video, 42 abone; son 60 dk 1.063, son 48 saat ~9.350 izlenme (~4.700/gün)
- Para kazanma eşiği 1.000 abone + 90 günde 10M Shorts izlenmesi → ~420 bin/90 gün ile 24 kat geride

## Değerlendirme
- Mühendislik derli toplu; zaafı strateji: geri besleme yok, stok görüntü, seri üretim.
- Asıl gelir modeli YouTube değil: "takip et, beğen, özelden yaz, botu bilgisayarına kurayım" (üç kez) — kitle toplama.
  Uzaktan kurulum teklifi güvenlik riski.
- Otomat'a alınan: aşamalı boru hattı, tekrar engelleyici benzerlik kontrolü, iddia kapısı, planlı yükleme.
- Otomat'ın farkı: veriden özgün görsel, analitik geri beslemesi, çok dilli metadata, düşük hacim (Proje-Fikri).
